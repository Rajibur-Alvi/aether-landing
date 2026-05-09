"""
Payment router — Lemon Squeezy integration.

Setup steps (one-time, no code required):
1. Create a free account at https://app.lemonsqueezy.com
2. Create a Store → copy your Store ID
3. Create two Products:
      "Signal"      → $29/month subscription  → copy the Variant ID
      "Signal Pro"  → $99/month subscription  → copy the Variant ID
4. Go to Settings → API → create an API key
5. Set these env vars on Render:
      LEMONSQUEEZY_API_KEY
      LEMONSQUEEZY_STORE_ID
      LEMONSQUEEZY_SIGNAL_VARIANT_ID
      LEMONSQUEEZY_SIGNAL_PRO_VARIANT_ID
      APP_URL  (your Vercel frontend URL, e.g. https://yourapp.vercel.app)
6. In Lemon Squeezy → Settings → Webhooks, add:
      URL: https://your-render-url.onrender.com/api/webhook/lemonsqueezy
      Events: order_created, subscription_created, subscription_updated
"""

import httpx
from fastapi import APIRouter, HTTPException, Request
from config import get_settings

router = APIRouter(tags=["Payments"])

_LS_BASE = "https://api.lemonsqueezy.com/v1"


def _ls_headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }


async def _create_checkout(variant_id: str, user_email: str | None = None) -> str:
    """
    Create a Lemon Squeezy hosted checkout and return the checkout URL.
    Card data never touches your server — Lemon Squeezy handles everything.
    """
    settings = get_settings()

    if not settings.lemonsqueezy_api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "Payment system not configured. "
                "Set LEMONSQUEEZY_API_KEY on your Render dashboard."
            ),
        )

    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_options": {
                    "embed": False,
                    "media": True,
                    "logo": True,
                },
                "checkout_data": {
                    **({"email": user_email} if user_email else {}),
                },
                "product_options": {
                    "redirect_url": f"{settings.app_url}/dashboard.html?payment=success",
                    "receipt_button_text": "Go to Dashboard",
                    "receipt_thank_you_note": "Welcome to Aether. Your account is now active.",
                },
            },
            "relationships": {
                "store": {
                    "data": {
                        "type": "stores",
                        "id": str(settings.lemonsqueezy_store_id),
                    }
                },
                "variant": {
                    "data": {
                        "type": "variants",
                        "id": str(variant_id),
                    }
                },
            },
        }
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_LS_BASE}/checkouts",
            json=payload,
            headers=_ls_headers(settings.lemonsqueezy_api_key),
        )

    if resp.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail=f"Lemon Squeezy error: {resp.text}",
        )

    checkout_url: str = resp.json()["data"]["attributes"]["url"]
    return checkout_url


@router.post("/checkout/signal")
async def checkout_signal(request: Request):
    """Create checkout for Signal plan ($29/month)."""
    settings = get_settings()

    if not settings.lemonsqueezy_signal_variant_id:
        raise HTTPException(
            status_code=503,
            detail="Signal variant not configured. Set LEMONSQUEEZY_SIGNAL_VARIANT_ID.",
        )

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    url = await _create_checkout(
        variant_id=settings.lemonsqueezy_signal_variant_id,
        user_email=body.get("email"),
    )
    return {"checkout_url": url}


@router.post("/checkout/signal-pro")
async def checkout_signal_pro(request: Request):
    """Create checkout for Signal Pro plan ($99/month)."""
    settings = get_settings()

    if not settings.lemonsqueezy_signal_pro_variant_id:
        raise HTTPException(
            status_code=503,
            detail="Signal Pro variant not configured. Set LEMONSQUEEZY_SIGNAL_PRO_VARIANT_ID.",
        )

    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    url = await _create_checkout(
        variant_id=settings.lemonsqueezy_signal_pro_variant_id,
        user_email=body.get("email"),
    )
    return {"checkout_url": url}


@router.post("/webhook/lemonsqueezy")
async def lemon_squeezy_webhook(request: Request):
    """
    Receive Lemon Squeezy order/subscription webhooks.
    Upgrades the user's plan in Supabase when payment is confirmed.
    Configure the webhook URL in Lemon Squeezy → Settings → Webhooks.
    """
    from services.supabase_service import get_supabase

    payload = await request.json()
    event = payload.get("meta", {}).get("event_name", "")
    data = payload.get("data", {})
    attributes = data.get("attributes", {})

    settings = get_settings()
    variant_map = {
        settings.lemonsqueezy_signal_variant_id: "signal",
        settings.lemonsqueezy_signal_pro_variant_id: "signal_pro",
    }

    if event in ("order_created", "subscription_created", "subscription_updated"):
        variant_id = str(
            attributes.get("first_order_item", {}).get("variant_id", "")
            or attributes.get("variant_id", "")
        )
        user_email = (
            attributes.get("user_email")
            or attributes.get("customer_email")
            or ""
        )
        plan = variant_map.get(variant_id, "signal")
        status = attributes.get("status", "active")

        if user_email:
            try:
                sb = get_supabase()
                # Look up the user by the email column we store in user_profiles.
                # This avoids the slow/unreliable auth.admin.list_users() call.
                sb.table("user_profiles").update({
                    "plan": plan,
                    "subscription_status": status,
                }).eq("email", user_email).execute()
            except Exception:
                pass  # Must return 200 even on partial failures

    return {"received": True}
