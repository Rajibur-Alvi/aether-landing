from supabase import create_client, Client
from config import get_settings
import httpx

_client: Client | None = None


def get_supabase() -> Client:
    """Return singleton Supabase client using service_role key."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


async def refresh_user_token(refresh_token: str) -> dict:
    """Refresh a user's Supabase token server-side if needed."""
    settings = get_settings()
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"{settings.supabase_url}/auth/v1/token?grant_type=refresh_token",
            headers={
                "apikey": settings.supabase_service_key,
                "Content-Type": "application/json",
            },
            json={"refresh_token": refresh_token},
        )
        return resp.json()
