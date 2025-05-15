FROM python:3.11-slim-bullseye

WORKDIR /app

# Install system dependencies with security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Create necessary directories with correct permissions
RUN mkdir -p /app/chat_data /app/chat_data/logs /app/chat_data/knowledge_base \
    && chmod -R 777 /app/chat_data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_HEADLESS=true

# Run as non-root user
RUN useradd -m appuser
USER appuser

# Expose port
EXPOSE 7860

# Run the application
CMD ["python", "run_app.py"]