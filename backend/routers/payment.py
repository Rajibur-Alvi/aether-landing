import stripe
from fastapi import APIRouter, HTTPException
from config import get_settings

router = APIRouter()
settings = get_settings()

# Set Stripe API key
stripe.api_key = settings.stripe_secret_key

@router.post("/create-checkout-session")
async def create_checkout_session(product: str):
    """Create a Stripe Checkout session for subscription."""
    if product == "signal_pro":
        price_id = settings.stripe_signal_pro_price_id  # Placeholder
    elif product == "aether_core":
        price_id = settings.stripe_aether_core_price_id  # Placeholder
    else:
        raise HTTPException(status_code=400, detail="Invalid product")

    try:
        if settings.stripe_secret_key == "sk_test_placeholder":
            raise HTTPException(
                status_code=400,
                detail="Stripe is not configured. Please set your STRIPE_SECRET_KEY in the .env file.",
            )
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url="https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url="https://yourdomain.com/cancel",
        )
        return {"checkout_url": session.url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))