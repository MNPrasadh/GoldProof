# GoldProof — AI-Powered Gold Exchange Intelligence & Verifiable Trust Platform

> **"Make every gold exchange transparent, explainable, accountable and verifiable."**

GoldProof is a mobile-first, voice-enabled Progressive Web Application (PWA) built for Indian jewellery businesses and customers. It combines transparent 24K equivalent valuation math, neutral rule-based and machine-learning Deduction Intelligence, a Tamil & English voice-first AI assistant grounded strictly in recorded evidence, human-verified OCR extraction, low-connectivity offline draft queuing, and cryptographically signed Digital Gold Passports (SHA-256 + Ed25519 + QR).

---

## Architecture Overview

| Layer | Technology & Responsibilities |
| :--- | :--- |
| **Frontend PWA** (`frontend/`) | Next.js 15 (App Router, TypeScript), Tailwind CSS v4, Lucide icons, Recharts, Web Speech API (`ta-IN` / `en-IN`), Service Worker static-asset shell caching (`public/sw.js`), and offline draft sync queue (`localStorage`). |
| **Backend API** (`backend/`) | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT (`HS256`) + `bcrypt` RBAC & strict shop tenant isolation. |
| **AI & Document Intelligence** | Deterministic policy validation rules + `scikit-learn` `IsolationForest` (activated strictly on `>= 15` non-demo shop transactions), evidence-grounded Tamil/English assistant (configurable OpenAI-compatible LLM or clearly labelled `local_evidence_explainer`), and PaddleOCR / clearly labelled `MockOCRAdapter` requiring human confirmation. |
| **Cryptographic Trust Layer** | Canonical JSON serialization, SHA-256 hashing, Ed25519 digital signatures (`cryptography`), QR PNG generation (`qrcode` + `Pillow`), versioned immutable amendments, and SHA-256 hash-chained append-only `audit_logs`. |
| **Database** | 14 relational tables (`users`, `jeweller_profiles`, `customer_profiles`, `transactions`, `jewellery_items`, `measurement_records`, `rate_records`, `deductions`, `valuation_results`, `anomaly_flags`, `acknowledgements`, `digital_passports`, `audit_logs`, `consent_records`) supporting PostgreSQL 16 (Docker) and SQLite (local development). |

---

## Quick Start

### Option A: Docker Compose (PostgreSQL 16 + FastAPI + Next.js)

```bash
cp .env.example .env
docker compose up --build
```

- Frontend PWA: `http://localhost:3000`
- Backend API & OpenAPI Docs: `http://localhost:8000/docs`

### Option B: Local Development (Windows / macOS / Linux)

#### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate  |  macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

---

## Demo Accounts (`DEMO_MODE=true`)

All seeded demo records and simulated measurements are explicitly tagged `[DEMO]` / `simulated_demo`.

| Role | Email | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Jeweller 1 (Coimbatore)** | `meena@kaverigold.demo` | `GoldProof2026!` | Kaveri Heritage Jewellers — owns `GP-DEMO-2026-001`..`004` |
| **Jeweller 2 (Madurai)** | `arun@maduraigold.demo` | `GoldProof2026!` | Madurai Bullion & Crafts — tenant isolation test (`GP-DEMO-2026-005`) |
| **Customer (Tamil / English)** | `lakshmi@customer.demo` | `GoldProof2026!` | Lakshmi Narayanan — view breakdowns & ask Tamil voice questions |
| **Administrator** | `admin@goldproof.demo` | `GoldProof2026!` | Platform aggregates & append-only hash-chain verifier |

---

## End-to-End Hackathon Demonstration Script (9 Steps)

1. **Jeweller creates / inspects a valuation**: Sign in as `meena@kaverigold.demo`, open **New Exchange** (`/jeweller/new`), enter `20 g` gross, `0 g` non-gold, `91.6%` purity, `₹7,600/g` 24K rate, and `₹3,000` documented deduction.
2. **Valuation engine calculates transparently**: Pure gold equivalent = `18.3200 g`, Gross reference value = `₹1,39,232.00`, Net exchange value = `₹1,36,232.00`.
3. **Deduction Intelligence detects issues**: Inspect `GP-DEMO-2026-002` (an illustrative `₹6,500` deduction with no explanation and manual entry) to see neutral rule-based `Review Required` flags.
4. **Customer opens pending transaction**: Sign in as `lakshmi@customer.demo` and open `GP-DEMO-2026-003`.
5. **Customer asks in Tamil**: Tap the microphone (or click the Tamil chip) to ask `"எனது தங்கத்தின் மதிப்பு எவ்வளவு?"`.
6. **AI explains using recorded evidence**: The assistant walks step by step through weights, purity, 24K rate, deductions, and flags any missing documentation without inventing data.
7. **Both parties acknowledge**: Customer clicks **Confirm & Acknowledge Record**; Jeweller confirms on `/jeweller/transactions/[id]`.
8. **Digital Gold Passport issued**: Jeweller clicks **Issue Signed Digital Gold Passport** to generate the SHA-256 hash, Ed25519 signature, and QR code.
9. **Public QR verification**: Open `/verify/GP-DEMO-2026-001` (no login required) to verify the Ed25519 signature, SHA-256 record integrity, and scope notice.

---

## Security & Honesty Guarantees

- **Strict Tenant Isolation**: Jewellers can read/modify only their own shop's transactions (`403 Forbidden` across tenants). Customers see only their own records.
- **Immutability & Amendments**: Signed transactions return `409 Conflict` on `PUT`; corrections require creating a linked `v+1` amendment (`POST /api/transactions/{id}/amend`) while preserving the original signed passport intact.
- **Signature Scope Clarity**: Every verification page clearly states that an Ed25519 signature proves the signed digital record has not changed since signing, and does not independently verify the physical truthfulness of manual weights/purity readings.
- **ML Honesty**: `IsolationForest` does not train on fabricated demo records; it activates automatically only once a shop accumulates at least 15 real non-demo transactions.
- **External Provider Transparency**: When `LLM_API_KEY`, `OCR_PROVIDER`, or cloud speech APIs are unconfigured, GoldProof reports its local/simulated adapters explicitly (`is_external_llm: false`, `is_simulated: true`, `requires_human_confirmation: true`).

---

## Running Tests

```bash
cd backend
pytest -v
```
