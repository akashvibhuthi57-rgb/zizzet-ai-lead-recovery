from datetime import datetime

from app.models.database import (
    Lead,
    LeadAnalysis,
    SessionLocal,
    WebhookEvent,
)
from app.models.schemas import WebhookLeadEvent
from app.services.ai_service import AIServiceError, ai_service


def process_lead_webhook(event_data: dict) -> None:
    """
    Process a lead webhook in the background.

    The webhook event status is updated throughout processing so that
    failures are visible and the event remains idempotent.
    """

    db = SessionLocal()

    try:
        event = WebhookLeadEvent.model_validate(event_data)

        webhook_event = (
            db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == event.event_id)
            .first()
        )

        if webhook_event is None:
            return

        webhook_event.status = "processing"
        db.commit()

        # Create or update the lead within the correct tenant.
        lead = (
            db.query(Lead)
            .filter(
                Lead.tenant_id == event.tenant_id,
                Lead.lead_id == event.lead_id,
            )
            .first()
        )

        conversation_json = WebhookLeadEvent.model_validate(
            event_data
        ).model_dump_json(
            include={"conversation"}
        )

        if lead is None:
            lead = Lead(
                tenant_id=event.tenant_id,
                lead_id=event.lead_id,
                customer_name=event.customer.name,
                customer_phone=event.customer.phone,
                source=event.lead.source,
                status=event.lead.status,
                created_at=event.lead.created_at,
                last_contacted_at=event.lead.last_contacted_at,
                conversation_json=conversation_json,
            )
            db.add(lead)

        else:
            lead.customer_name = event.customer.name
            lead.customer_phone = event.customer.phone
            lead.source = event.lead.source
            lead.status = event.lead.status
            lead.created_at = event.lead.created_at
            lead.last_contacted_at = event.lead.last_contacted_at
            lead.conversation_json = conversation_json

        db.commit()
        db.refresh(lead)

        # Run AI analysis.
        analysis = ai_service.analyze_lead(
            customer=event.customer.model_dump(),
            lead=event.lead.model_dump(mode="json"),
            conversation=[
                message.model_dump()
                for message in event.conversation
            ],
        )

        # Store the analysis.
        db_analysis = LeadAnalysis(
            tenant_id=event.tenant_id,
            lead_id=event.lead_id,
            lead_score=analysis.lead_score,
            priority=analysis.priority.value,
            intent=analysis.intent.value,
            stage=analysis.stage,
            summary=analysis.summary,
            next_best_action=analysis.next_best_action,
            follow_up_channel=analysis.follow_up_channel,
            follow_up_message=analysis.follow_up_message,
            do_not_contact=analysis.do_not_contact,
            created_at=datetime.utcnow(),
        )

        db.add(db_analysis)

        webhook_event.status = "completed"

        db.commit()

    except AIServiceError:
        db.rollback()

        webhook_event = (
            db.query(WebhookEvent)
            .filter(
                WebhookEvent.event_id == event_data.get("event_id")
            )
            .first()
        )

        if webhook_event is not None:
            webhook_event.status = "failed"
            db.commit()

    except Exception:
        db.rollback()

        webhook_event = (
            db.query(WebhookEvent)
            .filter(
                WebhookEvent.event_id == event_data.get("event_id")
            )
            .first()
        )

        if webhook_event is not None:
            webhook_event.status = "failed"
            db.commit()

    finally:
        db.close()
