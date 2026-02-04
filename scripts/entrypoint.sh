#!/usr/bin/env bash
set -euo pipefail

export FLASK_APP="${FLASK_APP:-app.wsgi:app}"
export FLASK_ENV="${FLASK_ENV:-development}"

wait_for_postgres() {
  python - <<'PY'
import os
import time

import psycopg2

database_url = os.getenv("DATABASE_URL", "")
if not database_url.startswith("postgres"):
    print("DATABASE_URL is not Postgres. Skipping DB wait.")
    raise SystemExit(0)

attempts = int(os.getenv("POSTGRES_WAIT_ATTEMPTS", "30"))
delay = float(os.getenv("POSTGRES_WAIT_DELAY", "2"))

for attempt in range(1, attempts + 1):
    try:
        conn = psycopg2.connect(database_url)
        conn.close()
        print("Postgres is ready.")
        break
    except Exception as exc:  # noqa: BLE001
        print(f"Postgres not ready ({attempt}/{attempts}): {exc}")
        time.sleep(delay)
else:
    raise SystemExit("Postgres did not become ready in time.")
PY
}

wait_for_postgres

if [[ "${FLASK_ENV}" == "development" || "${AUTO_SEED_SMOKE:-false}" == "true" ]]; then
  echo "Running migrations..."
  flask db upgrade
  echo "Seeding smoke scenario..."
  if [[ "${FLASK_ENV}" == "development" ]]; then
    flask seed --scenario smoke
  else
    flask seed --scenario smoke --allow-production
  fi
else
  echo "Skipping migrations and seed (not in development and AUTO_SEED_SMOKE!=true)."
fi

if [[ "${FLASK_ENV}" == "development" ]]; then
  exec flask run --host=0.0.0.0 --port="${PORT:-5000}"
else
  exec gunicorn -b "0.0.0.0:${PORT:-5000}" "app.wsgi:app"
fi
