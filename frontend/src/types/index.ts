// ============================================================
// Auth Types
// ============================================================

export interface AuthResult {
  user: {
    id: string;
    email: string;
  } | null;
  session: Session | null;
  error: string | null;
}

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  user: {
    id: string;
    email: string;
  };
}

// ============================================================
// Loan Application Input (matches backend LoanApplicationInput)
// ============================================================

export type EmploymentStatus = "Employed" | "Self-Employed" | "Unemployed" | "Retired";

export interface LoanApplicationInput {
  age: number; // 18-100
  monthly_income: number; // >0, <=10,000,000
  employment_status: EmploymentStatus;
  employment_length: number; // 0-50
  credit_score: number; // 300-850
  existing_loans: number; // 0-50
  monthly_emi: number; // >=0, <= monthly_income
  dti_ratio: number; // 0-100
  credit_utilization: number; // 0-100
  loan_amount_requested: number; // >0, <=10,000,000
}

// ============================================================
// Risk Levels and Categories
// ============================================================

export type RiskLevel =
  | "Very Low Risk"
  | "Low Risk"
  | "Moderate Risk"
  | "High Risk"
  | "Very High Risk";

export type ReadinessCategory = "Poor" | "Fair" | "Good" | "Excellent";

export type Decision = "Approved" | "Rejected";

// ============================================================
// SHAP Value
// ============================================================

export interface ShapValue {
  feature: string;
  value: number;
  shap_value: number;
  direction: "positive" | "negative";
}

// ============================================================
// Counterfactual
// ============================================================

export interface Counterfactual {
  feature: string;
  current_value: number;
  recommended_value: number;
  projected_approval_probability: number;
  projected_risk_score: number;
  projected_risk_level: RiskLevel;
  projected_loan_readiness_score: number;
}

// ============================================================
// Prediction Result
// ============================================================

export interface PredictionResult {
  application_id: string;
  approval_probability: number;
  risk_score: number;
  risk_level: RiskLevel;
  default_probability: number;
  decision: Decision;
  loan_readiness_score: number;
  readiness_category: ReadinessCategory;
  shap_values: ShapValue[];
  top_factors: ShapValue[];
  counterfactuals: Counterfactual[] | null;
  rf_approval_probability: number;
  timestamp: string;
}

// ============================================================
// Simulation Result (What-If)
// ============================================================

export interface SimulationResult {
  approval_probability: number;
  risk_score: number;
  risk_level: RiskLevel;
  loan_readiness_score: number;
  readiness_category: ReadinessCategory;
  decision: Decision;
}

// ============================================================
// Fairness Metrics
// ============================================================

export interface FairnessMetrics {
  demographic_parity_diff: number;
  equalized_odds_diff: number;
  proxy_correlations: Record<string, number>;
  prediction_count: number;
  computed_at: string;
}

// ============================================================
// Audit Types
// ============================================================

export interface AuditLog {
  id: string;
  user_id: string | null;
  event_type: string;
  event_data: Record<string, unknown>;
  ip_address: string | null;
  created_at: string;
}

export interface AuditFilters {
  date_from?: string;
  date_to?: string;
  user_id?: string;
  decision?: Decision;
}

// ============================================================
// Pagination
// ============================================================

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ============================================================
// Model Statistics
// ============================================================

export interface ModelMetrics {
  auc_roc: number;
  f1_score: number;
  ks_statistic: number;
}

export interface ModelStatistics {
  xgboost: ModelMetrics;
  random_forest: ModelMetrics;
}

// ============================================================
// User / Profile
// ============================================================

export type UserRole = "Applicant" | "Bank_Officer" | "Admin";

export interface UserProfile {
  id: string;
  user_id: string;
  name: string;
  email: string;
  role: UserRole;
  created_at: string;
}

// ============================================================
// Assessment Detail (combined view)
// ============================================================

export interface AssessmentDetail {
  application: LoanApplicationInput & {
    id: string;
    user_id: string;
    status: string;
    created_at: string;
  };
  prediction: PredictionResult;
}

// ============================================================
// Plain Language Explanation Types
// ============================================================

export interface PlainLanguageExplanation {
  feature_display_name: string;
  explanation: string;
  direction: "positive" | "negative";
}

export interface PlainLanguageRecommendation {
  feature_display_name: string;
  recommendation: string;
  projected_outcome: string;
}

export interface ReadinessInterpretation {
  score: number;
  category: ReadinessCategory;
  description: string;
  improvement_areas: string[];
}
