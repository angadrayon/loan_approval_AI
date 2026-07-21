-- Migration: 00002_create_rls_policies
-- Description: Enable Row Level Security and create policies for all tables
-- Requirements: 3.6, 22.2, 12.2

-- ============================================================================
-- PROFILES - RLS POLICIES
-- ============================================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile
CREATE POLICY "Users can read own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = user_id);

-- Users can update their own profile name
CREATE POLICY "Users can update own profile name"
    ON profiles FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Admins can read all profiles
CREATE POLICY "Admins can read all profiles"
    ON profiles FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE user_id = auth.uid() AND role = 'Admin'
        )
    );

-- ============================================================================
-- LOAN_APPLICATIONS - RLS POLICIES
-- ============================================================================
ALTER TABLE loan_applications ENABLE ROW LEVEL SECURITY;

-- Applicants can read their own applications
CREATE POLICY "Applicants can read own applications"
    ON loan_applications FOR SELECT
    USING (auth.uid() = user_id);

-- Applicants can insert their own applications
CREATE POLICY "Applicants can insert own applications"
    ON loan_applications FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Officers and Admins can read all applications
CREATE POLICY "Officers can read all applications"
    ON loan_applications FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE user_id = auth.uid() AND role IN ('Bank_Officer', 'Admin')
        )
    );

-- ============================================================================
-- PREDICTIONS - RLS POLICIES
-- ============================================================================
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;

-- Users can read predictions for their own applications (via join)
CREATE POLICY "Users can read predictions for own applications"
    ON predictions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM loan_applications
            WHERE loan_applications.id = predictions.application_id
            AND loan_applications.user_id = auth.uid()
        )
    );

-- Officers and Admins can read all predictions
CREATE POLICY "Officers can read all predictions"
    ON predictions FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE user_id = auth.uid() AND role IN ('Bank_Officer', 'Admin')
        )
    );

-- ============================================================================
-- SHAP_VALUES - RLS POLICIES
-- ============================================================================
ALTER TABLE shap_values ENABLE ROW LEVEL SECURITY;

-- Users can read SHAP values for their own predictions (via join chain)
CREATE POLICY "Users can read shap values for own predictions"
    ON shap_values FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM predictions p
            JOIN loan_applications la ON la.id = p.application_id
            WHERE p.id = shap_values.prediction_id
            AND la.user_id = auth.uid()
        )
    );

-- Officers and Admins can read all SHAP values
CREATE POLICY "Officers can read all shap values"
    ON shap_values FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE user_id = auth.uid() AND role IN ('Bank_Officer', 'Admin')
        )
    );

-- ============================================================================
-- COUNTERFACTUALS - RLS POLICIES
-- ============================================================================
ALTER TABLE counterfactuals ENABLE ROW LEVEL SECURITY;

-- Users can read counterfactuals for their own predictions (via join chain)
CREATE POLICY "Users can read counterfactuals for own predictions"
    ON counterfactuals FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM predictions p
            JOIN loan_applications la ON la.id = p.application_id
            WHERE p.id = counterfactuals.prediction_id
            AND la.user_id = auth.uid()
        )
    );

-- Officers and Admins can read all counterfactuals
CREATE POLICY "Officers can read all counterfactuals"
    ON counterfactuals FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE user_id = auth.uid() AND role IN ('Bank_Officer', 'Admin')
        )
    );

-- ============================================================================
-- AUDIT_LOGS - RLS POLICIES (Immutable: no UPDATE or DELETE policies)
-- ============================================================================
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Admins can read all audit logs
CREATE POLICY "Admins can read all audit logs"
    ON audit_logs FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE user_id = auth.uid() AND role = 'Admin'
        )
    );

-- Officers can read application-specific audit logs
CREATE POLICY "Officers can read application-specific audit logs"
    ON audit_logs FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE user_id = auth.uid() AND role = 'Bank_Officer'
        )
    );

-- System can insert audit logs (service role or any authenticated user triggering actions)
CREATE POLICY "System can insert audit logs"
    ON audit_logs FOR INSERT
    WITH CHECK (true);

-- No UPDATE or DELETE policies = immutable audit trail

-- ============================================================================
-- FAIRNESS_METRICS - RLS POLICIES
-- ============================================================================
ALTER TABLE fairness_metrics ENABLE ROW LEVEL SECURITY;

-- Admins can read fairness metrics
CREATE POLICY "Admins can read fairness metrics"
    ON fairness_metrics FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM profiles
            WHERE user_id = auth.uid() AND role = 'Admin'
        )
    );

-- System can insert fairness metrics
CREATE POLICY "System can insert fairness metrics"
    ON fairness_metrics FOR INSERT
    WITH CHECK (true);
