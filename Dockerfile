# Use Node.js LTS version
FROM node:18-alpine

# Install PHP (if needed for other purposes) and other dependencies
RUN apk add --no-cache \
    php \
    php-common \
    php-curl \
    php-json \
    php-mbstring \
    php-phar \
    && rm -rf /var/cache/apk/*

# Create app directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Create directory for auth files
RUN mkdir -p auth_info_baileys

# Expose port (Render requires a web server, but this is a bot)
# We'll use a simple HTTP server to keep the service alive
EXPOSE 3000

# Create a simple HTTP server to satisfy Render's web service requirement
RUN echo "<?php echo 'WhatsApp Bot is running...'; ?>" > index.php

# Start command - runs both the Node.js bot and a simple PHP web server
CMD ["sh", "-c", "php -S 0.0.0.0:3000 index.php & node index.js"]
