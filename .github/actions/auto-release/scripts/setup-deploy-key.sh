#!/usr/bin/env bash
#
# setup-deploy-key.sh - Fetch a repo-scoped deploy key from AWS Secrets
# Manager and point the git remote at it over SSH, so cut-release.sh can push
# straight to the default branch without a standing PAT. Same mechanism as
# aws-crt-swift's update-version.yml: the key is fetched fresh each run via
# the already-assumed CRT_CI_ROLE_ARN role, used once, and never persisted
# past the job.
#
# Inputs (env):
#   DEPLOY_KEY_SECRET_ID   Secrets Manager secret ID holding the private key

set -euo pipefail

DEPLOY_KEY_SECRET_ID="${DEPLOY_KEY_SECRET_ID:?DEPLOY_KEY_SECRET_ID must be set}"

mkdir -p ~/.ssh
aws secretsmanager get-secret-value --secret-id "$DEPLOY_KEY_SECRET_ID" \
  --query SecretString --output text > ~/.ssh/deploy_key
chmod 600 ~/.ssh/deploy_key

ssh-keyscan -H github.com >> ~/.ssh/known_hosts

cat > ~/.ssh/config << EOF
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/deploy_key
EOF
chmod 600 ~/.ssh/config

git remote set-url origin "git@github.com:${GITHUB_REPOSITORY}.git"
