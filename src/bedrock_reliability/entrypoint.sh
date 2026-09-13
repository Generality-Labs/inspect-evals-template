#!/bin/bash
# Starts both sandbox services and keeps the container alive for the sample's
# duration. Fails loudly (bedrock's own principle, see agent/plan.py) rather
# than leaving a half-started sandbox for the solver to time out against.
set -euo pipefail

python3 /opt/bedrock/site_server.py &
SITE_PID=$!
python3 /opt/bedrock/control_server.py &
CONTROL_PID=$!

check() {
  python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$1/healthz', timeout=1)" \
    >/dev/null 2>&1
}

ready=0
for _ in $(seq 1 30); do
  if ! kill -0 "$SITE_PID" 2>/dev/null; then
    echo "site_server exited before becoming healthy" >&2
    exit 1
  fi
  if ! kill -0 "$CONTROL_PID" 2>/dev/null; then
    echo "control_server exited before becoming healthy" >&2
    exit 1
  fi
  if check 8080 && check 8000; then
    ready=1
    break
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "site_server/control_server did not become healthy in time" >&2
  exit 1
fi

echo "bedrock_reliability sandbox ready"

# If either service dies later, exit so the failure is visible instead of the
# sandbox silently serving nothing for the rest of the sample.
wait -n "$SITE_PID" "$CONTROL_PID"
code=$?
echo "a sandbox service exited (code $code) — stopping container" >&2
exit "$code"
