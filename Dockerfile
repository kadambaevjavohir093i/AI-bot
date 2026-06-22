FROM python:3.11-slim

WORKDIR /app

COPY requirements-inspection.txt .
RUN pip install --no-cache-dir -r requirements-inspection.txt

COPY . .

# Persistent data directory (mounted as a Railway volume at /data)
ENV DATA_DIR=/data
RUN mkdir -p /data/uploads /data/pdfs

EXPOSE 8080

CMD ["python", "run_inspection.py"]
