"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import type { UserRole } from "@/types";

function getDashboardPath(role: UserRole | null): string {
  switch (role) {
    case "Bank_Officer":
      return "/officer/dashboard";
    case "Admin":
      return "/admin/dashboard";
    default:
      return "/applicant/dashboard";
  }
}

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { isAuthenticated, role, loading } = useAuth();
  const router = useRouter();

  console.log("[AuthLayout] render:", { loading, isAuthenticated, role });

  useEffect(() => {
    if (!loading && isAuthenticated) {
      router.replace(getDashboardPath(role));
    }
  }, [isAuthenticated, role, loading, router]);

  // Show nothing while checking auth state
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }

  // If authenticated, don't render auth pages (redirect is happening)
  if (isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-8">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-foreground md:text-3xl">
            AI Loan Decision Platform
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Transparent, explainable, and fair lending decisions
          </p>
        </div>
        {children}
      </div>
    </div>
  );
}
