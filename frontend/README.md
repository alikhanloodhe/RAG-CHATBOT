# Scalable RAG Front-End (React + Vite)

This is the interactive dashboard UI for monitoring and interacting with the Scalable RAG pipeline.

## Features
- **System Indicators**: Real-time status checks showing connectivity for FastAPI, PostgreSQL, Qdrant, and Redis.
- **RAG Query Console**: Interactive query testing displaying the multi-layered latency breakdown (Cache -> Vector Store -> DB -> LLM).
- **Ingestion Simulator**: Drag-and-drop simulation that maps SQL metadata registry writes and embedding generation progress.

## Running Locally

1. Install npm dependencies:
   ```bash
   npm install
   ```

2. Start the Vite dev server:
   ```bash
   npm run dev
   ```

Open the local network link displayed in the terminal to view the dashboard interface in your web browser.
