FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create runtime directories
RUN mkdir -p inspection/uploads inspection/pdfs

EXPOSE 8080

CMD ["python", "run_inspection.py"]
