import logging

from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger(__name__)

_supabase: Client | None = None


def get_supabase() -> Client:
    """Server-side Supabase client (used only for Storage operations).

    Prefers the service-role key: reads/writes on a *private* bucket are
    denied for the anon key by Storage RLS, which surfaces as a 500 on
    upload. The server is a trusted backend, so service-role is the correct
    credential here. Falls back to the anon key (with a warning) only so the
    app still boots if the secret is unset -- uploads will keep failing until
    SUPABASE_SERVICE_ROLE_KEY is configured.
    """
    global _supabase
    if _supabase is None:
        key = settings.SUPABASE_SERVICE_ROLE_KEY
        if not key:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY not set; falling back to the anon "
                "key. Storage operations on a private bucket will fail until "
                "the service-role key is configured."
            )
            key = settings.SUPABASE_ANON_KEY
        _supabase = create_client(settings.SUPABASE_URL, key)
    return _supabase
