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
    && rm -rf /var/lib/apt/lists/*

# Install Telegram bot dependencies
RUN pip3 install python-telegram-bot pyyaml

# Configure SSH
RUN mkdir /var/run/sshd
RUN echo 'root:password123' | chpasswd
RUN sed -i 's/#PermitRootLogin prohibit-ssh/PermitRootLogin yes/' /etc/ssh/sshd_config
RUN sed -i 's/#Port 22/Port 443/' /etc/ssh/sshd_config
RUN echo "ClientAliveInterval 60" >> /etc/ssh/sshd_config
RUN echo "ClientAliveCountMax 3" >> /etc/ssh/sshd_config

# Create user management script
RUN echo '#!/bin/bash\n\
useradd -m -s /bin/bash $1\n\
echo "$1:$2" | chpasswd\n\
echo "User $1 created successfully"' > /usr/local/bin/create_user.sh
RUN chmod +x /usr/local/bin/create_user.sh

# Create app directory
RUN mkdir /app

# Copy bot.py to container
COPY bot.py /app/bot.py

# Create startup script
RUN echo '#!/bin/bash\n\
# Start SSH service\n\
service ssh start\n\
# Start Telegram bot\n\
python3 /app/bot.py &\n\
# Keep container running\n\
tail -f /dev/null' > /start.sh
RUN chmod +x /start.sh

EXPOSE 443

CMD ["/bin/bash", "/start.sh"]
