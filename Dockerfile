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

# Copy application
COPY app.py .

# Create screenshots directory
RUN mkdir -p /screenshots

# Make the script executable
RUN chmod +x app.py

# Run the application
CMD ["python", "-u", "app.py"]
