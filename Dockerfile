FROM node:18-alpine

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy all other files
COPY . .

# Create auth directory
RUN mkdir -p auth_info_baileys

# Create health endpoint
RUN echo '{"scripts":{"health":"node -e \"require('"'"'http'"'"').createServer((_,r)=>{r.end('"'"'ok'"'"')}).listen(3000)\""}}' > package-health.json

EXPOSE 3000

CMD ["sh", "-c", "node -e \"require('http').createServer((_,r)=>{r.end('ok')}).listen(3000)\" & node index.js"]
