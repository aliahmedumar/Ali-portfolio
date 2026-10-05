# Ali Ahmed — Portfolio

Static site served at https://ali.cloudordinate.com

- `index.html` — the site
- `assets/ali.png` — profile photo
- `assets/projects/<slug>.jpg` — project previews (apogeu, moodzy, tlogistikz, tradeandtrade, expships, expresscon, purplestore, gccpl). Images from cloudordinate.com; missing ones fall back to a live screenshot.

## Deploy
- Ports 80/443 are owned by the `n8n-setup-caddy-1` container. Caddy terminates HTTPS and proxies `ali.cloudordinate.com` to host nginx on `:8088`. The block is in `deploy/Caddyfile.snippet`, appended to `/home/opc/n8n-setup/caddy/Caddyfile`.
- One-time VPS setup: `deploy/setup-vps.sh`.
- GitHub secret `VPS_SSH_KEY` = private key. A push to `main` runs `.github/workflows/deploy.yml`.
