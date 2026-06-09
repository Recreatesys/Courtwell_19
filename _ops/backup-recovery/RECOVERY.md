# CW19_Test — Fully Recoverable Backup Set

**Captured:** 2026-06-08T10:11:56Z (UTC)
**Source host:** `courtwell.com.hk` (Contabo VPS, Ubuntu 22.04)
**Git HEAD at capture:** `71fc3f4` on `main`

## What's in this folder

```
CW19_Test_20260608T101156Z/
├── CW19_Test_20260608T101156Z.dump            1.4 GB  pg_dump custom format (-Fc -Z9) of DB
├── CW19_Test_20260608T101156Z_config_snapshot.txt 5 KB  Human-readable point-in-time snapshot
├── filestore_CW19_Test.tar.gz                 377 MB  Compressed Odoo filestore
├── pg_globals.sql                             753 B   pg_dumpall --globals-only (roles, tablespaces)
├── SHA256SUMS                                 ~300 B  Integrity manifest for the three binaries
├── RECOVERY.md                                this file
└── configs/                                   40 KB total
    ├── etc_odoo19.conf
    ├── etc_systemd_system_odoo19.service
    ├── etc_nginx_nginx.conf
    ├── etc_nginx_sites-enabled_default
    ├── etc_postgresql_14_main_postgresql.conf
    ├── etc_postgresql_14_main_pg_hba.conf
    ├── venv_pip_freeze.txt
    └── dpkg_filtered_packages.txt
```

**Total size:** ~1.8 GB.

## ⚠️ Security note

`pg_globals.sql` contains **PostgreSQL role password hashes** (the SCRAM-SHA-256 representations, not plaintext). Treat this file as sensitive — anyone who restores it gains the ability to authenticate as those roles to a PG cluster restored from this backup. Don't post it to ticket systems, paste it into chat, or store it in unencrypted cloud sync.

## Verify integrity before restoring

```bash
cd CW19_Test_20260608T101156Z/
sha256sum -c SHA256SUMS
# All three files should report: OK
```

If any line reports `FAILED` the corresponding file is corrupt — re-fetch from the original source before proceeding.

---

# Scenario A — Same machine, fresh database

Use this when the application file system + Odoo install are intact but the database is gone, corrupted, or you want to revert to this snapshot.

```bash
# 0. Confirm the box is at the right code version
cd /opt/odoo19/odoo19/custom-addons
git fetch
git checkout 71fc3f4

# 1. Stop the Odoo service so nothing writes during restore
systemctl stop odoo19

# 2. Drop the existing DB if present
sudo -u postgres dropdb --if-exists CW19_Test

# 3. Create empty target owned by the odoo19 role
sudo -u postgres createdb -O odoo19 CW19_Test

# 4. Restore the data
sudo -u postgres pg_restore \
  -d CW19_Test \
  -j 4 \
  --no-owner --role=odoo19 \
  /path/to/CW19_Test_20260608T101156Z.dump

# 5. Restore the filestore
sudo -u odoo19 mkdir -p /opt/odoo19/.local/share/Odoo/filestore
sudo -u odoo19 rm -rf /opt/odoo19/.local/share/Odoo/filestore/CW19_Test
sudo tar -C /opt/odoo19/.local/share/Odoo/filestore \
  -xzf /path/to/filestore_CW19_Test.tar.gz
sudo chown -R odoo19:odoo19 /opt/odoo19/.local/share/Odoo/filestore/CW19_Test

# 6. Start the service
systemctl start odoo19

# 7. Confirm
sudo -u postgres psql -d CW19_Test -tAc \
  "SELECT name, latest_version FROM ir_module_module WHERE name='sourcing_reference';"
# Expected: sourcing_reference|19.0.1.2.0
```

The whole sequence usually completes in 3–5 minutes for this DB size.

---

# Scenario B — Full machine rebuild (fresh Ubuntu host)

Use this when the entire host has been lost and you're rebuilding from a clean OS install.

### B.1 — Base OS preparation

```bash
# Ubuntu 22.04 LTS, fresh install. Then:
apt update && apt upgrade -y
apt install -y postgresql-14 nginx python3.10 python3.10-venv python3.10-dev \
               build-essential libpq-dev libxml2-dev libxslt1-dev libsasl2-dev \
               libldap2-dev libssl-dev libffi-dev libjpeg-dev liblcms2-dev \
               libwebp-dev wkhtmltopdf git curl
# (Cross-check configs/dpkg_filtered_packages.txt for the exact relevant set
#  that was running on the original host.)
```

### B.2 — Create the odoo19 system user, restore Odoo install

