import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402
from pymongo import ReturnDocument  # noqa: E402
from fastapi import HTTPException  # noqa: E402

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
DEV_MODE = os.environ.get("DEV_MODE", "false").lower() == "true"
log = logging.getLogger("champion")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def now():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or now()).isoformat()


def parse_dt(s):
    if isinstance(s, datetime):
        d = s
    else:
        d = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def new_id(prefix="id"):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


async def next_ref(prefix):
    doc = await db.counters.find_one_and_update(
        {"_id": prefix}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return f"{prefix}-{now().year}-{doc['seq']:05d}"


def fail(status, message, **extra):
    raise HTTPException(status_code=status, detail={"message": message, **extra})


async def audit(user, action, obj_type="", obj_id="", detail=None, sensitive=False, outcome="ok"):
    await db.audit_logs.insert_one({
        "id": new_id("aud"), "at": iso(),
        "actor_id": (user or {}).get("id", "system"), "actor": (user or {}).get("email", "system"),
        "role": (user or {}).get("active_role", ""), "action": action, "object_type": obj_type,
        "object_id": obj_id, "detail": detail or {}, "sensitive": sensitive, "outcome": outcome,
        "correlation": new_id("cor"),
    })


async def get_config(key, default=None):
    doc = await db.config.find_one({"key": key}, {"_id": 0})
    return doc["value"] if doc else default


async def set_config(key, value, user=None, note=""):
    cur = await db.config.find_one({"key": key}, {"_id": 0})
    ver = (cur or {}).get("version", 0) + 1
    by = (user or {}).get("email", "system")
    await db.config.update_one({"key": key}, {"$set": {"key": key, "value": value, "version": ver, "updated_at": iso(), "updated_by": by, "note": note}}, upsert=True)
    await db.config_versions.insert_one({"key": key, "version": ver, "value": value, "at": iso(), "by": by, "note": note})
    return ver


def public_user(u):
    keep = ["id", "email", "name", "roles", "active_role", "org_id", "org_name", "centre_id", "centre_name", "regions", "skills", "phone", "status", "demo", "preferences", "confidentiality", "customer_id"]
    return {k: u.get(k) for k in keep}
