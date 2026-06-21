# Kairo Phantom — Docker One-Liner Experience (P0.1)
# Usage:
#   docker build -t kairo-phantom -f docker/Dockerfile .
#   docker run --rm kairo-phantom
#
# Or with a custom question:
#   docker run --rm kairo-phantom python3 scripts/qa_pipeline.py \
#     --doc samples/invoice/sample_invoice_01.txt \
#     --question "What is the invoice number?"

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (none required for text-based samples;
# for PDF support add: poppler-utils tesseract-ocr)
RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir numpy

# Copy the repo
COPY . /app/

# Set environment for local-first (no cloud, no network)
ENV KAIRO_GATEWAY_TEST_MODE=true \
    KAIRO_AIR_GAP=true \
    PYTHONPATH=/app

# Default: run the first-run flow on the bundled invoice sample
CMD ["python3", "scripts/first_run.py"]
