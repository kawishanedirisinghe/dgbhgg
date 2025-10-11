FROM php:8.2-cli

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links only if they don't exist
RUN ln -sf /usr/bin/python3 /usr/bin/python
RUN which pip || ln -s /usr/bin/pip3 /usr/bin/pip

WORKDIR /app
COPY . .

# Install Python requirements if requirements.txt exists
COPY requirements.txt ./
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

EXPOSE 10000

# For Render, use their PORT environment variable with fallback
CMD ["sh", "-c", "php -S 0.0.0.0:${PORT:-10000} -t ."]
