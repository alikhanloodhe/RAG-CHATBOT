# Scalable RAG Project Monorepo

Welcome to the **Scalable RAG (Retrieval-Augmented Generation)** project! This repository contains a production-ready, highly optimized RAG application designed as a monorepo containing a high-performance **FastAPI** backend and a premium **React (Vite + TypeScript)** frontend dashboard.

### 🌐 Live Production Application
*   **Production Frontend (Vercel):** [https://rag-chatbot-mocha-sigma.vercel.app/](https://rag-chatbot-mocha-sigma.vercel.app/)
*   **Production Backend API (Hugging Face Spaces):** `https://alikhanlodhi-rag-project.hf.space`

---

## 🏗️ Project Architecture

```text
Scalable-RAG-Project/
├── backend/                   # FastAPI Web Server
│   ├── app/
│   │   ├── api/               # API Controllers (Auth, upload, query, search)
│   │   ├── core/              # Settings, security, and logging config
│   │   ├── db/                # PostgreSQL sessions and schema migrations
│   │   ├── models/            # SQLModel schema declarations (Users, Documents)
│   │   └── services/          # Embeddings, LLM, Qdrant, and Redis Caching
│   ├── tests/                 # Isolated Python Unit Test suite
│   ├── Dockerfile             # Production HF Spaces container configuration
│   ├── requirements.txt       # Pin-locked python dependencies
│   └── README.md
├── frontend/                  # React + Vite + TypeScript Dashboard
│   ├── public/                # Custom brand SVG favicons
│   ├── src/
│   │   ├── components/        # UI components (Auth forms, Chat controls)
│   │   ├── App.tsx            # Main application layout and state logic
│   │   ├── index.css          # Premium glassmorphic CSS variables and themes
│   │   └── config.ts          # API Endpoint configurations
│   └── index.html             # Favicon references and base viewport meta
├── docker-compose.yml         # Containerized local DB/Cache setup
├── Trade-offs-analysis.md     # In-depth architectural trade-offs
├── Tests-documentation.md     # Detailed backend unit test catalog
└── README.md                  # Comprehensive root documentation (this file)
```

---

## 🚀 Tech Stack Overview

1.  **Frontend Interface**: React 19, TypeScript, Vite, and Vanilla CSS. Features curated Outfit typography, glassmorphism, responsive status alerts, active document indicators, and smooth loading animations.
2.  **Backend Web Server**: FastAPI, Uvicorn, and Python 3.10+. Fully asynchronous design, leveraging background threads to prevent event-loop blocking during heavy CPU tasks (PDF parsing, text chunking, and embedding generation).
3.  **Metadata Registry**: Managed **PostgreSQL** mapping relational tables for user profiles, document statuses, file metadata, and vector offsets.
4.  **Vector Database**: **Qdrant** (cloud and local disk fallback) performing sparse keyword (BM25) and dense vector (BGE semantic) hybrid search.
5.  **Reranking Engine**: **Reciprocal Rank Fusion (RRF)** merging sparse and dense candidate ranks locally to produce high-relevance search contexts.
6.  **LLM Synthesizer**: **Groq API** running `llama-3.1-8b-instant` for rapid grounded response synthesis.
7.  **Latency Cache**: **Redis** caching repeated semantic queries by namespace, ensuring sub-10ms response times for repeat client questions.

---

## 💻 Local Setup & Startup Guide

### Prerequisites
To run this project locally, ensure you have PostgreSQL, Redis, and Qdrant running.

#### Option A: Via Docker Compose (Recommended)
If you have Docker Desktop installed, spin up all local databases with one command:
```bash
docker compose up -d
```

#### Option B: OS-Native Installations (macOS Homebrew)
```bash
# PostgreSQL
brew install postgresql@14 && brew services start postgresql@14
# Redis
brew install redis && brew services start redis
# Qdrant
brew install qdrant && qdrant
```

---

### 1. Backend Local Setup
1.  Navigate to the backend directory and create a virtual environment:
    ```bash
    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    ```
2.  Install dependencies:
    ```bash
    # Option 1: Fast install using uv (preferred)
    uv pip install -e .
    # Option 2: Traditional pip install
    pip install -r requirements.txt
    ```
3.  Copy and fill the local configuration parameters:
    ```bash
    cp .env.example .env
    ```
4.  Launch the FastAPI server:
    ```bash
    uvicorn app.main:app --reload
    ```
    *Local Swagger documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*

---

### 2. Frontend Local Setup
1.  Navigate to the frontend directory:
    ```bash
    cd ../frontend
    ```
2.  Configure environment variables:
    ```bash
    cp .env.example .env
    ```
    Ensure `VITE_API_BASE_URL` points to your local backend: `http://127.0.0.1:8000/api/v1`
3.  Install dependencies and start the Vite dev server:
    ```bash
    npm install
    npm run dev
    ```
    *Open [http://localhost:5173](http://localhost:5173) in your browser.*

---

## ☁️ Production Cloud Deployment Guide

This RAG application is fully optimized for cloud environments, relying on managed serverless databases and containerized API servers.

### 1. Data and AI Services Setup
*   **Vector DB (Qdrant Cloud):** Create a free cluster at [cloud.qdrant.io](https://cloud.qdrant.io/). Take note of your **Endpoint URL** and **API Key**.
*   **Relational DB (Neon Postgres or Supabase):** Provision a managed database. Ensure you use the async connection string format.
*   **Cache (Upstash Redis):** Create a serverless Redis database at [upstash.com](https://upstash.com/). Copy the **TCP connection string** (`rediss://...`).
*   **LLM API (Groq Console):** Generate a free developer API key at [console.groq.com](https://console.groq.com/).

### 2. Backend API Deployment (Hugging Face Spaces)
The backend runs PyTorch and local SentenceTransformers (`BGE-small-en-v1.5`), requiring at least **800MB RAM** to boot. Traditional free tiers (Render/Fly.io) enforce 512MB limits and will OOM crash. We recommend **Hugging Face Spaces (Docker SDK)**, which provides a free 16GB RAM container.

1.  Create a new Space on Hugging Face, select **Docker** as the SDK (Blank template).
2.  In the Space **Settings**, add the following **Secrets**:
    *   `DATABASE_URL`: `postgresql+asyncpg://<user>:<password>@<host>:<port>/<db>?ssl=require`
    *   `QDRANT_URL`: `https://<your-cluster-id>.aws.cloud.qdrant.io:6333`
    *   `QDRANT_API_KEY`: `<your-qdrant-api-key>`
    *   `REDIS_URL`: `rediss://default:<password>@<host>:<port>`
    *   `GROQ_API_KEY`: `<your-groq-api-key>`
    *   `APP_ENV`: `production`
    *   `SECRET_KEY`: `<any-secure-random-string-for-jwt-signing>`
    *   `CORS_ORIGINS`: `https://rag-chatbot-mocha-sigma.vercel.app` (your frontend domain)
3.  Add the Hugging Face YAML metadata header to your Space's `README.md` (tells it to use Docker on port 8000):
    ```yaml
    ---
    title: RAG-PROJECT
    sdk: docker
    app_port: 8000
    ---
    ```
4.  Place the `Dockerfile` at the root of the repository and push the code. HF will build and launch your container.

### 3. Frontend Deployment (Vercel)
1.  Connect your GitHub repository to [Vercel](https://vercel.com).
2.  Set the **Root Directory** to `frontend`.
3.  Add the environment variable:
    *   `VITE_API_BASE_URL`: `https://alikhanlodhi-rag-project.hf.space/api/v1` (your direct HF Space URL with api path).
4.  Click **Deploy**. Vercel will compile the TypeScript and serve the static files via its global CDN edge network.

---

## 🧪 Verification & Testing
*   **Unit Tests:** run backend unit tests locally in isolation:
    ```bash
    cd backend
    source .venv/bin/activate
    python -m unittest discover -s tests
    ```
*   **Detailed Documentation:** Refer to [Tests-documentation.md](file:///Users/alikhanlodhi/Documents/Projects/Scalable-RAG-Project/Tests-documentation.md) for full test metrics and execution coverage.
*   **Trade-Offs Analysis:** Refer to [Trade-offs-analysis.md](file:///Users/alikhanlodhi/Documents/Projects/Scalable-RAG-Project/Trade-offs-analysis.md) for architectural trade-offs regarding embedding dimensions, BM25 rank pollution, RRF constants, and event-loop concurrency.
