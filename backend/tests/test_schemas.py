from datetime import datetime, timezone

from models.schemas import ChatRequest, UserProfileResponse


def test_chat_request_accepts_frontend_model_option_labels():
    request = ChatRequest.model_validate({
        "message": "Summarize this document",
        "model": "fast",
    })

    assert request.model.value == "fast"


def test_user_profile_response_includes_billing_fields_used_by_dashboard():
    profile = UserProfileResponse.model_validate({
        "id": "00000000-0000-0000-0000-000000000001",
        "username": None,
        "full_name": None,
        "avatar_url": None,
        "entropy_level": 50,
        "ghost_mode": False,
        "theme": "entropy",
        "plan": "signal",
        "subscription_status": "active",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    dumped = profile.model_dump()
    assert dumped["plan"] == "signal"
    assert dumped["subscription_status"] == "active"
