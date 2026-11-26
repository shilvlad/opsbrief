#!/usr/bin/env bash
set -Eeuo pipefail
# Fresh Ubuntu 24.04 host only. Run as root with:
# bash bootstrap-and-deploy.sh DOMAIN LETSENCRYPT_EMAIL COMMIT_SHA /tmp/opsbrief.env
DOMAIN="${1:?domain required}"
EMAIL="${2:?email required}"
REVISION="${3:?git commit required}"
ENV_SOURCE="${4:?environment file required}"

[[ "$EUID" -eq 0 ]] || { echo "Run as root" >&2; exit 1; }
[[ "$DOMAIN" =~ ^[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?$ ]] || exit 2
[[ "$EMAIL" =~ ^[^[:space:]@]+@[^[:space:]@]+$ ]] || exit 2
[[ "$REVISION" =~ ^[[:xdigit:]]{40}$ ]] || exit 2
[[ -f "$ENV_SOURCE" ]] || exit 2

. /etc/os-release
[[ "$ID" = ubuntu && "$VERSION_ID" = 24.04 ]] || {
  echo "Only fresh Ubuntu 24.04 is supported" >&2; exit 3;
}
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git nginx certbot python3-certbot-nginx docker.io docker-compose-v2
systemctl enable --now docker nginx

install -d -m 0700 /etc/opsbrief
install -m 0600 "$ENV_SOURCE" /etc/opsbrief/opsbrief.env
rm -f "$ENV_SOURCE"
install -d -m 0755 /opt/opsbrief
if [[ ! -d /opt/opsbrief/.git ]]; then
  git clone https://github.com/shilvlad/opsbrief.git /opt/opsbrief
fi
git -C /opt/opsbrief fetch --depth 1 origin "$REVISION"
git -C /opt/opsbrief checkout --detach --force FETCH_HEAD
ln -sfn /etc/opsbrief/opsbrief.env /opt/opsbrief/.env

cd /opt/opsbrief
docker compose config --quiet
docker compose up -d --build --remove-orphans
for attempt in {1..30}; do
  if curl --fail --silent http://127.0.0.1:8080/health | grep -q '"ok"'; then
    break
  fi
  if (( attempt == 30 )); then docker compose logs --tail=80; exit 4; fi
  sleep 2
done

# HTTP-only vhost to satisfy first-run ACME validation.
install -d -m 0755 /var/www/letsencrypt
cat > /etc/nginx/sites-available/opsbrief <<NGINX
server {
    listen 80;
    server_name ${DOMAIN};
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/letsencrypt;
    }
    location / { return 404; }
}
NGINX
ln -sfn /etc/nginx/sites-available/opsbrief /etc/nginx/sites-enabled/opsbrief
nginx -t
systemctl reload nginx

# DNS must already point at this host, and port 80 must be reachable.
if [[ ! -f "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" ]]; then
  certbot certonly --webroot -w /var/www/letsencrypt \
    -d "$DOMAIN" --email "$EMAIL" --agree-tos --non-interactive
fi

cat > /etc/nginx/sites-available/opsbrief <<NGINX
server {
    listen 80;
    server_name ${DOMAIN};
    location ^~ /.well-known/acme-challenge/ { root /var/www/letsencrypt; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl;
    server_name ${DOMAIN};
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    location = /health {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
    }
    location = /api/v1/brief {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
    }
    location ^~ /alice/webhook/ {
        access_log off;
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
    }
    location / { return 404; }
}
NGINX
nginx -t
systemctl reload nginx
curl --fail --silent --show-error --max-time 15 "https://${DOMAIN}/health" | grep -q '"ok"'
echo "OpsBrief installed at commit ${REVISION} and HTTPS health check passed."
