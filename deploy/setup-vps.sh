#!/usr/bin/env bash
# One-time setup on the Oracle VPS (Oracle Linux). Run as opc:
#   scp -i <key> deploy/setup-vps.sh deploy/ali.cloudordinate.com.conf opc@139.185.40.101:~
#   ssh -i <key> opc@139.185.40.101 "bash setup-vps.sh"
set -euo pipefail

DOMAIN=ali.cloudordinate.com
SITE_DIR=/var/www/$DOMAIN

sudo dnf install -y nginx rsync
sudo dnf install -y "oracle-epel-release-el$(rpm -E %rhel)" || true
sudo dnf install -y certbot python3-certbot-nginx

sudo mkdir -p "$SITE_DIR"
sudo cp ~/ali.cloudordinate.com.conf /etc/nginx/conf.d/$DOMAIN.conf
sudo chown -R nginx:nginx "$SITE_DIR"

if command -v getenforce >/dev/null && [ "$(getenforce)" != "Disabled" ]; then
  sudo semanage fcontext -a -t httpd_sys_content_t "/var/www(/.*)?" 2>/dev/null || true
  sudo restorecon -R /var/www
fi

if systemctl is-active --quiet firewalld; then
  sudo firewall-cmd --permanent --add-service=http --add-service=https
  sudo firewall-cmd --reload
fi

sudo systemctl enable --now nginx
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m ali@cloudordinate.com --redirect
