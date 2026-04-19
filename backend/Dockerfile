# View/Clip backend — production image
FROM python:3.11-slim

# System deps for bcrypt, cryptography, curl (healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend

# Install deps first for better layer cache
COPY requirements.txt ./
# NOTE: emergentintegrations is installed from an Emergent-hosted index.
# If you've applied the drop-in replacement documented in /app/DEPENDENCY_AUDIT.md
# you can remove the --extra-index-url line and the package from requirements.txt.
RUN pip install --no-cache-dir \
      --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/ \
      -r requirements.txt || pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001", "--proxy-headers"]
