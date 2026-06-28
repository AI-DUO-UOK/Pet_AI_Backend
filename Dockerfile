FROM python:3.11-slim

WORKDIR /app

# Copy only requirements.txt first (better Docker layer caching)
COPY requirements.txt .

# Install packages with no cache to keep image lean
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Keep bash as default command for interactive development
CMD ["bash"]
