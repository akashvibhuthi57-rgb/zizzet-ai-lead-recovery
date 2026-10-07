from sqlalchemy.orm import Session

from app.models.database import Lead, LeadAnalysis
from app.services.messaging import messaging_provider


class FollowUpServiceError(Exception):
    """Raised when a follow-up cannot be processed."""


def send_follow_up(
    db: Session,
    tenant_id: str,
    lead_id: str,
) -> dict:
    """
    Send the latest approved follow-up for a lead.

    Tenant ID is always used when looking up the lead and analysis.
    Opted-out leads are never contacted.
    """

    lead = (
        db.query(Lead)
        .filter(
            Lead.tenant_id == tenant_id,
            Lead.lead_id == lead_id,
        )
        .first()
    )

    if lead is None:
        raise FollowUpServiceError("Lead not found.")

    analysis = (
        db.query(LeadAnalysis)
        .filter(
            LeadAnalysis.tenant_id == tenant_id,
            LeadAnalysis.lead_id == lead_id,
        )
        .order_by(LeadAnalysis.created_at.desc())
        .first()
    )

    if analysis is None:
        raise FollowUpServiceError(
            "Lead analysis not found."
        )

    # Never send a message to an opted-out customer.
    if analysis.do_not_contact:
        return {
            "tenant_id": tenant_id,
            "lead_id": lead_id,
            "follow_up_channel": analysis.follow_up_channel,
            "follow_up_message": None,
            "do_not_contact": True,
        }

    # No message means there is nothing safe to send.
    if not analysis.follow_up_message:
        raise FollowUpServiceError(
            "No follow-up message is available."
        )

    messaging_provider.send_message(
        channel=analysis.follow_up_channel,
        phone=lead.customer_phone,
        message=analysis.follow_up_message,
    )

    return {
        "tenant_id": tenant_id,
        "lead_id": lead_id,
        "follow_up_channel": analysis.follow_up_channel,
        "follow_up_message": analysis.follow_up_message,
        "do_not_contact": False,
    }
