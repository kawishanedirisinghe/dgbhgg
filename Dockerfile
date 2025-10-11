FROM php:8.2-cli

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links for python and pip
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

WORKDIR /app
COPY . .

# Install Python requirements if requirements.txt exists
COPY requirements.txt ./
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

EXPOSE 10000

# For Render, you might want to use their default $PORT environment variable
CMD ["php", "-S", "0.0.0.0:10000", "-t", "."]
