FROM python:3.11-slim

WORKDIR /app

# Prevent python from writing pyc files to disk and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and data directory
COPY src/ /app/src/
COPY data/ /app/data/

# Mount volume for dataset persistence
VOLUME /app/data

# Run standard script by default
ENTRYPOINT ["python", "src/main.py"]
