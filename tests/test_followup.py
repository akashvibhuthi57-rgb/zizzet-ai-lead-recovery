from datetime import datetime

from app.models.database import Lead, LeadAnalysis


def create_lead(
    db_session,
    lead_id: str,
    tenant_id: str = "business_001",
):
    lead = Lead(
        tenant_id=tenant_id,
        lead_id=lead_id,
        customer_name="Test Customer",
        customer_phone="+919876543210",
        source="whatsapp",
        status="contacted",
        created_at=datetime(2026, 10, 6),
        last_contacted_at=datetime(2026, 10, 6),
        conversation_json='{"conversation":[]}',
    )

    db_session.add(lead)
    db_session.commit()

    return lead


def create_analysis(
    db_session,
    lead_id: str,
    tenant_id: str = "business_001",
    do_not_contact: bool = False,
):
    analysis = LeadAnalysis(
        tenant_id=tenant_id,
        lead_id=lead_id,
        lead_score=85,
        priority="high",
        intent="purchase",
        stage="pricing",
        summary="Customer is interested in the product.",
        next_best_action="Follow up with pricing information.",
        follow_up_channel="whatsapp",
        follow_up_message=(
            None
            if do_not_contact
            else "Hi! Here are the pricing details you requested."
        ),
        do_not_contact=do_not_contact,
        created_at=datetime(2026, 10, 6),
    )

    db_session.add(analysis)
    db_session.commit()

    return analysis


def test_followup_is_sent_for_contactable_lead(
    client,
    db_session,
    monkeypatch,
):
    create_lead(
        db_session,
        "lead_followup_001",
    )

    create_analysis(
        db_session,
        "lead_followup_001",
    )

    sent_messages = []

    def fake_send_message(
        channel: str,
        phone: str,
        message: str,
    ):
        sent_messages.append(
            {
                "channel": channel,
                "phone": phone,
                "message": message,
            }
        )

        return {"status": "sent"}

    monkeypatch.setattr(
        "app.services.followup_service.messaging_provider.send_message",
        fake_send_message,
    )

    response = client.post(
        "/api/v1/leads/lead_followup_001/follow-up",
        headers={"X-Tenant-ID": "business_001"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["do_not_contact"] is False
    assert data["follow_up_message"] == (
        "Hi! Here are the pricing details you requested."
    )

    assert len(sent_messages) == 1
    assert sent_messages[0]["channel"] == "whatsapp"
    assert sent_messages[0]["phone"] == "+919876543210"


def test_followup_is_blocked_for_opted_out_lead(
    client,
    db_session,
    monkeypatch,
):
    create_lead(
        db_session,
        "lead_followup_stop_001",
    )

    create_analysis(
        db_session,
        "lead_followup_stop_001",
        do_not_contact=True,
    )

    sent_messages = []

    def fake_send_message(
        channel: str,
        phone: str,
        message: str,
    ):
        sent_messages.append(message)
        return {"status": "sent"}

    monkeypatch.setattr(
        "app.services.followup_service.messaging_provider.send_message",
        fake_send_message,
    )

    response = client.post(
        "/api/v1/leads/lead_followup_stop_001/follow-up",
        headers={"X-Tenant-ID": "business_001"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["do_not_contact"] is True
    assert data["follow_up_message"] is None
    assert sent_messages == []
