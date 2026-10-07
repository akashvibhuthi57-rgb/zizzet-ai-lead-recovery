from app.models.schemas import LeadAnalysisResponse


def mock_ai_analysis():
    return LeadAnalysisResponse(
        lead_score=85,
        priority="high",
        intent="purchase",
        stage="pricing",
        summary="Customer is interested in the CRM and asked about pricing.",
        next_best_action="Follow up with pricing and schedule a sales call.",
        follow_up_channel="whatsapp",
        follow_up_message="Hi Arun, thanks for your interest in our CRM. I can share the pricing details and help you choose the right plan.",
        do_not_contact=False,
    )


def test_analyze_lead_success(client, monkeypatch):
    def fake_analyze_lead(
        customer,
        lead,
        conversation,
    ):
        return mock_ai_analysis()

    monkeypatch.setattr(
        "app.api.leads.ai_service.analyze_lead",
        fake_analyze_lead,
    )

    payload = {
        "tenant_id": "business_001",
        "lead_id": "lead_test_001",
        "customer": {
            "name": "Arun Kumar",
            "phone": "+919876543210",
        },
        "lead": {
            "source": "whatsapp",
            "status": "contacted",
            "created_at": "2026-10-06T00:00:00",
            "last_contacted_at": "2026-10-06T00:00:00",
        },
        "conversation": [
            {
                "role": "customer",
                "message": "I am interested in your CRM.",
            },
            {
                "role": "customer",
                "message": "What is the pricing?",
            },
        ],
    }

    response = client.post(
        "/api/v1/leads/analyze",
        json=payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["tenant_id"] == "business_001"
    assert data["lead_id"] == "lead_test_001"
    assert data["lead_score"] == 85
    assert data["priority"] == "high"
    assert data["intent"] == "purchase"
    assert data["do_not_contact"] is False


def test_tenant_isolation(client, monkeypatch):
    def fake_analyze_lead(
        customer,
        lead,
        conversation,
    ):
        return mock_ai_analysis()

    monkeypatch.setattr(
        "app.api.leads.ai_service.analyze_lead",
        fake_analyze_lead,
    )

    payload = {
        "tenant_id": "business_001",
        "lead_id": "lead_test_002",
        "customer": {
            "name": "Test Customer",
            "phone": "+919876543220",
        },
        "lead": {
            "source": "whatsapp",
            "status": "contacted",
            "created_at": "2026-10-06T00:00:00",
            "last_contacted_at": "2026-10-06T00:00:00",
        },
        "conversation": [
            {
                "role": "customer",
                "message": "Tell me about your product.",
            }
        ],
    }

    create_response = client.post(
        "/api/v1/leads/analyze",
        json=payload,
    )

    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/leads/lead_test_002/analysis",
        headers={"X-Tenant-ID": "business_002"},
    )

    assert response.status_code == 404

def test_analyze_lead_llm_failure(client, monkeypatch):
    def fake_analyze_lead(
        customer,
        lead,
        conversation,
    ):
        from app.services.ai_service import AIServiceError

        raise AIServiceError("LLM request failed after 3 attempts.")

    monkeypatch.setattr(
        "app.api.leads.ai_service.analyze_lead",
        fake_analyze_lead,
    )

    payload = {
        "tenant_id": "business_001",
        "lead_id": "lead_llm_failure_001",
        "customer": {
            "name": "Test Customer",
            "phone": "+919876543210",
        },
        "lead": {
            "source": "whatsapp",
            "status": "contacted",
            "created_at": "2026-10-06T00:00:00",
            "last_contacted_at": "2026-10-06T00:00:00",
        },
        "conversation": [
            {
                "role": "customer",
                "message": "I want to know more about your product.",
            }
        ],
    }

    response = client.post(
        "/api/v1/leads/analyze",
        json=payload,
    )

    assert response.status_code == 502
    assert "LLM request failed" in response.json()["detail"]
