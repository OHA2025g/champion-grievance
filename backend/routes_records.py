import json
import hashlib
import re
from fastapi import APIRouter, Depends, Request, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from core import db, iso, new_id, fail, audit
from auth import get_current_user
from rbac import scope_query, check_view, EXTERNAL, MINIMAL_CASE_FIELDS
from workflows import TERMINAL, WF
import engine
import notify

router = APIRouter(prefix="/api")
FILTER_KEYS = {"subtype", "safety_flag", "required_role", "sla_state", "priority", "region", "approval_type", "parent_type", "parent_id", "root_id", "quarantine", "level",
               "technician_id", "owner_id", "proposed_owner_id", "assignee_id", "estimate_state", "centre_id", "org_id", "customer_user_id", "under_appeal", "action_owner_id"}
LIST_PROJ = {"_id": 0, "sla": 0, "restricted_to": 0}
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".pdf", ".mp4", ".txt", ".csv", ".docx", ".xlsx", ".webp", ".heic"}
MAGIC = {".png": b"\x89PNG", ".jpg": b"\xff\xd8", ".jpeg": b"\xff\xd8", ".pdf": b"%PDF"}
EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR"
MAX_BYTES = 10 * 1024 * 1024


def ext_view(rec, user):
    """Projection for customers/dealers/distributors: hide internal working data."""
    if user["active_role"] not in EXTERNAL:
        return rec
    wf = WF[rec["type"]]
    allowed = {f["k"] for spec in wf["create"].values() for f in spec["fields"]} | {f["k"] + "_label" for spec in wf["create"].values() for f in spec["fields"]}
    allowed |= {a["key"] for a in wf["actions"] if a["cust"]}
    hide = {"possible_duplicates", "proposed_owner_id", "diagnosis", "repeat_count", "first_time_fix", "approval_required"}
    out = {k: v for k, v in rec.items() if k not in hide}
    out["data"] = {k: v for k, v in rec.get("data", {}).items() if k in allowed}
    return out


def mask(rec):
    if rec["type"] == "hr_grievance" and rec.get("data", {}).get("complainant_contact"):
        c = rec["data"]["complainant_contact"]
        rec["data"]["complainant_contact"] = c[:2] + "****" + c[-2:] if len(c) > 4 else "****"
    return rec


async def build_query(user, rtype, state=None, subtype=None, q=None, flt=None):
    scope = await scope_query(user, rtype)
    if scope is None:
        await audit(user, "list_denied", rtype, "", outcome="denied")
        fail(403, "Your role does not have access to these records.", code="forbidden")
    query = {"type": rtype}
    if state:
        sts = state.split(",")
        if "open" in sts:
            query["state"] = {"$nin": TERMINAL[rtype]}
        else:
            query["state"] = {"$in": sts}
    if subtype:
        query["subtype"] = {"$in": subtype.split(",")}
    if flt:
        for k, v in flt.items():
            if k in FILTER_KEYS or k.startswith("data."):
                query[k] = user["id"] if v == "$me" else ({"$in": v} if isinstance(v, list) else v)
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$or"] = [{"ref": rx}, {"title": rx}, {"customer_name": rx}, {"data.serial": rx}, {"org_name": rx}]
    return {"$and": [query, scope]} if scope else query


@router.get("/records")
async def list_records(type: str, state: str = None, subtype: str = None, q: str = None, filter: str = None, page: int = 1, size: int = 20, sort: str = "-created_at", user=Depends(get_current_user)):
    if type not in WF:
        fail(404, "Unknown record type")
    flt = json.loads(filter) if filter else None
    query = await build_query(user, type, state, subtype, q, flt)
    coll = engine.coll(type)
    size = max(1, min(size, 100))
    key = sort.lstrip("-")
    proj = {k: 1 for k in MINIMAL_CASE_FIELDS} | {"_id": 0} if type == "case" and user["active_role"] == "R13" else LIST_PROJ
    items = await coll.find(query, proj).sort(key, -1 if sort.startswith("-") else 1).skip((page - 1) * size).limit(size).to_list(size)
    total = await coll.count_documents(query)
    if type == "hr_grievance":
        await audit(user, "hr_list_viewed", type, "", {"count": len(items)}, sensitive=True)
    return {"items": [mask(ext_view(i, user)) for i in items], "total": total, "page": page, "size": size}


