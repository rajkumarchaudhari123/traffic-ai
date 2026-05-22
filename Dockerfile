# Use official lightweight Python 3.10 slim image
FROM python:3.10-slim

# Set environment variables for optimized execution
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

# Install system dependencies required for OpenCV, PyTorch, and Tesseract OCR
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    gcc \
    python3-dev \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create a secure non-root user with UID 1000 (Hugging Face standard)
RUN useradd -m -u 1000 user

# Switch execution context to the secure non-root user
USER user

# Set home environment variables and PATH
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/home/user/app

# Set the secure runtime application folder (automatically created and owned by user since we are USER user)
WORKDIR /home/user/app

# Copy requirements.txt and set ownership to user
COPY --chown=user:user requirements.txt .

# Install CPU-only PyTorch first as user (requires non-root context for sandboxed network access)
RUN pip install --no-cache-dir --user torch==2.3.0 torchvision==0.18.0 --extra-index-url https://download.pytorch.org/whl/cpu

# Install all other python dependencies as user
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the application source code files and assign ownership to the user
COPY --chown=user:user . .

# Create the persistent violations and static assets directories
RUN mkdir -p violations static/css static/js

# Expose default port
EXPOSE 7860

# Default port environment variable (can be overridden by cloud providers like Railway/Render)
ENV PORT=7860

# Launch application using run.py on exposed host and dynamic port
CMD ["python", "run.py", "--host", "0.0.0.0"]
