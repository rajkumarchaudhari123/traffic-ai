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

# Create a secure non-root user with UID 1000
RUN useradd -m -u 1000 user
USER user

# Set home environment variables and PATH
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/home/user/app

WORKDIR /home/user/app

# Install CPU-only PyTorch and torchvision first as user
RUN pip install --no-cache-dir --user --index-url https://download.pytorch.org/whl/cpu torch==2.3.0 torchvision==0.18.0

# Copy requirements.txt and install python requirements
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the application source code files and assign ownership to the user
COPY --chown=user:user . .

# Create the persistent violations and static assets directories
RUN mkdir -p violations static/css static/js

# Expose Hugging Face default port
EXPOSE 7860
ENV PORT=7860

# Launch application using run.py on exposed host and port
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "7860"]
