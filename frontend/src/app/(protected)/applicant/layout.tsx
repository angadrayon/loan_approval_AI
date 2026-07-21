"use client";

import { RoleGuard } from "@/components/layout/RoleGuard";

/**
 * Applicant route group layout — wraps all /applicant/* pages.
 * Only users with the "Applicant" role can access these pages.
 *
 * Requirements: 3.2, 3.5
 */
export default function ApplicantLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <RoleGuard allowedRoles={["Applicant"]}>{children}</RoleGuard>;
}
