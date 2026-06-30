FROM python:3.12-slim
# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
WORKDIR /app
# Install system packages (if using Postgres or others)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    unixodbc \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*
# Copy and install dependencies first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copy the rest of the source code
COPY . .
# Flask configuration (can override these in docker-compose)
ENV FLASK_APP=entrypoints.flask_app \
    FLASK_ENV=development \
    PORT=5000
# Expose port for documentation purposes
EXPOSE 5000
# Run the Flask app
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]