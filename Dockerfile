# Use an official Python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Copy dependencies list and install
COPY requirements.txt .

# Install system dependencies (optional: for packages like numpy/pandas, etc.)
RUN apt-get update && apt-get install -y \
    build-essential \
    && pip install --upgrade pip \
    && pip install -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# (Optional) Expose the port you’ll use
EXPOSE 7860

# Run the application
CMD ["python", "run_app.py"]
