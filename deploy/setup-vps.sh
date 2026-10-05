#!/usr/bin/env bash
# One-time setup on the Oracle VPS (Oracle Linux). Run as opc:
#   scp -i <key> deploy/setup-vps.sh deploy/ali.cloudordinate.com.conf opc@139.185.40.101:~
#   ssh -i <key> opc@139.185.40.101 "bash setup-vps.sh"
set -euo pipefail

DOMAIN=ali.cloudordinate.com
SITE_DIR=/var/www/$DOMAIN

sudo dnf install -y nginx rsync

sudo mkdir -p "$SITE_DIR"
sudo cp ~/ali.cloudordinate.com.conf /etc/nginx/conf.d/$DOMAIN.conf
sudo chown -R nginx:nginx "$SITE_DIR"

if command -v getenforce >/dev/null && [ "$(getenforce)" != "Disabled" ]; then
  sudo semanage fcontext -a -t httpd_sys_content_t "/var/www(/.*)?" 2>/dev/null || true
  sudo restorecon -R /var/www
  sudo semanage port -a -t http_port_t -p tcp 8088 2>/dev/null || sudo semanage port -m -t http_port_t -p tcp 8088
fi

# Move nginx's stock default server off port 80 (owned by Docker).
sudo sed -i -E 's/listen\s+80;/listen 127.0.0.1:8009;/; s/listen\s+\[::\]:80;/listen [::1]:8009;/' /etc/nginx/nginx.conf

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# HTTPS is terminated by the existing Docker reverse proxy on 80/443, which forwards to this host on port 8088.
curl -sI http://127.0.0.1:8088 -H "Host: $DOMAIN" | head -1
