FROM python:3.11-slim

# Install system dependencies required for pdf2image (poppler) and building native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . .

EXPOSE 7860

# Run FastAPI app with Uvicorn, binding to the port injected by cloud hosts (defaults to 8000 locally)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
