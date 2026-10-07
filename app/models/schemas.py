from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ConversationMessage(BaseModel):
    role: str = Field(..., description="customer or agent")
    message: str = Field(..., min_length=1)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        allowed_roles = {"customer", "agent"}

        if value not in allowed_roles:
            raise ValueError("role must be either 'customer' or 'agent'")

        return value


class Customer(BaseModel):
    name: str = Field(..., min_length=1)
    phone: str = Field(..., min_length=5)


class LeadData(BaseModel):
    source: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1)
    created_at: datetime
    last_contacted_at: datetime | None = None


class LeadAnalyzeRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1)
    lead_id: str = Field(..., min_length=1)

    customer: Customer
    lead: LeadData

    conversation: list[ConversationMessage] = Field(
        ...,
        min_length=1,
    )


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Intent(str, Enum):
    INFORMATION = "information"
    PURCHASE = "purchase"
    DEMO = "demo"
    SUPPORT = "support"
    UNKNOWN = "unknown"


class LeadAnalysisResponse(BaseModel):
    lead_score: int = Field(..., ge=0, le=100)

    priority: Priority
    intent: Intent

    stage: str = Field(..., min_length=1)
    summary: str = Field(..., min_length=1)

    next_best_action: str = Field(..., min_length=1)

    follow_up_channel: str = Field(..., min_length=1)

    follow_up_message: str | None = None

    do_not_contact: bool = False


class AnalysisResponse(LeadAnalysisResponse):
    tenant_id: str
    lead_id: str
    created_at: datetime


class FollowUpResponse(BaseModel):
    tenant_id: str
    lead_id: str

    follow_up_channel: str

    follow_up_message: str | None

    do_not_contact: bool


class WebhookLeadEvent(BaseModel):
    event_id: str = Field(..., min_length=1)

    tenant_id: str = Field(..., min_length=1)
    lead_id: str = Field(..., min_length=1)

    customer: Customer
    lead: LeadData

    conversation: list[ConversationMessage] = Field(
        ...,
        min_length=1,
    )
