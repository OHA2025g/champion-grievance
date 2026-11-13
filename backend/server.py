import asyncio
import os
import time
from collections import defaultdict, deque
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from core import db, log, client
import auth
import routes_records
import routes_ops
import routes_admin
import ai
import seed
import sla
import engine

app = FastAPI(title="Champion Electricals Service Desk API", version="1.0.0",
              description="Grievance, complaint, service and support ticket management. All endpoints are prefixed with /api.")
_hits = defaultdict(deque)
LIMITS = {"/api/auth/": 40, "/api/ai/": 20}


@app.middleware("http")
async def guard(request: Request, call_next):
    path = request.url.path
    if request.method == "POST":
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0]
        for prefix, limit in LIMITS.items():
            if path.startswith(prefix):
                q = _hits[(ip, prefix)]
                t = time.time()
                while q and t - q[0] > 60:
                    q.popleft()
                if len(q) >= limit:
                    return JSONResponse({"detail": {"message": "Too many requests. Please wait a minute.", "code": "rate_limited"}}, status_code=429)
                q.append(t)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return resp


for r in (auth.router, routes_records.router, routes_ops.router, routes_admin.router, routes_admin.dev, ai.router):
    app.include_router(r)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=[o.strip() for o in os.environ.get("CORS_ORIGINS", "*").split(",")], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
async def health():
    return {"ok": True}


async def indexes():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.records.create_index("id", unique=True)
    await db.records.create_index([("type", 1), ("state", 1)])
    for k in ("root_id", "parent_id", "owner_id", "technician_id", "customer_user_id", "org_id", "region", "sla_state", "created_at"):
        await db.records.create_index(k)
    await db.hr_records.create_index("id", unique=True)
    await db.events.create_index("record_id")
    await db.events.create_index("root_id")
    await db.hr_events.create_index("record_id")
    await db.communications.create_index("dedupe_key", unique=True, sparse=True)
    await db.communications.create_index("root_id")
    await db.idempotency.create_index("key", unique=True)
    await db.evidence.create_index("record_id")
    await db.notifications.create_index([("user_id", 1), ("at", -1)])
    await db.audit_logs.create_index([("at", -1)])
    await db.login_attempts.create_index("identifier")
    await db.knowledge.create_index([("title", "text"), ("body", "text")])


async def sla_loop():
    while True:
        try:
            await sla.tick()
        except Exception as e:
            log.warning("SLA tick failed: %s", e)
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup():
    await indexes()
    await seed.seed()
    await engine.load_overrides()
    asyncio.create_task(sla_loop())


@app.on_event("shutdown")
async def shutdown():
    client.close()
