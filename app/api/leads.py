from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.models.database import Lead, LeadAnalysis, get_db
from app.models.schemas import (
    AnalysisResponse,
    FollowUpResponse,
    LeadAnalyzeRequest,
)
from app.services.ai_service import AIServiceError, ai_service
from app.services.followup_service import (
    FollowUpServiceError,
    send_follow_up,
)

router = APIRouter(
    prefix="/api/v1/leads",
    tags=["Leads"],
)


@router.post(
    "/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def analyze_lead(
    request: LeadAnalyzeRequest,
    db: Session = Depends(get_db),
):
    """
    Analyze a lead and its conversation using Gemini.
    """

    try:
        # Check whether this lead already exists
        lead = (
            db.query(Lead)
            .filter(
                Lead.tenant_id == request.tenant_id,
                Lead.lead_id == request.lead_id,
            )
            .first()
        )

        # Create or update lead
        if lead is None:
            lead = Lead(
                tenant_id=request.tenant_id,
                lead_id=request.lead_id,
                customer_name=request.customer.name,
                customer_phone=request.customer.phone,
                source=request.lead.source,
                status=request.lead.status,
                created_at=request.lead.created_at,
                last_contacted_at=request.lead.last_contacted_at,
                conversation_json=request.model_dump_json(
                    include={"conversation"}
                ),
            )

            db.add(lead)

        else:
            lead.customer_name = request.customer.name
            lead.customer_phone = request.customer.phone
            lead.source = request.lead.source
            lead.status = request.lead.status
            lead.last_contacted_at = request.lead.last_contacted_at
            lead.conversation_json = request.model_dump_json(
                include={"conversation"}
            )

        db.commit()
        db.refresh(lead)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save lead.",
        ) from exc

    # Run AI analysis
    try:
        analysis = ai_service.analyze_lead(
            customer=request.customer.model_dump(),
            lead=request.lead.model_dump(mode="json"),
            conversation=[
                message.model_dump()
                for message in request.conversation
            ],
        )

    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    # Store analysis
    try:
        db_analysis = LeadAnalysis(
            tenant_id=request.tenant_id,
            lead_id=request.lead_id,
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
        db.commit()
        db.refresh(db_analysis)

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save lead analysis.",
        ) from exc

    return AnalysisResponse(
        tenant_id=db_analysis.tenant_id,
        lead_id=db_analysis.lead_id,
        lead_score=db_analysis.lead_score,
        priority=db_analysis.priority,
        intent=db_analysis.intent,
        stage=db_analysis.stage,
        summary=db_analysis.summary,
        next_best_action=db_analysis.next_best_action,
        follow_up_channel=db_analysis.follow_up_channel,
        follow_up_message=db_analysis.follow_up_message,
        do_not_contact=db_analysis.do_not_contact,
        created_at=db_analysis.created_at,
    )
@router.get(
    "/{lead_id}/analysis",
    response_model=AnalysisResponse,
)
def get_lead_analysis(
    lead_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
):
    """
    Get the latest analysis for a lead within the requested tenant.
    """

    analysis = (
        db.query(LeadAnalysis)
        .filter(
            LeadAnalysis.tenant_id == x_tenant_id,
            LeadAnalysis.lead_id == lead_id,
        )
        .order_by(LeadAnalysis.created_at.desc())
        .first()
    )

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead analysis not found.",
        )

    return AnalysisResponse(
        tenant_id=analysis.tenant_id,
        lead_id=analysis.lead_id,
        lead_score=analysis.lead_score,
        priority=analysis.priority,
        intent=analysis.intent,
        stage=analysis.stage,
        summary=analysis.summary,
        next_best_action=analysis.next_best_action,
        follow_up_channel=analysis.follow_up_channel,
        follow_up_message=analysis.follow_up_message,
        do_not_contact=analysis.do_not_contact,
        created_at=analysis.created_at,
    )
@router.post(
    "/{lead_id}/follow-up",
    response_model=FollowUpResponse,
)
def create_follow_up(
    lead_id: str,
    x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    db: Session = Depends(get_db),
):
    """
    Send the latest approved follow-up for a lead.
    """

    try:
        return send_follow_up(
            db=db,
            tenant_id=x_tenant_id,
            lead_id=lead_id,
        )

    except FollowUpServiceError as exc:
        detail = str(exc)

        if detail == "Lead not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        if detail == "Lead analysis not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=detail,
            ) from exc

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc
