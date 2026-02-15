# Use an official lightweight Python image.
FROM python:3.12-slim

# Set the working directory inside the container.
WORKDIR /app

# Copy the requirements file.
COPY requirements.txt .

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY . .

# Expose the port the app runs on.
EXPOSE 8000

# Run the application.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
