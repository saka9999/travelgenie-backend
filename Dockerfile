# ✅ Use official Playwright image WITH all browsers preinstalled
FROM mcr.microsoft.com/playwright/python:v1.41.1-focal

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose API port
EXPOSE 8000

# Start your FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
