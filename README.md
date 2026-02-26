# TaxMantri 🧾⚖️

> **GenAI-powered ITR-1 tax co-pilot for Indian salaried individuals.**  
> Compare Old vs New regime, discover missed deductions, and get guided ITR-1 filing — all in your browser.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Setup — macOS](#setup--macos)
- [Setup — Windows](#setup--windows)
- [Environment Variables](#environment-variables)
- [Running the App](#running-the-app)
- [API Reference](#api-reference)
- [Team](#team)

---

## Overview

TaxMantri is a full-stack web application that helps Indian salaried employees:

1. **Upload Form 16** (PDF/JPEG/PNG) and auto-extract salary & deduction fields via OCR
2. **Compare Old vs New tax regime** with a detailed breakdown grounded in the Income Tax Act 1961
3. **Get AI-powered insights** — regime recommendation, missed deductions, ITR-1 field mapping
4. **Chat with an AI assistant** for personalised tax Q&A backed by a RAG pipeline

Tax calculations follow AY 2025-26 (FY 2024-25) rules.

---

## Features

| Feature | Description |
|---|---|
| 📄 Form 16 OCR | Auto-extract salary, HRA, 80C, and other fields from uploaded Form 16 |
| ⚖️ Regime Comparison | Side-by-side Old vs New regime tax calculation with full breakdowns |
| 🤖 AI Insights | Mistral-powered regime recommendation with Income Tax Act citations |
| 💬 Tax Chatbot | RAG-powered chatbot — answers personalised queries using your own tax data |
| 🗂️ ITR-1 Mapping | Maps your financial data to exact Schedule/Field positions on ITR-1 |
| 📥 PDF Export | Download a full tax summary report as a PDF |
| 🔒 Privacy First | All session data stored temporarily — no login required |

---

## Tech Stack

### Frontend
- **React 18** + Vite
- **Vanilla CSS** — custom styling with glassmorphism & dark theme
- **Framer Motion** — animations
- **React Router v6** — routing
- **Lucide React** — icons

### Backend
- **FastAPI** — async Python web framework
- **LangGraph** — agent pipeline orchestration (InputAgent → MatcherAgent → EvaluatorAgent)
- **Mistral AI** — LLM for insights & chatbot
- **FAISS + BM25** — hybrid RAG retrieval
- **Sentence Transformers** (`BAAI/bge-m3`) — embeddings
- **SQLAlchemy + asyncpg** — async PostgreSQL ORM
- **Alembic** — database migrations
- **Redis** — FAQ caching & session store
- **Tesseract OCR + pdf2image** — Form 16 extraction
- **ReportLab** — PDF generation

---

## Project Structure

```
TaxMantri/
├── backend/                   # FastAPI application
│   ├── agents/
│   │   ├── input_agent/       # Validates & normalises user profile + OCR
│   │   ├── matcher_agent/     # RAG retrieval + Mistral chatbot generation
│   │   └── evaluator_agent/   # Tax calculation, ITR-1 mapping, PDF export
│   ├── graph/                 # LangGraph pipeline definition
│   ├── models/                # SQLAlchemy ORM models
│   ├── alembic/               # Database migrations
│   ├── main.py                # App entrypoint & lifespan
│   ├── store.py               # Data access layer
│   ├── cache.py               # Redis helpers
│   ├── config.py              # Settings (reads .env)
│   └── requirements.txt
├── frontend/                  # React + Vite app
│   ├── src/
│   │   ├── pages/             # HeroPage, InputPage, ResultsPage, AboutPage, HowItWorksPage
│   │   ├── components/        # Navbar, ChatWidget, RegimeCard, AIInsightsCard, etc.
│   │   ├── api/               # Axios endpoint helpers
│   │   └── images/            # Static assets
│   ├── index.html
│   └── package.json
├── knowledge_base/
│   ├── raw/                   # Income Tax Act PDF source documents
│   └── indexes/               # FAISS + BM25 index (auto-built on first run)
└── docker-compose.yml         # PostgreSQL + Redis services
```

---

## Prerequisites

Make sure the following are installed on your machine before proceeding:

| Tool | Version | Download |
|---|---|---|
| Python | 3.11 or 3.12 | [python.org](https://python.org) |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) |
| PostgreSQL | 14+ | [postgresql.org](https://www.postgresql.org) |
| Redis | 7+ | [redis.io](https://redis.io) |
| Tesseract OCR | 5+ | [github.com/tesseract-ocr](https://github.com/tesseract-ocr/tesseract) |
| Git | Latest | [git-scm.com](https://git-scm.com) |

> **Tip:** The easiest way to run PostgreSQL and Redis is via [Docker Desktop](https://www.docker.com/products/docker-desktop/).

---

## Setup — macOS

### 1. Clone the repository
```bash
git clone https://github.com/your-org/TaxMantri.git
cd TaxMantri
```

### 2. Start PostgreSQL & Redis (Docker)
```bash
docker-compose up -d
```
> Or install natively via Homebrew:
> ```bash
> brew install postgresql@14 redis tesseract
> brew services start postgresql@14
> brew services start redis
> ```

### 3. Set up the backend
```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (remove python-magic-bin — it's Windows-only)
grep -v "python-magic-bin" requirements.txt | pip install -r /dev/stdin

# Configure environment
cp .env.example .env
# Edit .env and fill in MISTRAL_API_KEY and database credentials
```

### 4. Set up the frontend
```bash
cd ../frontend
npm install
```

### 5. (Optional) Add Income Tax Act documents for RAG
Place PDF files of the Income Tax Act into:
```
knowledge_base/raw/
```
The FAISS index is **auto-built on first backend startup**. If no documents are present, the chatbot will return a 503 until they are added.

---

## Setup — Windows

### 1. Clone the repository
```cmd
git clone https://github.com/your-org/TaxMantri.git
cd TaxMantri
```

### 2. Start PostgreSQL & Redis (Docker)
```cmd
docker-compose up -d
```
> Or install [PostgreSQL for Windows](https://www.postgresql.org/download/windows/) and [Redis for Windows](https://github.com/microsoftarchive/redis/releases) manually.

### 3. Install Tesseract OCR
Download and install from:  
[https://github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)

Make sure the install path (e.g. `C:\Program Files\Tesseract-OCR`) is added to your **system PATH**.

### 4. Set up the backend
```cmd
cd backend

:: Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt

:: Configure environment
copy .env.example .env
:: Open .env in Notepad and fill in MISTRAL_API_KEY and database credentials
notepad .env
```

### 5. Set up the frontend
```cmd
cd ..\frontend
npm install
```

### 6. (Optional) Add Income Tax Act documents for RAG
Place PDF files of the Income Tax Act into:
```
knowledge_base\raw\
```

---

## Environment Variables

Create a `.env` file inside `backend/` (copy from `.env.example`):

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg driver) | `postgresql+asyncpg://taxmantri:taxmantri@localhost:5432/taxmantri` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `MISTRAL_API_KEY` | Mistral AI API key — get from [console.mistral.ai](https://console.mistral.ai) | `sk-...` |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173` |
| `SECRET_KEY` | JWT signing secret (32+ chars) | `change-me-in-production` |
| `DEBUG` | Include error details in responses (dev only) | `true` |

---

## Running the App

### Backend

**macOS / Linux:**
```bash
cd TaxMantri
source backend/venv/bin/activate
PYTHONPATH=. uvicorn backend.main:app --reload --port 8000
```

**Windows:**
```cmd
cd TaxMantri
backend\venv\Scripts\activate
set PYTHONPATH=.
uvicorn backend.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/api/docs`

> **Note:** On first startup, if the FAISS knowledge base index doesn't exist, it will be built automatically. This takes a few minutes.

### Frontend

```bash
# macOS / Windows (same command)
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/upload` | Upload Form 16 and extract fields via OCR |
| `POST` | `/api/profile` | Create a profile from manual wizard entry |
| `PUT` | `/api/profile/confirm` | Confirm OCR-extracted profile with edits |
| `POST` | `/api/calculate` | Run full LangGraph tax pipeline |
| `GET` | `/api/itr1-mapping/{profile_id}` | Get ITR-1 field mapping for a profile |
| `GET` | `/api/export/{profile_id}` | Download PDF tax report |
| `POST` | `/api/query` | RAG chatbot query (personalised if profile_id provided) |
| `GET` | `/api/chat/history` | Fetch session chat history |
| `POST` | `/api/session/event` | Track UI interaction events |
| `GET` | `/api/session/summary` | Get session analytics summary |
| `GET` | `/api/docs` | Swagger UI (interactive API docs) |

---

## Team

| Name | Role |
|---|---|
| **AMK** | Co-Founder & Developer |
| **Chiru** | Co-Founder & Developer |
| **Srikanth** | Co-Founder & Developer |
| **Rishi** | Co-Founder & Developer |

---

> **Disclaimer:** TaxMantri is built for AY 2025-26 (FY 2024-25) rules. Tax calculations are for reference only.
