"""
Supabase client initialization for the AI Loan Decision Support Platform.

Provides two client factories:
- get_supabase_client(): Uses the service role key (bypasses RLS) for backend operations
- get_supabase_anon_client(): Uses the anon key (respects RLS) for user-scoped operations
"""

from supabase import Client, create_client

from app.config import settings


def get_supabase_client() -> Client:
    """Return a Supabase client using the service role key.

    This client bypasses Row Level Security and should be used for
    backend operations that need unrestricted database access
    (e.g., admin queries, audit logging, prediction storage).
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_supabase_anon_client() -> Client:
    """Return a Supabase client using the anon/public key.

    This client respects Row Level Security policies and should be used
    for operations where access control should be enforced at the database level.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
