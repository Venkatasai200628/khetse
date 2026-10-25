# Deploying the KhetSe backend on a VM

The production stack is **Postgres + Redis + FastAPI behind Caddy** (automatic HTTPS),
defined in [`docker-compose.prod.yml`](../docker-compose.prod.yml). Only Caddy's ports
80/443 are published; the database and API are internal to the compose network.

## Option A0 — Azure for Students (what this repo's VM uses)

Azure for Students gives $100/12 months, no card. Real-world notes from our deployment:

- The subscription enforces a **region allow-list policy** ("Allowed resource deployment
  regions"). Ours permits only: `malaysiawest, eastasia, koreacentral, indiasouthcentral,
  uaenorth`. Read yours with:
  `az policy assignment list --query "[].parameters.listOfAllowedLocations.value" -o json`
- azure-cli 2.90 `az vm create` crashes with "The content for this response was already
  consumed" (known bug). Workaround: deploy via **ARM template**
  ([`deploy/azure/vm.json`](azure/vm.json)) — `az deployment group create` uses a code path
  that works:
  ```bash
  az group create -n khetse-rg -l indiasouthcentral
  az deployment group create -g khetse-rg --template-file deploy/azure/vm.json \
    --parameters "sshPublicKey=$(cat ~/.ssh/id_ed25519.pub)" "dnsLabel=khetse-sih"
  ```
  The template creates a **Standard** static public IP with a DNS label, so the VM gets a
  stable `<label>.<region>.cloudapp.azure.com` name — that suffix is on the Public Suffix
  List, so Caddy obtains a real Let's Encrypt certificate with **no domain purchase**.
- Add 2 GB swap before building on B1ms (1 vCPU / 2 GB): `fallocate -l 2G /swapfile && mkswap && swapon`.
- Then run the bootstrap: `sudo bash deploy/vm/bootstrap.sh <fqdn>`.
- Cost burn: B1ms ~$15/mo + Standard IP ~$3/mo + disk ~$2/mo ≈ **$20/month → ~5 months of credit**.
  Deallocate when idle: `az vm deallocate -g khetse-rg -n khetse-vm` (stops billing; public IP
  keeps charging ~$3/mo while allocated).

## Option A — Oracle Cloud "Always Free" VM (genuinely $0 forever)

1. Sign up at [oracle.com/cloud/free](https://www.oracle.com/cloud/free/) (needs a card for
   identity verification; the always-free tier is not charged).
2. Create an instance: **Ampere A1** (ARM), shape `VM.Standard.A1.Flex` with 2 OCPU / 12 GB RAM
   (always-free allowance), image **Ubuntu 22.04 or 24.04**, add your SSH public key.
3. In the VCN security list, open inbound TCP **22, 80, 443**.
4. DNS: create a free subdomain at [duckdns.org](https://www.duckdns.org) (e.g. `khetse.duckdns.org`)
   and point its A record at the VM's public IP. (Any domain works the same way.)
5. On the VM (ARM note: our Dockerfile is `python:3.13-slim`, which builds fine on ARM):

   ```bash
   sudo bash deploy/vm/bootstrap.sh khetse.duckdns.org
   ```

   The script installs Docker, opens the firewall, generates fresh `JWT_SECRET`/`POSTGRES_PASSWORD`,
   starts the stack, runs migrations, and seeds the labelled demo data.

Option B — any Ubuntu/Debian VM (college lab, AWS, Azure, DigitalOcean): identical, same script.

## After the VM is up

- Health: `curl https://YOUR_DOMAIN/health` · Swagger UI: `https://YOUR_DOMAIN/docs`
- Demo logins: `farmer1`, `buyer1`, `driver1`, `fpo1`, `admin1` (via `POST /api/v1/auth/demo-login`)
- Rebuild and redeploy the frontend against it (from your dev machine, or ask the agent):

  ```bash
  cd app && flutter build web --release --dart-define=API_BASE_URL=https://YOUR_DOMAIN/api/v1
  # then redeploy build/web to Vercel
  ```

## Operations on the VM

| Task | Command |
|---|---|
| Update to latest code | `cd /opt/khetse && git pull && docker compose -f docker-compose.prod.yml up -d --build` |
| Logs | `docker compose -f docker-compose.prod.yml logs -f backend` |
| Restart | `docker compose -f docker-compose.prod.yml restart backend` |
| Backup database | `docker compose -f docker-compose.prod.yml exec db pg_dump -U khetse khetse > backup.sql` |
| Reset demo state | `docker compose -f docker-compose.prod.yml exec backend python -m app.db.seed` (idempotent) |

## Hardening for anything beyond a demo

- `CORS_ORIGINS`: set to your frontend origin instead of `*`.
- `DEMO_MODE=false` disables demo logins and dev OTP echo; keep `ENV=production` (the app then
  refuses placeholder JWT secrets).
- Point `DATA_GOV_IN_API_KEY` / `BHASHINI_API_KEY` at real keys — adapters activate automatically.
- Schedule `pg_dump` backups (cron) and keep at least one off-VM copy.
