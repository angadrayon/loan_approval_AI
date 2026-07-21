/**
 * API Client for the AI Loan Decision Platform.
 *
 * Communicates with the FastAPI backend at NEXT_PUBLIC_API_URL.
 * Automatically attaches the Supabase JWT access token to every request.
 * Provides typed methods for all application endpoints.
 *
 * Requirements: 18.1, 18.2, 18.3
 */

import { createClient } from "@/lib/supabase/client";
import type {
  LoanApplicationInput,
  PredictionResult,
  SimulationResult,
  PaginatedResponse,
  AssessmentDetail,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ============================================================
// Error Types
// ============================================================

export class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// ============================================================
// Core HTTP Methods
// ============================================================

/**
 * Get the current Supabase JWT access token.
 */
async function getAccessToken(): Promise<string | null> {
  const supabase = createClient();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

/**
 * Build request headers with JWT authorization.
 */
async function buildHeaders(): Promise<HeadersInit> {
  const token = await getAccessToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Handle API response — parse JSON or throw ApiError.
 */
async function handleResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>;
  }

  // Parse error response
  let detail = "An unexpected error occurred";
  try {
    const errorBody = await response.json();
    detail = errorBody.detail || detail;
  } catch {
    detail = response.statusText || detail;
  }

  // Don't auto-redirect on 401 — let the calling code handle it
  // The useAuth hook will detect session expiry and redirect appropriately

  throw new ApiError(response.status, detail);
}

/**
 * Perform a GET request to the API.
 */
async function get<T>(path: string): Promise<T> {
  const headers = await buildHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers,
  });
  return handleResponse<T>(response);
}

/**
 * Perform a POST request to the API.
 */
async function post<T>(path: string, body: unknown): Promise<T> {
  const headers = await buildHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  return handleResponse<T>(response);
}

/**
 * Perform a PUT request to the API.
 */
async function put<T>(path: string, body: unknown): Promise<T> {
  const headers = await buildHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(body),
  });
  return handleResponse<T>(response);
}

/**
 * Perform a DELETE request to the API.
 */
async function del<T>(path: string): Promise<T> {
  const headers = await buildHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers,
  });
  return handleResponse<T>(response);
}

// ============================================================
// Application Endpoints
// ============================================================

/**
 * Submit a new loan application and receive a prediction.
 *
 * POST /api/v1/applications
 */
export async function submitApplication(
  data: LoanApplicationInput
): Promise<PredictionResult> {
  return post<PredictionResult>("/api/v1/applications", data);
}

/**
 * Get the current user's loan applications (paginated).
 *
 * GET /api/v1/applications?page=N
 */
export async function getApplications(
  page: number = 1
): Promise<PaginatedResponse<Record<string, unknown>>> {
  return get<PaginatedResponse<Record<string, unknown>>>(
    `/api/v1/applications?page=${page}`
  );
}

/**
 * Get full application detail with prediction, SHAP, and counterfactuals.
 *
 * GET /api/v1/applications/{id}
 */
export async function getApplicationById(id: string): Promise<AssessmentDetail> {
  return get<AssessmentDetail>(`/api/v1/applications/${id}`);
}

/**
 * Get all applications for officer review (paginated).
 *
 * GET /api/v1/applications/review?page=N
 */
export async function getReviewApplications(
  page: number = 1
): Promise<PaginatedResponse<Record<string, unknown>>> {
  return get<PaginatedResponse<Record<string, unknown>>>(
    `/api/v1/applications/review?page=${page}`
  );
}

// ============================================================
// Simulation Endpoint
// ============================================================

/**
 * Run a What-If simulation without persisting results.
 *
 * POST /api/v1/predictions/simulate
 */
export async function simulateWhatIf(
  data: LoanApplicationInput
): Promise<SimulationResult> {
  return post<SimulationResult>("/api/v1/predictions/simulate", data);
}

// ============================================================
// Report Endpoint
// ============================================================

/**
 * Download a PDF assessment report.
 *
 * GET /api/v1/reports/{assessmentId}/pdf
 */
export async function downloadReport(assessmentId: string): Promise<Blob> {
  const headers = await buildHeaders();
  const response = await fetch(
    `${API_BASE_URL}/api/v1/reports/${assessmentId}/pdf`,
    {
      method: "GET",
      headers,
    }
  );

  if (!response.ok) {
    throw new ApiError(response.status, "Failed to download report");
  }

  return response.blob();
}

// ============================================================
// Admin Endpoints
// ============================================================

/**
 * Get fairness metrics (Admin only).
 *
 * GET /api/v1/admin/fairness
 */
export async function getFairnessMetrics() {
  return get<Record<string, unknown>>("/api/v1/admin/fairness");
}

/**
 * Get paginated user list (Admin only).
 *
 * GET /api/v1/admin/users?page=N
 */
export async function getUsers(page: number = 1) {
  return get<PaginatedResponse<Record<string, unknown>>>(
    `/api/v1/admin/users?page=${page}`
  );
}

/**
 * Update a user's role (Admin only).
 *
 * PUT /api/v1/admin/users/{id}/role
 */
export async function updateUserRole(userId: string, role: string) {
  return put<Record<string, unknown>>(`/api/v1/admin/users/${userId}/role`, {
    role,
  });
}

/**
 * Get audit logs (Admin only).
 *
 * GET /api/v1/admin/audit-logs?page=N
 */
export async function getAuditLogs(
  page: number = 1,
  filters?: Record<string, string>
) {
  const params = new URLSearchParams({ page: String(page) });
  if (filters) {
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.append(key, value);
    });
  }
  return get<PaginatedResponse<Record<string, unknown>>>(
    `/api/v1/admin/audit-logs?${params.toString()}`
  );
}

/**
 * Get model performance statistics (Officer/Admin).
 *
 * GET /api/v1/admin/model-stats
 */
export async function getModelStats() {
  return get<Record<string, unknown>>("/api/v1/admin/model-stats");
}

// ============================================================
// Export all as a unified API client object
// ============================================================

export const apiClient = {
  // Applications
  submitApplication,
  getApplications,
  getApplicationById,
  getReviewApplications,

  // Simulation
  simulateWhatIf,

  // Reports
  downloadReport,

  // Admin
  getFairnessMetrics,
  getUsers,
  updateUserRole,
  getAuditLogs,
  getModelStats,

  // Raw HTTP methods (for custom calls)
  get,
  post,
  put,
  delete: del,
};
