# Stage 1: build React frontend
FROM node:20-bookworm AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY frontend/ ./
ARG REACT_APP_BACKEND_URL=http://localhost:8310
ENV REACT_APP_BACKEND_URL=${REACT_APP_BACKEND_URL}
ENV DISABLE_EMERGENT_OVERLAY=true
RUN yarn build

# Stage 2: runtime (nginx + FastAPI)
FROM python:3.11-slim-bookworm

RUN apt-get update \
  && apt-get install -y --no-install-recommends nginx curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /backend
COPY backend/requirements.txt /tmp/requirements.txt
# emergentintegrations is private/not on public PyPI and unused by app code
RUN grep -v '^emergentintegrations' /tmp/requirements.txt > /tmp/req.txt \
  && echo 'httpx>=0.27.0' >> /tmp/req.txt \
  && pip install --no-cache-dir -r /tmp/req.txt \
  && rm -f /tmp/requirements.txt /tmp/req.txt

COPY backend/ /backend/
COPY --from=frontend-build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh \
  && mkdir -p /backend/uploads /backend/data \
  && rm -f /etc/nginx/sites-enabled/default

ENV PYTHONUNBUFFERED=1
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8080/api/health || exit 1

CMD ["/entrypoint.sh"]
