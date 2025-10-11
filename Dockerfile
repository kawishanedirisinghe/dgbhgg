FROM php:8.2-cli

# Install Python and pip with venv support
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install Python requirements if requirements.txt exists using virtual environment
COPY requirements.txt ./
RUN if [ -f requirements.txt ]; then \
    python3 -m venv /app/venv && \
    /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install -r requirements.txt; \
    fi

EXPOSE 10000

CMD ["sh", "-c", "php -S 0.0.0.0:${PORT:-10000} -t ."]
