FROM ubuntu:22.04

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive

# Update and install dependencies
RUN apt-get update && apt-get install -y \
    openssh-server \
    sudo \
    python3 \
    python3-pip \
    wget \
    curl \
    net-tools \
    iptables \
    systemd \
    && rm -rf /var/lib/apt/lists/*

# Install Telegram bot dependencies
RUN pip3 install python-telegram-bot pyyaml

# Configure SSH properly
RUN mkdir -p /var/run/sshd
RUN echo 'root:password123' | chpasswd

# SSH Configuration
RUN sed -i 's/#Port 22/Port 443/' /etc/ssh/sshd_config
RUN sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
RUN sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
RUN echo "ClientAliveInterval 60" >> /etc/ssh/sshd_config
RUN echo "ClientAliveCountMax 3" >> /etc/ssh/sshd_config
RUN echo "AllowUsers root" >> /etc/ssh/sshd_config

# Fix SSH directory permissions
RUN chmod 755 /var/run/sshd

# Create user management script
RUN echo '#!/bin/bash\n\
useradd -m -s /bin/bash $1\n\
echo "$1:$2" | chpasswd\n\
echo "User $1 created successfully"\n\
# Add user to SSH allowed users\n\
echo "AllowUsers root $1" >> /etc/ssh/sshd_config' > /usr/local/bin/create_user.sh
RUN chmod +x /usr/local/bin/create_user.sh

# Create app directory
RUN mkdir -p /app

# Copy bot.py to container
COPY bot.py /app/bot.py

# Create startup script with proper service management
RUN echo '#!/bin/bash\n\
# Create necessary directories\n\
mkdir -p /var/run/sshd\n\
\n\
# Generate SSH host keys if not exists\n\
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then\n\
    ssh-keygen -A\n\
fi\n\
\n\
# Start SSH service\n\
echo "Starting SSH service on port 443..."\n\
/usr/sbin/sshd -D -p 443 &\n\
\n\
# Wait for SSH to start\n\
sleep 3\n\
\n\
# Check if SSH is running\n\
if pgrep sshd > /dev/null; then\n\
    echo "SSH service started successfully on port 443"\n\
    netstat -tlnp | grep 443 || echo "SSH might not be listening properly"\n\
else\n\
    echo "Failed to start SSH service"\n\
fi\n\
\n\
# Start Telegram bot\n\
echo "Starting Telegram bot..."\n\
cd /app && python3 bot.py &\n\
\n\
# Keep container running and show logs\n\
echo "Container is running..."\n\
tail -f /dev/null' > /start.sh

RUN chmod +x /start.sh

EXPOSE 443

CMD ["/bin/bash", "/start.sh"]
