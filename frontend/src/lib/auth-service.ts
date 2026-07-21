import { createClient } from "@/lib/supabase/client";
import type { AuthResult } from "@/types";

/**
 * AuthService implementation wrapping Supabase Auth client.
 * Handles register, login, logout, session management, and auth state changes.
 *
 * Requirements: 2.1, 2.3, 2.4, 2.5
 */
export const authService = {
  /**
   * Register a new user with name, email, and password.
   * The database trigger will create the profile automatically with the Applicant role.
   */
  async register(
    name: string,
    email: string,
    password: string
  ): Promise<AuthResult> {
    const supabase = createClient();

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          name,
        },
      },
    });

    if (error) {
      return {
        user: null,
        session: null,
        error: error.message,
      };
    }

    return {
      user: data.user
        ? { id: data.user.id, email: data.user.email ?? "" }
        : null,
      session: data.session
        ? {
            access_token: data.session.access_token,
            refresh_token: data.session.refresh_token,
            expires_at: data.session.expires_at ?? 0,
            user: {
              id: data.user?.id ?? "",
              email: data.user?.email ?? "",
            },
          }
        : null,
      error: null,
    };
  },

  /**
   * Login with email and password via Supabase Auth.
   * Returns session data on success.
   */
  async login(email: string, password: string): Promise<AuthResult> {
    const supabase = createClient();

    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      return {
        user: null,
        session: null,
        error: error.message,
      };
    }

    return {
      user: data.user
        ? { id: data.user.id, email: data.user.email ?? "" }
        : null,
      session: data.session
        ? {
            access_token: data.session.access_token,
            refresh_token: data.session.refresh_token,
            expires_at: data.session.expires_at ?? 0,
            user: {
              id: data.user.id,
              email: data.user.email ?? "",
            },
          }
        : null,
      error: null,
    };
  },

  /**
   * Logout the current user.
   * Calls supabase.auth.signOut() which clears all cookies and local storage.
   * Requirement 2.3: Clear all client-side stored authentication state.
   */
  async logout(): Promise<void> {
    const supabase = createClient();
    await supabase.auth.signOut();
  },

  /**
   * Get the current session.
   * Returns null if not authenticated.
   */
  async getSession() {
    const supabase = createClient();
    const { data, error } = await supabase.auth.getSession();

    if (error || !data.session) {
      return null;
    }

    return {
      access_token: data.session.access_token,
      refresh_token: data.session.refresh_token,
      expires_at: data.session.expires_at ?? 0,
      user: {
        id: data.session.user.id,
        email: data.session.user.email ?? "",
      },
    };
  },

  /**
   * Subscribe to auth state changes.
   * Handles token refresh failures by redirecting to login with a session ended message.
   * Requirements: 2.4, 2.5
   */
  onAuthStateChange(
    callback: (session: AuthResult["session"]) => void
  ): { unsubscribe: () => void } {
    const supabase = createClient();

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === "TOKEN_REFRESHED" && session) {
        callback({
          access_token: session.access_token,
          refresh_token: session.refresh_token,
          expires_at: session.expires_at ?? 0,
          user: {
            id: session.user.id,
            email: session.user.email ?? "",
          },
        });
      } else if (event === "SIGNED_OUT") {
        callback(null);
      } else if (event === "SIGNED_IN" && session) {
        callback({
          access_token: session.access_token,
          refresh_token: session.refresh_token,
          expires_at: session.expires_at ?? 0,
          user: {
            id: session.user.id,
            email: session.user.email ?? "",
          },
        });
      } else if (event === "TOKEN_REFRESHED" && !session) {
        // Token refresh failed — redirect to login with session ended message
        // Requirement 2.5
        if (typeof window !== "undefined") {
          window.location.href = "/login?message=session_ended";
        }
      }
    });

    return {
      unsubscribe: () => subscription.unsubscribe(),
    };
  },
};
