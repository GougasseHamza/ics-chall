FROM python:3.12-slim

ARG PLAYER_PASSWORD=line4-maint

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
       ca-certificates curl iproute2 iputils-ping less nano netcat-openbsd nmap \
       openssh-server procps tcpdump \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pyModbusTCP==0.3.0 \
    && useradd --create-home --shell /bin/bash player \
    && printf 'player:%s\n' "$PLAYER_PASSWORD" | chpasswd \
    && ssh-keygen -A \
    && mkdir -p /run/sshd /opt/challenge \
    && chmod 0755 /run/sshd

COPY services/attacker/sshd_config /etc/ssh/sshd_config
COPY services/attacker/mbcli.py /usr/local/bin/mbcli
COPY services/attacker/README.txt /opt/challenge/README.txt

RUN chmod 0755 /usr/local/bin/mbcli \
    && chmod 0444 /opt/challenge/README.txt \
    && printf '\ncat /opt/challenge/README.txt\n' >> /home/player/.bashrc \
    && chown -R player:player /home/player

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D", "-e"]

