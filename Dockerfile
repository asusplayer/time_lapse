FROM python:3.11-slim

# Install ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY migrate_frames.py .
COPY start.py .

# Create screenshots directory
RUN mkdir -p /screenshots

# Make scripts executable
RUN chmod +x start.py

# Run the smart startup script
CMD ["python", "-u", "start.py"]
