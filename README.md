# Elventa — AI-Native Agentic Commerce

Elventa is an AI-native electronics storefront built for the **Razorpay Buildathon 2026** (AI Growth & Agentic Commerce track). A Buyer Agent turns natural-language requests into structured constraints, a Merchant Agent responds with ranked, explainable offers backed by a real Growth Engine (cross-sell, upsell, and promotion logic driven by co-purchase data), and every money action — cart validation, tiered authorization, Razorpay test-mode payment, and order fulfillment — is logged to a queryable audit trail. The result is an agentic commerce system where AI-driven revenue growth is bounded, explainable, and provably trustworthy, not a black box.

## Architecture

```
CUSTOMER
  → BUYER AGENT (parses intent → constraints, independently evaluates every offer against budget)
  → MERCHANT AGENT (searches catalog, ranks offers, calls Growth Engine)
    → Growth Engine (cross-sell / upsell / promotion, backed by co-purchase data)
  → CART (frozen pricing, revalidated before checkout)
  → POLICY ENGINE (auto-approve / confirm / explicit-auth, by amount)
  → RAZORPAY (test-mode payment, signature-verified)
  → ORDER + INVOICE
  → AUDIT TRAIL (every decision above, logged with a reason)
```

Every merchant suggestion — an add-on, a bundle, an upsell — is independently re-checked by the Buyer Agent against the customer's actual stated budget before it's shown as accepted. The merchant can propose; it cannot force.

## Tech stack

- **Backend:** Python, FastAPI
- **Database:** SQLite (via SQLAlchemy async)
- **LLM:** Ollama (llama3.1), with a deterministic regex fallback if unavailable
- **Payments:** Razorpay (test mode), signature-verified
- **Frontend:** Vanilla HTML/CSS/JS — no build step

## Project structure

```
backend/
  agents/        Buyer Agent, Merchant Agent, LLM client
  growth_engine/ Cross-sell/upsell/promotion logic + synthetic co-purchase data
  commerce/      Product catalog, cart, order, invoice, offer storage
  policy/        Authorization gate + input guardrails
  payments/      Razorpay integration
  audit/         Decision logging
  schemas/       Pydantic models
  seed/          Catalog seed data (laptops, monitors, GPUs, processors, mice, etc.)
  evaluation/    Baseline vs AI-assisted revenue evaluation script
  tests/         End-to-end smoke test
frontend/
  index.html     Full customer flow + merchant dashboard + audit trail viewer
```

## Setup

**Prerequisites:** Python 3.11+, [Ollama](https://ollama.com) (optional — falls back to regex parsing if not running), a free [Razorpay test-mode API key](https://dashboard.razorpay.com/app/keys).

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
```

Create `backend/.env`:
```
DATABASE_URL=sqlite+aiosqlite:///./app.db
RAZORPAY_KEY_ID=rzp_test_your_key
RAZORPAY_KEY_SECRET=your_secret
LLM_PROVIDER=ollama
LLM_MODEL=llama3.1
LLM_BASE_URL=http://localhost:11434
AUTO_APPROVE_MAX_INR=2000
USER_CONFIRM_MAX_INR=10000
```

Seed the catalog:
```bash
python -m backend.seed.seed_products
```

## Running

**Terminal 1 — backend:**
```bash
python -m uvicorn backend.main:app --reload
```

**Terminal 2 — frontend:**
```bash
cd frontend
python -m http.server 5500
```

Open `http://localhost:5500/index.html`.

## Testing

```bash
python -m backend.tests.e2e_smoke_test          # full flow, API-level
python -m backend.evaluation.evaluate_growth_engine   # revenue uplift measurement
```

## Measured impact

The Growth Engine's effect is measured, not asserted — `evaluate_growth_engine.py` runs a fixed synthetic buyer population through the real Merchant Agent and Growth Engine code, comparing baseline revenue (base product only) against AI-assisted revenue (with cross-sell, upsell, and promotion applied):

```
[paste your evaluation script's actual output block here]
```

## Design notes

- Medusa was evaluated as the commerce backend but dropped after persistent install/runtime issues on Windows; replaced with a custom SQLite-backed service behind the same `CommerceService` abstraction, so the swap touched only one adapter file.
- Test-mode payments use Razorpay's UPI test identifiers (`success@razorpay` / `failure@razorpay`) for reliable success/failure demonstration.
- A formal state-machine module was intentionally descoped given the timeline; equivalent ordering is enforced by each checkout endpoint re-validating cart state before proceeding.