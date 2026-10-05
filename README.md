# Ali Ahmed — Portfolio

Static site served at https://ali.cloudordinate.com

- `index.html` — the site
- `assets/ali.jpg` — profile photo
- `assets/projects/<slug>.jpg` — project previews (apogeu, moodzy, tlogistikz, tradeandtrade, expships, expresscon, purplestore, gccpl). Missing files fall back to a live screenshot.

## Deploy
1. DNS: `A ali.cloudordinate.com → 139.185.40.101`
2. Oracle Cloud security list: allow TCP 80/443
3. One-time VPS setup: `scp -i <key> deploy/* opc@139.185.40.101:~ && ssh -i <key> opc@139.185.40.101 'bash setup-vps.sh'`
4. GitHub repo secret `VPS_SSH_KEY` = contents of the private key
5. Push to `main` (or run the workflow manually) → `.github/workflows/deploy.yml`
