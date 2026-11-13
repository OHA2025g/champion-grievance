"""SIMULATED payment adapter. No real funds move. Replace with a configured provider before production."""
from core import db, iso, new_id

ADAPTER_NAME = "SIMULATED payment adapter (development) - no real funds moved"


async def submit(rec, key):
    existing = await db.payment_instructions.find_one({"key": key}, {"_id": 0})
    if existing:
        return existing
    doc = {"id": new_id("pay"), "key": key, "settlement_id": rec["id"], "reference": f"SIM-{new_id('')[1:9].upper()}", "amount": rec.get("amount"),
           "at": iso(), "checks": 0, "adapter": ADAPTER_NAME}
    await db.payment_instructions.insert_one(dict(doc))
    return doc


async def status(rec):
    ins = await db.payment_instructions.find_one({"settlement_id": rec["id"], "reference": rec.get("instruction_ref")}, {"_id": 0})
    if not ins:
        return {"state": "unknown", "detail": "No instruction found at simulated provider"}
    checks = ins.get("checks", 0) + 1
    await db.payment_instructions.update_one({"id": ins["id"]}, {"$set": {"checks": checks}})
    ben = (rec.get("beneficiary_reference") or "").upper()
    if "FAIL" in ben and rec.get("attempts", 1) == 1:
        return {"state": "failed", "detail": "Simulated provider rejected the instruction (beneficiary reference contains FAIL on first attempt)"}
    if "UNKNOWN" in ben and checks == 1:
        return {"state": "unknown", "detail": "Simulated provider timeout - outcome unknown; enquire again"}
    return {"state": "executed", "provider_ref": f"SIMPAY-{ins['reference'][4:]}", "detail": "Simulated execution recorded", "checked_at": iso()}
