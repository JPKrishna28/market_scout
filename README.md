# 🔍 Market Intelligence Scout

AI-powered competitive intelligence platform that discovers, verifies, and scores technical features from public sources.

---

## Prerequisites

Make sure you have these installed:

- **Python 3.10+** → [Download](https://www.python.org/downloads/)
- **Node.js 18+** → [Download](https://nodejs.org/)
- **Docker Desktop** → [Download](https://www.docker.com/products/docker-desktop/)
- **Git** → [Download](https://git-scm.com/)

---

## 🚀 Setup Guide (Step by Step)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Market_Scout
```

### 2. Create the `.env` File

Create a file called `.env` in the project root with your API keys:

```env
NVIDIA_API_KEY=your_nvidia_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

> **How to get API keys:**
> - **NVIDIA NIM:** Sign up at [build.nvidia.com](https://build.nvidia.com/) → Get API Key
> - **Tavily:** Sign up at [tavily.com](https://tavily.com/) → Get API Key (free tier available)

### 3. Start Docker Services

```bash
docker compose up -d
```

This starts 4 services:
| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5433 | Database |
| Redis | 6379 | Cache & Rate Limiting |
| Prometheus | 9090 | Metrics Collection |
| Grafana | 3000 | Monitoring Dashboard |

Verify all are running:
```bash
docker compose ps
```

### 4. Set Up Python Virtual Environment

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 5. Start the Backend

```bash
uvicorn app.main:app --reload
```

Verify: Open **http://localhost:8000/docs** in your browser — you should see the Swagger API docs.

### 6. Set Up & Start the Frontend

Open a **new terminal window**:

```bash
cd frontend
npm install
npm run dev
```

### 7. Open the App

Open **http://localhost:5173** in your browser. You're ready to go! 🎉

---

## 📌 Quick Reference

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:5173 | — |
| **Backend API** | http://localhost:8000 | — |
| **Swagger Docs** | http://localhost:8000/docs | — |
| **Prometheus** | http://localhost:9090 | — |
| **Grafana** | http://localhost:3000 | admin / admin |

---

## 🔧 Useful Commands

```bash
# Stop all Docker services
docker compose down

# Restart a specific service
docker compose restart grafana

# View Docker logs
docker compose logs -f app

# Access PostgreSQL
docker exec -it market_postgres psql -U admin -d market_db

# Access Redis
docker exec -it market_redis redis-cli

# Rebuild app container
docker compose up -d --build app
```

---

## 📁 Project Structure

```
Market_Scout/
├── app/              # FastAPI application (main.py, config.py)
├── agents/           # LLM-powered nodes (search_planner, scraper, synthesis)
├── nodes/            # Deterministic nodes (guardrails, date_validation, scoring...)
├── graph/            # LangGraph pipeline (builder.py, state.py)
├── llm/              # NVIDIA NIM client
├── database/         # PostgreSQL models, CRUD, schemas
├── cache/            # Redis client
├── observability/    # Prometheus metrics + OpenTelemetry tracing
├── monitoring/       # Prometheus & Grafana configs
├── frontend/         # React SPA (Vite)
├── docker-compose.yaml
├── Dockerfile
├── requirements.txt
└── .env              # API keys (create this yourself)
```

---

## 🏗️ Tech Stack

**Backend:** Python, FastAPI, LangGraph, NVIDIA NIM (LLaMA 3.3 70B), Tavily, SBERT, SQLAlchemy, Redis

**Frontend:** React 19, Vite, React Router

**Infrastructure:** Docker, PostgreSQL 15, Redis 7, Prometheus, Grafana
