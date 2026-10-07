from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.database import WebhookEvent, get_db
from app.models.schemas import WebhookLeadEvent
from app.workers.lead_worker import process_lead_webhook

router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["Webhooks"],
)


@router.post("/leads", status_code=status.HTTP_202_ACCEPTED)
def receive_lead_webhook(
    event: WebhookLeadEvent,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Accept a lead webhook and process it in the background.

    event_id provides idempotency: duplicate webhook events
    are accepted without creating duplicate processing jobs.
    """

    existing_event = (
        db.query(WebhookEvent)
        .filter(WebhookEvent.event_id == event.event_id)
        .first()
    )

    if existing_event is not None:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "duplicate",
                "event_id": event.event_id,
                "processing_status": existing_event.status,
            },
        )

    webhook_event = WebhookEvent(
        tenant_id=event.tenant_id,
        event_id=event.event_id,
        lead_id=event.lead_id,
        status="pending",
    )

    try:
        db.add(webhook_event)
        db.commit()
        db.refresh(webhook_event)

    except IntegrityError:
        db.rollback()

        existing_event = (
            db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == event.event_id)
            .first()
        )

        if existing_event is not None:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "status": "duplicate",
                    "event_id": event.event_id,
                    "processing_status": existing_event.status,
                },
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register webhook event.",
        )

    background_tasks.add_task(
        process_lead_webhook,
        event.model_dump(mode="json"),
    )

    return {
        "status": "accepted",
        "event_id": event.event_id,
        "processing_status": "pending",
    }
