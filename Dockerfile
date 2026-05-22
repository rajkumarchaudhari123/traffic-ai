# Use official lightweight Python 3.12 slim image
FROM python:3.12-slim

# Set environment variables for optimized execution
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_DEFAULT_TIMEOUT=1000

# Install system dependencies required for OpenCV, PyTorch, and Tesseract OCR
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    gcc \
    python3-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory as root
WORKDIR /app

# Install CPU-only PyTorch and torchvision globally (as root) to prevent permission errors
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.3.0 torchvision==0.18.0

# Copy requirements.txt and install dependencies globally
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files
COPY . .

# Create the violations and static asset directories
RUN mkdir -p violations static/css static/js

# Set up a secure non-root user with UID 1000 (Hugging Face requirement)
# and assign full ownership of /app to the user
RUN useradd -m -u 1000 user && \
    chown -R user:user /app

# Switch execution context to the secure non-root user for container runtime
USER user

# Set PYTHONPATH and PATH
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/app

# Expose default port
EXPOSE 7860
ENV PORT=7860

# Launch application using run.py on exposed host and dynamic port
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "7860"]
