import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import db, DEV_MODE  # noqa: E402
import seed  # noqa: E402

DEMO_COLLECTIONS = ["records", "hr_records", "events", "hr_events", "communications", "notifications", "evidence", "evidence_files.files", "evidence_files.chunks",
                    "idempotency", "counters", "ai_logs", "movements", "exports", "integration_events", "customers", "products", "orders", "parts", "warehouses",
                    "stock", "knowledge", "orgs", "product_models", "otp_codes", "reset_tokens", "login_attempts", "user_sessions", "payment_instructions"]


async def main():
    if not DEV_MODE:
        sys.exit("Refusing to reset: DEV_MODE is not true.")
    for c in DEMO_COLLECTIONS:
        await db[c].delete_many({})
    r = await db.users.delete_many({"$or": [{"demo": True}, {"email": {"$regex": "^test_|@example\\.com$", "$options": "i"}}]})
    await db.meta.delete_one({"_id": "seed"})
    print("users removed", r.deleted_count)
    await seed.seed()
    print("records", await db.records.count_documents({}), "users", await db.users.count_documents({}))


asyncio.run(main())
