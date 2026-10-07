# Zizzet AI Lead Recovery Engine

## 🚀 Live Demo

**Live API / Swagger Demo:**  
https://zizzet-ai-lead-recovery.onrender.com

The live demo opens the interactive Swagger UI for testing all API endpoints.

AI-powered backend for identifying high-intent and inactive leads, analyzing conversations, recommending the next best action, and generating personalized follow-ups.

Built for the Zizzet AI Backend Developer Intern technical screening task.

## Features

- Lead analysis with Gemini
- Structured AI output with Pydantic
- Lead score, priority, intent, stage, summary, and next-best-action
- Personalized follow-up generation
- Deterministic STOP/opt-out protection
- Tenant isolation
- Webhook ingestion and background processing
- Webhook idempotency using event_id
- Mock messaging provider
- LLM retry with exponential backoff
- SQLite for local development
- Automated tests
- Swagger/OpenAPI documentation

## API Endpoints

### Analyze a lead
POST /api/v1/leads/analyze

Request body contains tenant_id, lead_id, customer, lead metadata, and conversation messages.

### Get latest analysis
GET /api/v1/leads/{lead_id}/analysis

Required header:
X-Tenant-ID: business_001

### Send follow-up
POST /api/v1/leads/{lead_id}/follow-up

Required header:
X-Tenant-ID: business_001

The endpoint uses the latest stored analysis and the mock messaging provider.
For opted-out leads, no message is sent.

### Lead webhook
POST /api/v1/webhooks/leads

Webhooks are accepted and processed in the background.
event_id is used to prevent duplicate processing.

## AI Approach

The application sends customer details, lead metadata, and conversation history to Gemini.
The model is instructed to return structured JSON containing lead score, priority, intent, stage, summary, next best action, follow-up channel, follow-up message, and do_not_contact.

The response is parsed as JSON and validated with the Pydantic LeadAnalysisResponse schema.

Temporary LLM failures are retried up to three times using exponential backoff.

STOP and explicit opt-out messages are detected before the LLM request. This guarantees that opted-out customers are not contacted even when the LLM is unavailable.

## Testing

Run the complete test suite:

pytest -q

The project currently contains 10 automated tests covering:
- Lead analysis
- Tenant isolation
- Webhook acceptance
- Webhook idempotency
- Normal follow-up
- STOP follow-up protection
- Structured JSON parsing
- Invalid JSON handling
- STOP detection before LLM calls

## Local Setup

Requirements:
- Python 3.10+
- Gemini API key
- Docker optional

Create and activate the virtual environment:

python3 -m venv venv
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt

Create the environment file:

cp .env.example .env

Set your Gemini API key in .env.

Start the API:

uvicorn app.main:app --reload

Swagger UI:
http://127.0.0.1:8000/docs

Health check:
GET /health

## Environment Variables

APP_NAME - Application name
DATABASE_URL - SQLAlchemy database URL
GEMINI_API_KEY - Gemini API key
GEMINI_MODEL - Gemini model name

Never commit .env or real API keys.

## Docker

Build and start the application:

docker compose up --build

The API will be available at http://127.0.0.1:8000

## Tenant Isolation

Protected analysis and follow-up operations use the X-Tenant-ID header and query records using tenant_id together with lead_id.

X-Tenant-ID represents the resolved tenant context in this screening implementation. Authentication and authorization are outside the scope of this feature.

## Assumptions

- SQLite is used for local reproducibility.
- A mock messaging provider is used instead of a real messaging service.
- FastAPI BackgroundTasks is used for webhook processing.
- X-Tenant-ID represents the tenant context.

## Limitations

- SQLite is not intended for production-scale concurrent workloads.
- FastAPI BackgroundTasks is suitable for this screening implementation; a durable queue such as Redis/ARQ would be stronger for production.
- No authentication or authorization system is included.
- Messaging delivery is mocked.
- LLM availability and output quality depend on the configured Gemini service.

## Architecture

FastAPI
  ↓
Request validation with Pydantic
  ↓
Lead / webhook persistence with SQLAlchemy + SQLite
  ↓
AI service using Gemini
  ↓
Structured JSON parsing + Pydantic validation
  ↓
Lead analysis persistence
  ↓
Follow-up service / mock messaging provider

Webhook flow:

Webhook
  ↓
Idempotency check
  ↓
FastAPI BackgroundTasks
  ↓
AI analysis
  ↓
Database persistence
