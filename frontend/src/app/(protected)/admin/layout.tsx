"use client";

import { RoleGuard } from "@/components/layout/RoleGuard";

/**
 * Admin route group layout — wraps all /admin/* pages.
 * Only users with the "Admin" role can access these pages.
 *
 * Requirements: 3.4, 3.5
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <RoleGuard allowedRoles={["Admin"]}>{children}</RoleGuard>;
}