@router.get("/records/{rid}")
async def get_record(rid: str, user=Depends(get_current_user)):
    rec = await engine.find(rid)
    if not rec:
        fail(404, "Record not found")
    scope = await check_view(user, rec)
    if scope == "minimal":
        rec = {k: rec.get(k) for k in MINIMAL_CASE_FIELDS}
        return {"record": rec, "actions": [], "events": [], "evidence": [], "children": [], "comms": [], "minimal": True}
    ext = user["active_role"] in EXTERNAL
    evq = {"record_id": rid} if rec["type"] != "case" else {"$or": [{"record_id": rid}, {"root_id": rid, "type": {"$in": ["job", "approval", "settlement", "warranty"]}}]}
    if ext:
        evq = {"$and": [evq, {"visibility": "customer"}]}
    evc = db.hr_events if rec["type"] == "hr_grievance" else db.events
    events = await evc.find(evq, {"_id": 0}).sort("at", -1).to_list(200)
    evidence = await db.evidence.find({"record_id": rid} if not ext else {"record_id": rid, "visibility": {"$ne": "internal"}}, {"_id": 0, "file_id": 0}).sort("at", -1).to_list(100)
    children = []
    if rec["type"] != "hr_grievance":
        cq = {"$or": [{"parent_id": rid}, {"root_id": rid}]}
        raw = await db.records.find(cq, {"_id": 0, "id": 1, "ref": 1, "type": 1, "subtype": 1, "title": 1, "state": 1, "owner_name": 1, "assignee_name": 1, "technician_name": 1,
                                         "parent_id": 1, "amount": 1, "required_role": 1, "data.mandatory": 1, "appointment": 1, "estimate": 1, "estimate_state": 1, "data.site": 1, "data.serial": 1, "job_ref": 1}).to_list(300)
        for c in raw:
            q = await scope_query(user, c["type"])
            if q is None:
                continue
            if q and not await db.records.find_one({"$and": [{"id": c["id"]}, q]}, {"_id": 1}):
                continue
            children.append(ext_view(c, user) if ext else c)
    comms = await db.communications.find({"root_id": rec.get("root_id") or rid} if not ext else {"root_id": rec.get("root_id") or rid, "visibility": "customer"}, {"_id": 0, "dedupe_key": 0}).sort("at", -1).to_list(100)
    out = {"record": mask(ext_view(rec, user)), "actions": engine.allowed_actions(rec, user), "events": events, "evidence": evidence, "children": children, "comms": comms,
           "read_only": scope == "ro"}
    if rec["type"] == "case" and not ext:
        out["dependencies"] = await engine.pending_dependencies(rec)
    if rec.get("parent_id"):
        p = await engine.find(rec["parent_id"])
        if p:
            out["parent"] = {k: p.get(k) for k in ("id", "ref", "type", "title", "state")}
    if rec["type"] == "hr_grievance" or user["active_role"] == "R21":
        await audit(user, "record_viewed", rec["type"], rid, {"ref": rec["ref"]}, sensitive=rec["type"] == "hr_grievance")
    return out


class CreateIn(BaseModel):
    values: dict = {}
    parent_id: str | None = None


@router.post("/records/{rid}/evidence")
async def upload(rid: str, file: UploadFile = File(...), category: str = Form("Supporting evidence"), visibility: str = Form("shared"), user=Depends(get_current_user)):
    rec = await engine.find(rid)
    if not rec:
        fail(404, "Record not found")
    scope = await check_view(user, rec)
    if scope in ("ro", "minimal"):
        fail(403, "Read-only access cannot add evidence.", code="read_only")
    if engine.is_terminal(rec):
        fail(409, "Evidence cannot be added to a closed record. Reopen or appeal first.")
    name = re.sub(r"[^A-Za-z0-9._-]", "_", file.filename or "upload")[-80:]
    ext = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    if ext not in ALLOWED_EXT:
        fail(422, f"File type {ext or '(none)'} is not allowed. Allowed: {', '.join(sorted(ALLOWED_EXT))}", code="upload_rejected")
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        fail(413, "File exceeds the 10 MB limit.", code="upload_rejected")
    if not content:
        fail(422, "Empty file.", code="upload_rejected")
    state, note = scan(content, ext)
    eid = new_id("evd")
    file_id = await AsyncIOMotorGridFSBucket(db, bucket_name="evidence_files").upload_from_stream(f"{eid}{ext}", content, metadata={"record_id": rid, "evidence_id": eid})
    doc = {"id": eid, "record_id": rid, "root_id": rec.get("root_id") or rid, "ref": rec["ref"], "filename": name, "size": len(content), "sha256": hashlib.sha256(content).hexdigest(),
           "mime": file.content_type, "category": category, "visibility": "internal" if visibility == "internal" and user["active_role"] not in EXTERNAL else "shared",
           "scan_state": state, "scan_note": note, "uploaded_by": user["id"], "uploaded_by_name": user["name"], "uploaded_by_role": user["active_role"], "at": iso(), "file_id": str(file_id)}
    await db.evidence.insert_one(dict(doc))
    await engine.log_event(rec, user, "evidence_added" if state == "clean" else "evidence_quarantined", f"Evidence {'added' if state == 'clean' else 'quarantined'}: {name}", None, None,
                           {"category": category, "scan": state}, cust=True)
    await audit(user, "evidence_upload", rec["type"], rid, {"file": name, "scan": state})
    if state != "clean":
        await notify.to_roles(["R04"], f"Evidence quarantined on {rec['ref']}", note, rec, "urgent")
    doc.pop("file_id")
    return doc


