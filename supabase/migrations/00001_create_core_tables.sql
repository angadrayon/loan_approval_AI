-- Migration: 00001_create_core_tables
-- Description: Create core tables for the AI Loan Decision Platform
-- Tables: profiles, loan_applications, predictions, shap_values, counterfactuals, audit_logs, fairness_metrics

-- ============================================================================
-- PROFILES TABLE
-- Stores user profile information linked to Supabase Auth users
-- ============================================================================
CREATE TABLE profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
    name TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 100),
    role TEXT NOT NULL DEFAULT 'Applicant' CHECK (role IN ('Applicant', 'Bank_Officer', 'Admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for profiles
CREATE INDEX idx_profiles_user_id ON profiles(user_id);
CREATE INDEX idx_profiles_role ON profiles(role);

-- ============================================================================
-- LOAN_APPLICATIONS TABLE
-- Stores loan application submissions with all financial input fields
-- ============================================================================
CREATE TABLE loan_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    age INT NOT NULL CHECK (age BETWEEN 18 AND 100),
    monthly_income NUMERIC NOT NULL CHECK (monthly_income > 0 AND monthly_income <= 10000000),
    employment_status TEXT NOT NULL CHECK (employment_status IN ('Employed', 'Self-Employed', 'Unemployed', 'Retired')),
    employment_length NUMERIC NOT NULL CHECK (employment_length BETWEEN 0 AND 50),
    credit_score INT NOT NULL CHECK (credit_score BETWEEN 300 AND 850),
    existing_loans INT NOT NULL CHECK (existing_loans BETWEEN 0 AND 50),
    monthly_emi NUMERIC NOT NULL CHECK (monthly_emi >= 0),
    dti_ratio NUMERIC NOT NULL CHECK (dti_ratio BETWEEN 0 AND 100),
    credit_utilization NUMERIC NOT NULL CHECK (credit_utilization BETWEEN 0 AND 100),
    loan_amount_requested NUMERIC NOT NULL CHECK (loan_amount_requested > 0 AND loan_amount_requested <= 10000000),
    status TEXT NOT NULL DEFAULT 'Pending Review' CHECK (status IN ('Pending Review', 'Approved', 'Rejected')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT emi_not_exceeding_income CHECK (monthly_emi <= monthly_income)
);

-- Indexes for loan_applications
CREATE INDEX idx_loan_applications_user_id ON loan_applications(user_id);
CREATE INDEX idx_loan_applications_status ON loan_applications(status);
CREATE INDEX idx_loan_applications_created_at ON loan_applications(created_at DESC);

-- ============================================================================
-- PREDICTIONS TABLE
-- Stores ML prediction results linked to loan applications (one-to-one)
-- ============================================================================
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES loan_applications(id) ON DELETE CASCADE NOT NULL UNIQUE,
    approval_probability NUMERIC NOT NULL CHECK (approval_probability BETWEEN 0 AND 100),
    risk_score NUMERIC NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_level TEXT NOT NULL CHECK (risk_level IN ('Very Low Risk', 'Low Risk', 'Moderate Risk', 'High Risk', 'Very High Risk')),
    default_probability NUMERIC NOT NULL CHECK (default_probability BETWEEN 0 AND 100),
    decision TEXT NOT NULL CHECK (decision IN ('Approved', 'Rejected')),
    loan_readiness_score NUMERIC NOT NULL CHECK (loan_readiness_score BETWEEN 0 AND 100),
    readiness_category TEXT NOT NULL CHECK (readiness_category IN ('Poor', 'Fair', 'Good', 'Excellent')),
    rf_approval_probability NUMERIC NOT NULL CHECK (rf_approval_probability BETWEEN 0 AND 100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for predictions
CREATE INDEX idx_predictions_application_id ON predictions(application_id);
CREATE INDEX idx_predictions_created_at ON predictions(created_at DESC);

-- ============================================================================
-- SHAP_VALUES TABLE
-- Stores SHAP explanation values for each prediction (one-to-many)
-- ============================================================================
CREATE TABLE shap_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id UUID REFERENCES predictions(id) ON DELETE CASCADE NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value NUMERIC NOT NULL,
    shap_value NUMERIC NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('positive', 'negative'))
);

-- Indexes for shap_values
CREATE INDEX idx_shap_values_prediction_id ON shap_values(prediction_id);

-- ============================================================================
-- COUNTERFACTUALS TABLE
-- Stores counterfactual explanations for rejected predictions (one-to-many)
-- ============================================================================
CREATE TABLE counterfactuals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id UUID REFERENCES predictions(id) ON DELETE CASCADE NOT NULL,
    feature_name TEXT NOT NULL,
    current_value NUMERIC NOT NULL,
    recommended_value NUMERIC NOT NULL,
    estimated_impact NUMERIC NOT NULL CHECK (estimated_impact BETWEEN 0 AND 100)
);

-- Indexes for counterfactuals
CREATE INDEX idx_counterfactuals_prediction_id ON counterfactuals(prediction_id);

-- ============================================================================
-- AUDIT_LOGS TABLE
-- Stores immutable audit trail for all system events
-- ============================================================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}',
    ip_address TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for audit_logs
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- ============================================================================
-- FAIRNESS_METRICS TABLE
-- Stores computed fairness metrics snapshots
-- ============================================================================
CREATE TABLE fairness_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    demographic_parity_diff NUMERIC NOT NULL,
    equalized_odds_diff NUMERIC NOT NULL,
    proxy_correlations JSONB NOT NULL DEFAULT '{}',
    prediction_count INT NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for fairness_metrics
CREATE INDEX idx_fairness_metrics_computed_at ON fairness_metrics(computed_at DESC);
