"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { createClient } from "@/lib/supabase/client";
import type { UserRole } from "@/types";
import type { User, Session, SupabaseClient } from "@supabase/supabase-js";

interface UseAuthReturn {
  user: User | null;
  session: Session | null;
  role: UserRole | null;
  loading: boolean;
  isAuthenticated: boolean;
}

/**
 * React hook for auth state management.
 */
export function useAuth(): UseAuthReturn {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [role, setRole] = useState<UserRole | null>(null);
  const [loading, setLoading] = useState(true);

  // Stable supabase reference — created once per component lifetime
  const supabaseRef = useRef<SupabaseClient | null>(null);
  if (!supabaseRef.current) {
    supabaseRef.current = createClient();
  }
  const supabase = supabaseRef.current;

  const fetchRole = useCallback(
    async (userId: string) => {
      try {
        console.log("[useAuth] fetchRole: querying profiles for", userId.slice(0, 8));
        
        // Add timeout — if profile query hangs, default to Applicant after 3s
        const timeoutPromise = new Promise<null>((resolve) => {
          setTimeout(() => resolve(null), 3000);
        });

        const queryPromise = supabase
          .from("profiles")
          .select("role")
          .eq("user_id", userId)
          .single();

        const result = await Promise.race([queryPromise, timeoutPromise]);

        if (result === null) {
          console.warn("[useAuth] fetchRole: timed out after 3s, defaulting to Applicant");
          setRole("Applicant");
          return;
        }

        const { data: profile, error } = result;
        console.log("[useAuth] fetchRole result:", { profile, error: error?.message });

        if (profile?.role) {
          setRole(profile.role as UserRole);
        } else {
          setRole("Applicant");
        }
      } catch (err) {
        console.error("[useAuth] fetchRole exception:", err);
        setRole("Applicant");
      }
    },
    [supabase]
  );

  useEffect(() => {
    let mounted = true;

    const getInitialSession = async () => {
      console.log("[useAuth] getInitialSession START");
      try {
        const {
          data: { session: currentSession },
        } = await supabase.auth.getSession();

        console.log("[useAuth] getSession returned:", {
          hasSession: !!currentSession,
          userId: currentSession?.user?.id?.slice(0, 8),
        });

        if (!mounted) return;

        setSession(currentSession);
        setUser(currentSession?.user ?? null);

        if (currentSession?.user) {
          console.log("[useAuth] Fetching role for user:", currentSession.user.id.slice(0, 8));
          await fetchRole(currentSession.user.id);
          console.log("[useAuth] fetchRole completed");
        }
      } catch (err) {
        console.error("[useAuth] getInitialSession ERROR:", err);
        if (!mounted) return;
        setSession(null);
        setUser(null);
        setRole(null);
      } finally {
        if (mounted) {
          console.log("[useAuth] Setting loading=false");
          setLoading(false);
        }
      }
    };

    getInitialSession();

    // Subscribe to auth state changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, newSession) => {
      if (!mounted) return;

      setSession(newSession);
      setUser(newSession?.user ?? null);

      if (event === "SIGNED_IN" && newSession?.user) {
        await fetchRole(newSession.user.id);
      } else if (event === "SIGNED_OUT") {
        setRole(null);
        setUser(null);
        setSession(null);
      } else if (event === "TOKEN_REFRESHED" && !newSession) {
        if (typeof window !== "undefined") {
          window.location.href = "/login?message=session_ended";
        }
      }

      setLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [supabase, fetchRole]);

  return {
    user,
    session,
    role,
    loading,
    isAuthenticated: !!session && !!user,
  };
}