@router.post("/records/{rtype}/{subtype}")
async def create(rtype: str, subtype: str, body: CreateIn, user=Depends(get_current_user)):
    if rtype not in WF:
        fail(404, "Unknown record type")
    parent = None
    if body.parent_id:
        parent = await engine.find(body.parent_id)
        if parent:
            await check_view(user, parent)
    rec = await engine.create_record(user, rtype, subtype, body.values, parent=parent)
    return {"id": rec["id"], "ref": rec["ref"], "state": rec["state"], "safety_flag": rec.get("safety_flag"), "possible_duplicates": rec.get("possible_duplicates", [])}


class ActionIn(BaseModel):
    values: dict = {}
    expected_version: int | None = None


@router.post("/records/{rid}/actions/{key}")
async def action(rid: str, key: str, body: ActionIn, request: Request, user=Depends(get_current_user)):
    return await engine.run_action(user, rid, key, body.values, request.headers.get("Idempotency-Key"), body.expected_version)


@router.get("/records/{rid}/duplicates")
async def duplicates(rid: str, user=Depends(get_current_user)):
    rec = await engine.find(rid)
    if not rec:
        fail(404, "Record not found")
    await check_view(user, rec)
    ors = []
    if rec.get("customer_id"):
        ors.append({"customer_id": rec["customer_id"]})
    if rec["data"].get("serial"):
        ors.append({"data.serial": rec["data"]["serial"]})
    if rec.get("model_id") and rec.get("customer_name"):
        ors.append({"model_id": rec["model_id"], "customer_name": rec["customer_name"]})
    if not ors:
        return {"items": []}
    items = await db.records.find({"type": "case", "id": {"$ne": rid}, "$or": ors}, {"_id": 0, "sla": 0}).sort("created_at", -1).to_list(10)
    for i in items:
        i["match"] = [k for k, ok in (("Same customer", i.get("customer_id") == rec.get("customer_id") and rec.get("customer_id")),
                                       ("Same serial", rec["data"].get("serial") and i["data"].get("serial") == rec["data"].get("serial")),
                                       ("Same product", i.get("model_id") == rec.get("model_id"))) if ok]
    return {"items": items}


def scan(content, ext):
    if EICAR in content:
        return "quarantined", "Malware signature detected (EICAR test signature)"
    m = MAGIC.get(ext)
    if m and not content.startswith(m):
        return "quarantined", "File content does not match its declared type"
    return "clean", "Built-in signature scan (development scanner - integrate an AV engine for production)"


@router.get("/evidence/quarantine")
async def quarantine(user=Depends(get_current_user)):
    if user["active_role"] not in ("R04", "R05", "R14", "R18"):
        fail(403, "Not permitted", code="forbidden")
    return {"items": await db.evidence.find({"scan_state": "quarantined"}, {"_id": 0, "file_id": 0}).sort("at", -1).to_list(100)}


@router.post("/evidence/{eid}/request-replacement")
async def request_replacement(eid: str, user=Depends(get_current_user)):
    if user["active_role"] not in ("R04", "R05"):
        fail(403, "Not permitted", code="forbidden")
    ev = await db.evidence.find_one({"id": eid}, {"_id": 0})
    if not ev:
        fail(404, "Evidence not found")
    rec = await engine.find(ev["record_id"])
    await db.evidence.update_one({"id": eid}, {"$set": {"scan_state": "quarantined_replacement_requested", "replacement_requested_at": iso()}})
    await notify.customer(rec, "evidence_request", f"The file '{ev['filename']}' could not be accepted by our security scan. Please upload a safe replacement copy.", actor=user)
    await engine.log_event(rec, user, "evidence_replacement_requested", f"Safe replacement requested for {ev['filename']}", None, None, cust=True)
    return {"ok": True}


@router.get("/evidence/{eid}/download")
async def download(eid: str, user=Depends(get_current_user)):
    ev = await db.evidence.find_one({"id": eid}, {"_id": 0})
    if not ev:
        fail(404, "Evidence not found")
    rec = await engine.find(ev["record_id"])
    await check_view(user, rec)
    if ev["scan_state"] != "clean":
        fail(423, "This file is quarantined and cannot be opened.", code="quarantined")
    if ev["visibility"] == "internal" and user["active_role"] in EXTERNAL:
        fail(403, "Not permitted", code="forbidden")
    await audit(user, "evidence_download", rec["type"], rec["id"], {"file": ev["filename"]}, sensitive=rec["type"] == "hr_grievance")
    stream = await AsyncIOMotorGridFSBucket(db, bucket_name="evidence_files").open_download_stream(ObjectId(ev["file_id"]))
    data = await stream.read()
    return Response(content=data, media_type=ev.get("mime") or "application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{ev["filename"]}"'})
