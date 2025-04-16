FROM mcr.microsoft.com/playwright/python:v1.41.1

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run Uvicorn with FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
