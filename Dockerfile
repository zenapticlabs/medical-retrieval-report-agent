FROM python:3.9-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch and CUDA first
RUN pip install --no-cache-dir torch>=2.1.0

# Copy requirements and install other dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create directory for model cache
RUN mkdir -p /root/.cache/huggingface

# Pre-download NLTK data and model
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')" && \
    python -c "from transformers import AutoTokenizer, AutoModel; \
    AutoTokenizer.from_pretrained('FremyCompany/BioLORD-2023', local_files_only=False, force_download=True); \
    AutoModel.from_pretrained('FremyCompany/BioLORD-2023', local_files_only=False, force_download=True)"

# Final stage
FROM python:3.9-slim

WORKDIR /app

# Copy installed packages and cache from builder
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /root/.cache /root/.cache

# Copy application code
COPY . .

# Expose port for the web application
EXPOSE 5000

# Command to run the application
CMD ["python", "app.py"] 