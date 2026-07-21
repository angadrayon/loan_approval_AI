"use client";

import { RoleGuard } from "@/components/layout/RoleGuard";

/**
 * Officer route group layout — wraps all /officer/* pages.
 * Only users with the "Bank_Officer" role can access these pages.
 *
 * Requirements: 3.3, 3.5
 */
export default function OfficerLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <RoleGuard allowedRoles={["Bank_Officer"]}>{children}</RoleGuard>;
}
