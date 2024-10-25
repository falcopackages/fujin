FROM ubuntu:latest

# Update and install necessary packages
RUN apt update && apt install -y openssh-server sudo

# Create the user 'test' and passwordless sudo
RUN useradd -rm -d /home/test -s /bin/bash -g root -G sudo -u 2000 test && \
    echo 'test:test' | chpasswd && \
    echo 'test ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

# Set up SSH server
RUN mkdir /var/run/sshd

# Copy the public key and set correct permissions for SSH
COPY id_rsa.pub /tmp/id_rsa.pub
RUN mkdir -p /home/test/.ssh && \
     cat /tmp/id_rsa.pub >> /home/test/.ssh/authorized_keys && \
     chown -R 2000:root /home/test/.ssh && \
     chmod 700 /home/test/.ssh && \
     chmod 600 /home/test/.ssh/authorized_keys

# Ensure SSH is configured to accept key-based login
RUN sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config && \
     sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin no/' /etc/ssh/sshd_config && \
     sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config && \
     echo AllowUsers test >> /etc/ssh/sshd_config

# Start SSH service
RUN service ssh start

# Expose the SSH port
EXPOSE 22

# Run the SSH server
CMD ["/usr/sbin/sshd", "-D"]
#VOLUME [ "/sys/fs/cgroup" ]
#CMD ["/lib/systemd/systemd"]
#VOLUME [ "/sys/fs/cgroup" ]
#CMD ["/lib/systemd/systemd"]