# DocMind - AI Enterprise Document Intelligence Platform

DocMind is a production-grade AI-powered Document Intelligence platform. It allows users to upload various document categories (PDFs, images, invoices, receipts, contracts, medical reports, IDs, etc.), clean them via computer-vision pipelines, run structured metadata models, and execute grounded queries using hybrid search (pgvector + BM25) and local Cross-Encoder reranking.

---

## Key Features

* **JWT Authentication**: Secure user isolation for uploaded documents, chat history, and semantic indexes.
* **Smart Processing Pipeline**:
  * Scans PDFs to detect selectable text; extracts layout text directly to skip OCR when unnecessary.
  * Image preprocessing (deskewing, noise-filtering, and contrast adjustment) via OpenCV.
  * Native OCR using PaddleOCR, with a high-fidelity multimodal fallback using Gemini API.
* **Multi-Schema Metadata Extraction**: Automated category classification (Invoice, Contract, ID, Medical Report, Policy) and structured JSON property extraction via Gemini schema-conforming outputs.
* **Intelligent Semantic Chunking**: Split text strictly based on paragraph, heading, and semantic markers instead of character slicing.
* **State-of-the-Art Hybrid Retrieval**:
  * Cosine Vector Search (`pgvector`) using local `BAAI/bge-base-en-v1.5` embeddings.
  * Keyword Search (`rank_bm25` Okapi index) over filtered documents.
  * Reciprocal Rank Fusion (RRF) to merge candidate lists.
  * Reranking using local `BAAI/bge-reranker-base` Cross-Encoder.
* **Streaming RAG with Citations**: Stream tokens via Server-Sent Events (SSE) while enforcing zero-hallucination rules and displaying document and page references.

---

## Directory Structure

```
├── backend/
│   ├── app/
│   │   ├── api/            # Authentication, document files, and chat streaming routers
│   │   ├── core/           # Config settings and security JWT helpers
│   │   ├── db/             # Engine creation and pgvector initialization
│   │   ├── models/         # SQLAlchemy schemas (Users, Documents, Chunks, Messages)
│   │   ├── schemas/        # Pydantic validation schemas
│   │   ├── repositories/   # SOLID DB interfaces (UserRepo, DocumentRepo, ChatRepo)
│   │   ├── services/       # Core business logic (Embeddings, OCR, RAG, Metadata)
│   │   └── utils/          # Intelligent text splitters
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # Chat interface, document panels, metadata modal, auth
│   │   ├── services/       # Axios API client and Server-Sent Event stream reader
│   │   ├── types/          # TypeScript interfaces
│   │   ├── App.tsx         # Dashboard master console
│   │   └── index.css       # Tailwind directives & Inter Typography
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml
```

---

## Environment Variables

Create a `.env` file at the project root:

```env
# Gemini API Key (Required for reasoning & extraction)
GEMINI_API_KEY=your_gemini_api_key_here

# Secret key for JWT hashing
JWT_SECRET_KEY=generate_a_random_jwt_secret_hex_key

# Options (Defaults are pre-configured)
DATABASE_URL=postgresql://postgres:postgres@db:5432/docmind
EMBEDDING_MODEL_NAME=BAAI/bge-base-en-v1.5
RERANKER_MODEL_NAME=BAAI/bge-reranker-base
```

---

## Quick Start (Docker Compose)

The easiest way to run the entire stack (Postgres + pgvector, FastAPI, Nginx React app) is via Docker Compose:

1. **Start Services**:
   ```bash
   docker-compose up -d --build
   ```
2. **Accessing the Apps**:
   * Frontend Dashboard: `http://localhost:3000`
   * Backend Swagger docs: `http://localhost:8000/docs`
   * PostgreSQL database: `localhost:5434` (external map)

---

## Manual Developer Setup (Local Machine)

If you prefer running services outside Docker containers:

### Prerequisites
* **Python**: 3.11+
* **Node.js**: 20+
* **System Poppler binary** (for PDF image conversions during OCR):
  * macOS: `brew install poppler`
  * Debian/Ubuntu: `apt-get install poppler-utils`

### 1. Database
Launch the Docker database alone if you don't have local Postgres with pgvector:
```bash
docker-compose up -d db
```

### 2. Backend API
1. Navigate to backend, create virtualenv, and install requirements:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Run backend dev server:
   ```bash
   export GEMINI_API_KEY="your_api_key"
   export DATABASE_URL="postgresql://postgres:postgres@localhost:5434/docmind"
   uvicorn app.main:app --reload --port 8000
   ```

### 3. Frontend App
1. Navigate to frontend and install dependencies:
   ```bash
   cd frontend
   npm install --legacy-peer-deps
   ```
2. Launch Vite dev server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

---

## Scalability and Future Improvements

1. **Asynchronous Task Queue (Celery/Redis)**:
   For processing thousands of documents concurrently, replace FastAPI's background tasks with a Celery worker pool and a Redis broker to prevent thread exhaustion.
2. **Blob Storage Abstraction (MinIO/S3)**:
   Introduce a storage class interface (`backend/app/services/storage/`) that handles saves, deletes, and presigned URLs, making it easy to swap local directory storage for AWS S3 or MinIO.
3. **Advanced Table Extraction**:
   Integrate Microsoft Table Transformer or PaddleStructure layout parsing to extract grid tabular structures and index them as Markdown-formatted text tables for better LLM reasoning.
