# Use a slim base Python image
FROM python:3.10-slim-bullseye

# Set the working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# # Install dependencies
# RUN pip install --no-cache-dir -r requirements.txt


# Install system dependencies + Python packages
RUN apt-get update && apt-get install -y libgl1 && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code
COPY . .

COPY .env .env

# Set env variable if using service account (optional, only if needed)
# ENV GOOGLE_APPLICATION_CREDENTIALS="/app/turing-genai-ws-58339643dd3f.json"

# Expose the default Streamlit port
EXPOSE 8501

# Run the Streamlit app on Cloud Run-compatible settings
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableCORS=false"]