```bash
adduser --system --group --home /opt/odoo19 --shell /bin/bash odoo19

# Clone Odoo source (you'll need the same revision / branch the prod host had — check
# /opt/odoo19/odoo19/.git on the original if available, otherwise use the version
# embedded in configs/venv_pip_freeze.txt).
sudo -u odoo19 git clone https://github.com/odoo/odoo.git -b 19.0 /opt/odoo19/odoo19

# Recreate the venv with the same pip set
sudo -u odoo19 python3.10 -m venv /opt/odoo19/odoo19-venv
sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/pip install -U pip wheel
sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/pip install -r configs/venv_pip_freeze.txt

# Restore custom-addons from the canonical git repo
sudo -u odoo19 git clone <vendor-repo-url> /opt/odoo19/odoo19/custom-addons
cd /opt/odoo19/odoo19/custom-addons
sudo -u odoo19 git checkout 71fc3f4
```

### B.3 — Restore PostgreSQL

```bash
# Service should already be running after apt install
systemctl enable --now postgresql

# Restore roles BEFORE creating the DB so ownership succeeds
sudo -u postgres psql -f /path/to/pg_globals.sql

# Replace pg_hba + postgresql.conf with the captured versions (review first!)
cp configs/etc_postgresql_14_main_pg_hba.conf      /etc/postgresql/14/main/pg_hba.conf
cp configs/etc_postgresql_14_main_postgresql.conf  /etc/postgresql/14/main/postgresql.conf
chown postgres:postgres /etc/postgresql/14/main/pg_*.conf
systemctl restart postgresql

# Create empty DB owned by odoo19, then restore
sudo -u postgres createdb -O odoo19 CW19_Test
sudo -u postgres pg_restore \
  -d CW19_Test \
  -j 4 \
  /path/to/CW19_Test_20260608T101156Z.dump
```

### B.4 — Restore Odoo configs and filestore

```bash
# Configs
cp configs/etc_odoo19.conf                  /etc/odoo19.conf
cp configs/etc_systemd_system_odoo19.service /etc/systemd/system/odoo19.service
chown odoo19:odoo19 /etc/odoo19.conf
systemctl daemon-reload
systemctl enable odoo19

# Filestore
sudo -u odoo19 mkdir -p /opt/odoo19/.local/share/Odoo/filestore
sudo tar -C /opt/odoo19/.local/share/Odoo/filestore -xzf /path/to/filestore_CW19_Test.tar.gz
chown -R odoo19:odoo19 /opt/odoo19/.local/share/Odoo/filestore

systemctl start odoo19
```

### B.5 — Restore nginx + TLS

```bash
cp configs/etc_nginx_nginx.conf              /etc/nginx/nginx.conf
cp configs/etc_nginx_sites-enabled_default   /etc/nginx/sites-enabled/default
# Review the site config — it references TLS certs that are NOT in this backup.
# Re-issue them with certbot:
apt install -y certbot python3-certbot-nginx
certbot --nginx -d courtwell.com.hk -d www.courtwell.com.hk
# (DNS for these domains must already point to this host.)

systemctl restart nginx
```

### B.6 — Smoke test

```bash
# DB-level
sudo -u postgres psql -d CW19_Test -tAc "SELECT pg_size_pretty(pg_database_size('CW19_Test'));"
sudo -u postgres psql -d CW19_Test -tAc \
  "SELECT name, latest_version FROM ir_module_module \
   WHERE name LIKE 'cw_%' OR name = 'sourcing_reference' ORDER BY name;"

# Service-level
systemctl is-active odoo19 postgresql nginx
journalctl -u odoo19 -n 50 --no-pager

# HTTP-level
curl -I https://courtwell.com.hk/
```

Cross-check the snapshot file (`CW19_Test_20260608T101156Z_config_snapshot.txt`) against the queries above — module versions, pool state, row counts should all match.

---

# What this backup does NOT cover

| Item | Why excluded | What to do at restore |
|---|---|---|
| TLS certificates (`/etc/letsencrypt/`) | Easily re-issued via certbot DNS challenge; including them widens the sensitivity surface unnecessarily | Re-issue with certbot during B.5 |
| SSH host keys (`/etc/ssh/ssh_host_*`) | Restoring them lets impersonation of the original host; usually undesirable | Generate new keys on rebuild; SSH clients prompt about new fingerprint |
| `/var/log/` history | Bulky, not load-bearing | Accept loss; future logs accumulate normally |
| Customer-uploaded files outside the Odoo filestore | None such exist on this box; included only if you put files outside `~odoo19/.local/share/Odoo/` | n/a |
| Other databases (e.g. `Courtwell_Odoo19` prod DB) | Not part of CW19_Test backup scope per memory note "DO NOT touch without explicit instruction" | Backed up separately with its own dump if required |
| Crontabs | None configured for root or odoo19 on this host (Odoo's own cron lives in `ir.cron`, part of the DB dump) | n/a |

# Caveat on capture consistency

The DB dump (step 1) was taken at 10:11:56 UTC. The filestore tar and config copies (steps 2–4 in the augmentation pass) were captured shortly after (~10:41 UTC) without first stopping the Odoo service. For this test database with no active user traffic the gap is operationally irrelevant — neither the filestore nor the configs were being written to. If you want strictly atomic future backups, the pattern is: `systemctl stop odoo19 → pg_dump → tar → systemctl start odoo19`. Plan ~5 minutes of downtime for a backup of this size.
