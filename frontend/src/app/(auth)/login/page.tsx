"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { authService } from "@/lib/auth-service";
import { useAuth } from "@/hooks/useAuth";
import { validateEmail } from "@/lib/validators";
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

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { role } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [sessionMessage, setSessionMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Handle ?message=session_ended query param
  useEffect(() => {
    const message = searchParams.get("message");
    if (message === "session_ended") {
      setSessionMessage("Your session has ended. Please log in again.");
    }
  }, [searchParams]);

  // Inline validation for email (within 200ms via onChange)
  const handleEmailChange = (value: string) => {
    setEmail(value);
    if (emailError) {
      setEmailError(validateEmail(value));
    }
  };

  // Inline validation on blur
  const handleEmailBlur = () => {
    setEmailError(validateEmail(email));
  };

  // Inline validation for password
  const handlePasswordChange = (value: string) => {
    setPassword(value);
    if (passwordError) {
      setPasswordError(value ? null : "Password is required");
    }
  };

  const handlePasswordBlur = () => {
    setPasswordError(password ? null : "Password is required");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    // Validate all fields
    const emailErr = validateEmail(email);
    const passwordErr = password ? null : "Password is required";

    setEmailError(emailErr);
    setPasswordError(passwordErr);

    if (emailErr || passwordErr) {
      return;
    }

    setIsSubmitting(true);

    try {
      const result = await authService.login(email.trim(), password);

      if (result.error) {
        // Requirement 2.2: Don't reveal which credential is wrong
        setFormError("Invalid email or password");
        setIsSubmitting(false);
        return;
      }

      // Redirect to role-appropriate dashboard
      router.push(getDashboardPath(role));
    } catch {
      setFormError("Invalid email or password");
      setIsSubmitting(false);
    }
  };

  return (
    <div className="rounded-lg border border-border bg-card p-6 shadow-sm md:p-8">
      <div className="mb-6 text-center">
        <h2 className="text-xl font-semibold text-card-foreground">
          Sign in to your account
        </h2>
      </div>

      {/* Session ended message */}
      {sessionMessage && (
        <div className="mb-4 rounded-md border border-border bg-muted p-3 text-sm text-muted-foreground">
          {sessionMessage}
        </div>
      )}

      {/* Form-level error */}
      {formError && (
        <div className="mb-4 rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {formError}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {/* Email field */}
        <div className="space-y-1.5">
          <label
            htmlFor="email"
            className="block text-sm font-medium text-foreground"
          >
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => handleEmailChange(e.target.value)}
            onBlur={handleEmailBlur}
            className={`block w-full min-h-[44px] rounded-md border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 ${
              emailError
                ? "border-destructive focus:ring-destructive"
                : "border-input"
            }`}
            placeholder="you@example.com"
            aria-invalid={!!emailError}
            aria-describedby={emailError ? "email-error" : undefined}
          />
          {emailError && (
            <p id="email-error" className="text-xs text-destructive" role="alert">
              {emailError}
            </p>
          )}
        </div>

        {/* Password field */}
        <div className="space-y-1.5">
          <label
            htmlFor="password"
            className="block text-sm font-medium text-foreground"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => handlePasswordChange(e.target.value)}
            onBlur={handlePasswordBlur}
            className={`block w-full min-h-[44px] rounded-md border px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1 ${
              passwordError
                ? "border-destructive focus:ring-destructive"
                : "border-input"
            }`}
            placeholder="Enter your password"
            aria-invalid={!!passwordError}
            aria-describedby={passwordError ? "password-error" : undefined}
          />
          {passwordError && (
            <p id="password-error" className="text-xs text-destructive" role="alert">
              {passwordError}
            </p>
          )}
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="flex w-full min-h-[44px] items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
              Signing in...
            </span>
          ) : (
            "Sign in"
          )}
        </button>
      </form>

      {/* Link to register */}
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Don&apos;t have an account?{" "}
        <Link
          href="/register"
          className="font-medium text-primary underline-offset-4 hover:underline"
        >
          Create an account
        </Link>
      </p>
    </div>
  );
}
