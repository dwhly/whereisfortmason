#!/usr/bin/env bash
# Deploy site/ to Cloudflare Pages (project "whereisfortmason", custom domain whereisfortmason.com).
# The Cloudflare API token is read from 1Password at run time; it is never stored in the repo or typed in chat.
set -euo pipefail
cd "$(dirname "$0")/.."
: "${OP_ITEM:=op://hermes/Cloudflare-WhereIsFortMason}"
export CLOUDFLARE_API_TOKEN="$(op read "$OP_ITEM/credential")"
export CLOUDFLARE_ACCOUNT_ID="$(op read "$OP_ITEM/account_id")"
python3 scripts/build_site.py
npx --yes wrangler@4 pages project list | grep -q whereisfortmason || npx --yes wrangler@4 pages project create whereisfortmason --production-branch main
npx --yes wrangler@4 pages deploy site --project-name whereisfortmason --branch main --commit-dirty=true
