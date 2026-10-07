def webhook_payload(event_id: str) -> dict:
    return {
        "event_id": event_id,
        "tenant_id": "business_001",
        "lead_id": "lead_webhook_test_001",
        "customer": {
            "name": "Rahul Sharma",
            "phone": "+919876543211",
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


def test_webhook_accepts_new_event(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.webhooks.process_lead_webhook",
        lambda event_data: None,
    )

    response = client.post(
        "/api/v1/webhooks/leads",
        json=webhook_payload("event_test_001"),
    )

    assert response.status_code == 202

    data = response.json()

    assert data["status"] == "accepted"
    assert data["event_id"] == "event_test_001"
    assert data["processing_status"] == "pending"


def test_duplicate_webhook_is_idempotent(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.webhooks.process_lead_webhook",
        lambda event_data: None,
    )

    payload = webhook_payload("event_duplicate_001")

    first_response = client.post(
        "/api/v1/webhooks/leads",
        json=payload,
    )

    second_response = client.post(
        "/api/v1/webhooks/leads",
        json=payload,
    )

    assert first_response.status_code == 202
    assert second_response.status_code == 200

    data = second_response.json()

    assert data["status"] == "duplicate"
    assert data["event_id"] == "event_duplicate_001"
    assert data["processing_status"] == "pending"
