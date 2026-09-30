#!/usr/bin/env bash
set -euo pipefail

release_dir=${1:?release directory required}
app_dir=/opt/hackathon2026

if [[ ! -f "$release_dir/compose.yaml" || ! -f "$release_dir/backend/app.jar" || ! -f "$release_dir/frontend/Dockerfile" || ! -f "$release_dir/frontend/dist/index.html" || ! -f "$release_dir/ml/Dockerfile" || ! -f "$release_dir/ml/requirements.txt" || ! -f "$release_dir/ml/ml_study.py" || ! -f "$release_dir/ml/profile_api.py" || ! -f "$release_dir/data/tom_transactions.csv" || ! -f "$release_dir/data/maria_transactions.csv" ]]; then
  echo 'Incomplete release directory' >&2
  exit 1
fi

install -d -m 700 "$app_dir"
install -d -m 755 "$app_dir/backend" "$app_dir/frontend" "$app_dir/data" "$app_dir/ml" "$app_dir/profiles"
install -m 644 "$release_dir/compose.yaml" "$app_dir/compose.yaml"
install -m 644 "$release_dir/backend/Dockerfile" "$app_dir/backend/Dockerfile"
install -m 644 "$release_dir/backend/app.jar" "$app_dir/backend/app.jar"
for ml_file in Dockerfile requirements.txt ml_study.py profile_api.py; do
  install -m 644 "$release_dir/ml/$ml_file" "$app_dir/ml/$ml_file"
done
install -m 644 "$release_dir/data/tom_transactions.csv" "$app_dir/data/tom_transactions.csv"
install -m 644 "$release_dir/data/maria_transactions.csv" "$app_dir/data/maria_transactions.csv"
install -m 644 "$release_dir/frontend/Dockerfile" "$app_dir/frontend/Dockerfile"
install -m 644 "$release_dir/frontend/nginx.conf" "$app_dir/frontend/nginx.conf"
rm -rf "$app_dir/frontend/dist"
cp -a "$release_dir/frontend/dist" "$app_dir/frontend/dist"

# Recompute the artifact from the exact CSV snapshot on every deployment.
docker build -t hackathon2026-ml "$app_dir/ml"
docker run --rm --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --memory 768m -e TRANSACTIONS_DIR=/app/data -e ML_PROFILE_DIR=/app/profiles \
  -v "$app_dir/data:/app/data:ro" -v "$app_dir/profiles:/app/profiles:rw" hackathon2026-ml
test -s "$app_dir/profiles/profile_suggestions.json"
chmod 644 "$app_dir/profiles/profile_suggestions.json"

if [[ ! -f "$app_dir/.env" ]]; then
  umask 077
  printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 24)" > "$app_dir/.env"
fi

cd "$app_dir"
docker compose --project-name hackathon2026 --env-file .env up -d --build --remove-orphans

for attempt in $(seq 1 40); do
  if curl -fsS http://localhost/api/health | grep -q '"status":"ok"'; then
    echo 'Health check passed'
    exit 0
  fi
  sleep 5
done

docker compose --project-name hackathon2026 --env-file .env ps >&2
echo 'Deployment health check failed' >&2
exit 1
