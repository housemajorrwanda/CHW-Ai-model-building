FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OCR and image processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Slim deps for Railway image size limit (~4GB); see requirements-railway.txt
COPY requirements-railway.txt .
RUN pip install --no-cache-dir -r requirements-railway.txt

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose port (Railway will set PORT dynamically)
EXPOSE 8000

# Run the application using start script
CMD ["./start.sh"]

