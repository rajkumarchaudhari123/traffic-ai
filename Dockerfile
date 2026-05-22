# Use official lightweight Python image
FROM python:3.10-slim

# Set environment variables to optimize Python execution in container
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Create a non-root user (Hugging Face requirement for security)
RUN useradd -m -u 1000 user

# Set the working directory inside the container
WORKDIR /home/user/app

# Install system dependencies required for OpenCV and EasyOCR
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libgomp1 \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first to leverage Docker cache
COPY --chown=user:user requirements.txt .

# Install python dependencies as the non-root user
USER user
RUN pip install --no-cache-dir --user -r requirements.txt

# Pre-cache EasyOCR English language models during build to ensure instant application startup
RUN python -c "import easyocr; easyocr.Reader(['en'])"

# Copy the rest of the project files
COPY --chown=user:user . .

# Create persistent output and caching directories and ensure proper permissions
RUN mkdir -p violations static/css static/js && chmod -R 777 violations static

# Expose the default port for Hugging Face Spaces
EXPOSE 7860

# Start the application using run.py on the exposed port
CMD ["python", "run.py", "--host", "0.0.0.0", "--port", "7860"]
