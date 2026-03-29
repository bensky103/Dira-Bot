FROM python:3.13-slim

# Install Playwright Firefox dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 libdbus-glib-1-2 libxt6 libx11-xcb1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install firefox

COPY src/ src/
COPY run.py .

# Seed files — copied to /data volume at runtime by run.py
COPY session.json /app/session.json
COPY service_account.json /app/service_account.json

CMD ["python", "run.py"]
