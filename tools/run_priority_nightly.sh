#!/bin/bash
# Nightly priority-score recompute for Myugen.
# Loads env (Shopify token) + GA service-account creds, runs compute_priority.py,
# logs to .tmp/priority.log. Wire into cron/launchd to run once a night.
set -euo pipefail

REPO="/Users/adityasharma/Codes/claude_projects/culture-circle-inventory"
cd "$REPO"

# load .env (Shopify domain/token, DB creds)
set -a
. "$REPO/.env"
set +a

# GA service account
export GOOGLE_APPLICATION_CREDENTIALS="$REPO/.secrets/myugen-ga-sa.json"

mkdir -p "$REPO/.tmp"
echo "===== priority recompute $(date) =====" >> "$REPO/.tmp/priority.log"
"$REPO/venv/bin/python" "$REPO/tools/compute_priority.py" >> "$REPO/.tmp/priority.log" 2>&1
echo "===== done $(date) =====" >> "$REPO/.tmp/priority.log"
