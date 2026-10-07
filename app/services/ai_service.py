import json
import re
import time
from google import genai

from app.core.config import settings
from app.models.schemas import LeadAnalysisResponse


class AIServiceError(Exception):
    """Raised when the AI service cannot produce valid output."""


class GeminiAIService:
    def __init__(self) -> None:
        if not settings.GEMINI_API_KEY:
            raise AIServiceError(
                "GEMINI_API_KEY is not configured."
            )

        self.client = genai.Client(
            api_key=settings.GEMINI_API_KEY
        )

        self.model = settings.GEMINI_MODEL

    def analyze_lead(
        self,
        customer: dict,
        lead: dict,
        conversation: list[dict],
    ) -> LeadAnalysisResponse:
        if self._has_opted_out(conversation):
            return LeadAnalysisResponse(
                lead_score=0,
                priority="low",
                intent="unknown",
                stage="opted_out",
                summary="Customer has opted out of further contact.",
                next_best_action="Do not contact this customer.",
                follow_up_channel=str(
                    lead.get("source") or "whatsapp"
                ),
                follow_up_message=None,
                do_not_contact=True,
            )

        prompt = self._build_prompt(
            customer=customer,
            lead=lead,
            conversation=conversation,
        )

        response = None
        last_error = None

        for attempt in range(3):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config={
                        "temperature": 0.2,
                        "response_mime_type": "application/json",
                    },
                )

                break

            except Exception as exc:
                last_error = exc

                if attempt < 2:
                    time.sleep(2 ** attempt)
                else:
                    raise AIServiceError(
                        f"LLM request failed after 3 attempts: {exc}"
                    ) from exc

        if not response.text:
            raise AIServiceError(
                "LLM returned an empty response."
            )

        try:
            data = self._parse_json(response.text)

            return LeadAnalysisResponse.model_validate(data)

        except Exception as exc:
            raise AIServiceError(
                f"LLM returned malformed structured output: {exc}"
            ) from exc
    @staticmethod
    def _has_opted_out(
        conversation: list[dict],
    ) -> bool:
        opt_out_patterns = (
            r"\bstop\b",
            r"\bunsubscribe\b",
            r"do\s+not\s+contact\s+me",
            r"don't\s+contact\s+me",
            r"do\s+not\s+message\s+me",
            r"don't\s+message\s+me",
        )

        for message in conversation:
            if message.get("role") != "customer":
                continue

            text = message.get("message", "")

            for pattern in opt_out_patterns:
                if re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                ):
                    return True

        return False
    @staticmethod
    def _build_prompt(
        customer: dict,
        lead: dict,
        conversation: list[dict],
    ) -> str:

        conversation_text = "\n".join(
            f"{message['role']}: {message['message']}"
            for message in conversation
        )

        return f"""
You are an AI lead recovery engine for a business CRM.

Analyze the customer, lead metadata, and conversation.

Your goal is to determine:
- lead score from 0 to 100
- priority
- purchase intent
- current sales stage
- concise summary
- next best action
- follow-up channel
- personalized follow-up message
- whether the customer must not be contacted

IMPORTANT:
If the customer says STOP, unsubscribe, do not contact me,
don't message me again, or clearly opts out:

- do_not_contact must be true
- follow_up_message must be null
- do not recommend contacting the customer

Otherwise, recommend an appropriate follow-up.

Use these priority values:
low, medium, high

Use these intent values:
information, purchase, demo, support, unknown

Return ONLY valid JSON matching this exact structure:

{{
    "lead_score": 0,
    "priority": "low",
    "intent": "unknown",
    "stage": "unknown",
    "summary": "string",
    "next_best_action": "string",
    "follow_up_channel": "whatsapp",
    "follow_up_message": "string or null",
    "do_not_contact": false
}}

Customer:
{json.dumps(customer)}

Lead:
{json.dumps(lead)}

Conversation:
{conversation_text}
"""

    @staticmethod
    def _parse_json(text: str) -> dict:

        text = text.strip()

        # Remove accidental markdown code fences.
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        try:
            return json.loads(text)

        except json.JSONDecodeError as exc:
            raise ValueError(
                "Response was not valid JSON."
            ) from exc


ai_service = GeminiAIService()
