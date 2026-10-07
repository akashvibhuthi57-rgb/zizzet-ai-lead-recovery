import pytest

from app.models.schemas import LeadAnalysisResponse
from app.services.ai_service import AIServiceError, GeminiAIService


def test_parse_valid_json():
    response = GeminiAIService._parse_json(
        """
        {
            "lead_score": 80,
            "priority": "high",
            "intent": "purchase",
            "stage": "pricing",
            "summary": "Customer wants pricing.",
            "next_best_action": "Send pricing details.",
            "follow_up_channel": "whatsapp",
            "follow_up_message": "Here are the pricing details.",
            "do_not_contact": false
        }
        """
    )

    validated = LeadAnalysisResponse.model_validate(response)

    assert validated.lead_score == 80
    assert validated.priority.value == "high"
    assert validated.intent.value == "purchase"


def test_parse_json_rejects_invalid_json():
    with pytest.raises(ValueError):
        GeminiAIService._parse_json(
            '{"lead_score": 80, invalid-json}'
        )


def test_opt_out_is_handled_without_llm_call(
    monkeypatch,
):
    service = object.__new__(GeminiAIService)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("LLM should not be called for STOP.")

    monkeypatch.setattr(
        service,
        "_build_prompt",
        fail_if_called,
    )

    result = service.analyze_lead(
        customer={
            "name": "Test Customer",
            "phone": "+919876543210",
        },
        lead={
            "source": "whatsapp",
            "status": "contacted",
            "created_at": "2026-10-06T00:00:00",
            "last_contacted_at": "2026-10-06T00:00:00",
        },
        conversation=[
            {
                "role": "customer",
                "message": "STOP",
            }
        ],
    )

    assert result.do_not_contact is True
    assert result.follow_up_message is None
    assert result.stage == "opted_out"
