FROM php:8.2-cli

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Install Python requirements if requirements.txt exists
COPY requirements.txt ./
RUN if [ -f requirements.txt ]; then \
    python3 -m pip install --user --upgrade pip && \
    python3 -m pip install --user -r requirements.txt; \
    fi

EXPOSE 10000

CMD ["sh", "-c", "php -S 0.0.0.0:${PORT:-10000} -t ."]
