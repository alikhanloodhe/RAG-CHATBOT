# Scalable RAG Project Monorepo

Welcome to the Scalable RAG (Retrieval-Augmented Generation) Project! This repository is organized as a monorepo consisting of a FastAPI backend and a React (Vite + TypeScript) frontend, integrated with hybrid keyword and vector search, relational metadata storage, and query caching.

---

## Project Architecture

```
Scalable-RAG-Project/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/              # API Routing & controllers
│   │   ├── core/             # Settings, password hashing, token helpers
│   │   ├── db/               # PostgreSQL Database connections
│   │   ├── models/           # SQLModel database tables
│   │   └── services/         # Qdrant, Redis, and LLM services
│   ├── tests/                # Unit test suite
│   ├── pyproject.toml        # Hatch-based dependency configuration
│   ├── requirements.txt      # Traditional pip-installable dependencies
│   └── README.md
├── frontend/                 # React (Vite + TypeScript) Dashboard
│   ├── src/
│   │   ├── App.tsx           # Chatbot webpage controller
│   │   └── index.css         # Outift font styling sheet
│   └── README.md
├── Trade-offs-analysis.md    # RAG pipeline architectural analysis
├── Tests-documentation.md    # Unit test cases documentation
├── docker-compose.yml        # Docker compose configuration for DBs
└── README.md
```

---

## Tech Stack Overview
*   **Front-End**: React 19, Vite, TypeScript, Vanilla CSS (Outfit Font theme, glassmorphic elements, and visual loaders).
*   **Back-End API**: FastAPI, Uvicorn, Python 3.10+.
*   **Authentication**: PBKDF2 password hashing with signed bearer tokens for protected document and query routes.
*   **Vector Search Engine**: Qdrant (semantic storage of dense embedding vectors).
*   **Metadata SQL Registry**: Local PostgreSQL (user upload records, status, and size metadata).
*   **Latency Cache**: Redis (caching repeated RAG queries to drop latency).
*   **Dependency Tooling**: `uv` or `pip` (Python backend) and `npm` (React frontend).

---

## Prerequisites (Running Backends Locally)

To run this project locally, you **MUST** have PostgreSQL, Redis, and Qdrant running on your local machine.

### Option A: Via Docker Compose (Recommended)
If you have Docker Desktop installed, you can start all three services in one command:
```bash
docker compose up -d
```

### Option B: Local Installation on your OS

#### macOS (Using Homebrew)
1.  **PostgreSQL**:
    ```bash
    brew install postgresql@14
    brew services start postgresql@14
    ```
2.  **Redis**:
    ```bash
    brew install redis
    brew services start redis
    ```
3.  **Qdrant**:
    ```bash
    brew install qdrant
    qdrant
    ```

#### Linux (Debian/Ubuntu)
1.  **PostgreSQL**:
    ```bash
    sudo apt install postgresql postgresql-contrib
    sudo service postgresql start
    ```
2.  **Redis**:
    ```bash
    sudo apt install redis-server
    sudo service redis-server-start
    ```

---

## Local Setup & Startup Guide

### 1. Setup the FastAPI Backend

Initialize a virtual environment and install the required dependencies (which are matched between `pyproject.toml` and `requirements.txt`):

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (Choose one of the following commands):
# Option 1: Fast install using uv (preferred)
uv pip install -e .
# Option 2: Traditional pip install
pip install -r requirements.txt

# Create environment configuration
cp .env.example .env
```

Ensure your `.env` contains the correct PostgreSQL superuser, Redis host port, and your `GROQ_API_KEY` for the LLM synthesis.

Start the FastAPI application:
```bash
uvicorn app.main:app --reload
```
The FastAPI Swagger documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

### 2. Setup the React Frontend

Open a new terminal window or tab, navigate to the frontend directory, install dependencies from the package lock file to ensure version matching, and start Vite:

```bash
cd frontend
cp .env.example .env

# Install dependencies respecting package-lock.json
npm install

# Run Vite dev server
npm run dev
```
Open the URL shown in the terminal (usually [http://localhost:5173](http://localhost:5173)) to view the premium dashboard.

---

### 3. Run Backend Tests

The unit test suite runs in isolation using mock contexts and does not make actual network requests:

```bash
cd backend
source .venv/bin/activate
python -m unittest discover -s tests
```

---

## Architectural Documentation
Detailed write-ups explaining RAG design choices and test coverage are available in the repository root:
*   [Trade-offs-analysis.md](file:///Users/alikhanlodhi/Documents/Projects/Scalable-RAG-Project/Trade-offs-analysis.md): Analysis of chunk sizes, BGE asymmetric retrieval, BM25 + Dense Hybrid search, RRF reranking, and event-loop threading models.
*   [Tests-documentation.md](file:///Users/alikhanlodhi/Documents/Projects/Scalable-RAG-Project/Tests-documentation.md): Documentation of the backend unit test cases.
