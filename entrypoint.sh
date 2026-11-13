#!/bin/sh
set -e

cd /backend || { echo "Backend directory not found"; exit 1; }

echo "Starting FastAPI backend on :8001"
uvicorn server:app --host 127.0.0.1 --port 8001 &
BACKEND_PID=$!

echo "Waiting for backend health..."
i=0
while [ "$i" -lt 60 ]; do
  if curl -fsS http://127.0.0.1:8001/api/health >/dev/null 2>&1; then
    echo "Backend is up"
    break
  fi
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "Backend failed to start"
    exit 1
  fi
  i=$((i + 1))
  sleep 1
done

if [ "$i" -ge 60 ]; then
  echo "Backend health check timed out"
  exit 1
fi

echo "Starting nginx on :8080"
nginx -g 'daemon off;' &
NGINX_PID=$!

trap 'kill $BACKEND_PID $NGINX_PID 2>/dev/null; exit 0' TERM INT

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$NGINX_PID" 2>/dev/null; do
  sleep 1
done

if kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "Nginx exited; shutting down backend"
  kill "$BACKEND_PID" 2>/dev/null || true
else
  echo "Backend exited; shutting down nginx"
  kill "$NGINX_PID" 2>/dev/null || true
fi

exit 1
