-- Migration: 00003_create_auth_trigger
-- Description: Create trigger to automatically create a profile row when a new user registers via Supabase Auth
-- Requirements: 1.1, 1.4

-- ============================================================================
-- FUNCTION: handle_new_user()
-- Automatically creates a profiles row with default 'Applicant' role
-- when a new user is inserted into auth.users
-- ============================================================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (user_id, name, role)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'name', NEW.email),
        'Applicant'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ============================================================================
-- TRIGGER: on_auth_user_created
-- Fires AFTER INSERT on auth.users to call handle_new_user()
-- ============================================================================
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
