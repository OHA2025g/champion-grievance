import os
import json
import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from core import db, iso, new_id, fail, audit
from auth import staff_user
from rbac import flags, check_view
import engine

router = APIRouter(prefix="/api/ai")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
TASKS = {
    "categorise": "Suggest the most likely issue category and product category. JSON keys: category, product_category, rationale.",
    "priority": "Recommend a priority among 'P1 - Critical','P2 - High','P3 - Normal','P4 - Low'. JSON keys: priority, rationale, escalation_risk (low|medium|high).",
    "summary": "Summarise the case for a service coordinator in at most 5 bullet sentences. JSON keys: summary (string), open_questions (list).",
    "sentiment": "Assess customer sentiment. JSON keys: sentiment (positive|neutral|negative|distressed), signals (list).",
    "draft_reply": "Draft a polite, factual customer update. Never promise remedies, refunds or warranty outcomes. JSON keys: draft, cautions (list).",
    "routing": "Suggest the responsible team among Service coordination, Safety coordination, Dealer cases, Business accounts, Warranty. JSON keys: team, rationale.",
    "root_cause": "Suggest possible root-cause hypotheses for investigation (not conclusions). JSON keys: hypotheses (list), tests_to_confirm (list).",
    "trend": "Summarise trends in the supplied complaint statistics. JSON keys: summary, notable (list).",
}


def configured():
    return bool(os.environ.get("MISTRAL_API_KEY"))


async def _call(system, user_text):
    if not configured():
        fail(503, "AI assistance is not configured (MISTRAL_API_KEY missing). Core workflows are unaffected.", code="ai_unconfigured")
    if not (await flags()).get("ai_assist", True):
        fail(503, "AI assistance is disabled by an administrator.", code="ai_disabled")
    body = {"model": os.environ.get("MISTRAL_MODEL", "mistral-small-latest"), "messages": [{"role": "system", "content": system}, {"role": "user", "content": user_text}],
            "response_format": {"type": "json_object"}, "temperature": 0.2}
    try:
        async with httpx.AsyncClient(timeout=45) as c:
            r = await c.post(MISTRAL_URL, headers={"Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}"}, json=body)
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"]), body["model"]
    except httpx.HTTPStatusError as e:
        await db.integration_events.insert_one({"id": new_id("evt"), "adapter": "Mistral AI", "event": "chat completion", "error": f"{e.response.status_code}", "state": "failed", "attempts": 1, "at": iso()})
        fail(502, f"AI provider error ({e.response.status_code}). Continue without AI assistance.", code="ai_failed")
    except Exception as e:
        fail(502, f"AI provider unavailable: {str(e)[:120]}", code="ai_failed")


class AssistIn(BaseModel):
    task: str
    record_id: str | None = None
    text: str | None = None


@router.get("/status")
async def status(user=Depends(staff_user)):
    return {"configured": configured(), "enabled": (await flags()).get("ai_assist", True), "provider": "Mistral AI", "model": os.environ.get("MISTRAL_MODEL", "mistral-small-latest")}


@router.post("/assist")
async def assist(body: AssistIn, user=Depends(staff_user)):
    if body.task not in TASKS:
        fail(422, "Unknown AI task")
    context = body.text or ""
    rec = None
    if body.record_id:
        rec = await engine.find(body.record_id)
        if not rec:
            fail(404, "Record not found")
        if rec["type"] == "hr_grievance":
            fail(403, "Confidential HR records are excluded from AI assistance.", code="forbidden")
        await check_view(user, rec)
        evs = await db.events.find({"record_id": rec["id"]}, {"_id": 0, "label": 1, "values": 1, "at": 1}).sort("at", 1).to_list(30)
        context = json.dumps({"ref": rec["ref"], "title": rec["title"], "state": rec["state"], "product": rec.get("product"), "data": {k: v for k, v in rec["data"].items() if isinstance(v, (str, int, float))},
                              "history": [e["label"] for e in evs]}, default=str)[:6000]
    if not context.strip():
        fail(422, "Provide text or a record to analyse.")
    system = ("You assist Champion Electricals service staff. You make suggestions only; humans decide. Do not invent warranty terms, policies, amounts or facts. "
              "Respond ONLY with a JSON object. " + TASKS[body.task])
    out, model = await _call(system, context)
    log = {"id": new_id("ai"), "task": body.task, "record_id": body.record_id, "output": out, "model": model, "provider": "Mistral AI", "by": user["id"], "by_name": user["name"], "at": iso(), "accepted": False}
    await db.ai_logs.insert_one(dict(log))
    return {**log, "label": "AI suggestion - unverified prediction, requires human review"}


class AcceptIn(BaseModel):
    log_id: str
    apply_text: str | None = None


@router.post("/accept")
async def accept(body: AcceptIn, user=Depends(staff_user)):
    log = await db.ai_logs.find_one({"id": body.log_id}, {"_id": 0})
    if not log:
        fail(404, "Suggestion not found")
    await db.ai_logs.update_one({"id": body.log_id}, {"$set": {"accepted": True, "accepted_by": user["id"], "accepted_at": iso(), "reviewed_text": body.apply_text}})
    if log.get("record_id") and log["task"] == "summary":
        rec = await engine.find(log["record_id"])
        await check_view(user, rec)
        await db.records.update_one({"id": rec["id"]}, {"$set": {"reviewed_summary": body.apply_text or str(log["output"].get("summary")), "reviewed_summary_by": user["name"]}})
        await engine.log_event(rec, user, "ai_summary_accepted", "Reviewed AI-assisted summary accepted", None, None)
    await audit(user, "ai_recommendation_accepted", "ai", body.log_id, {"task": log["task"], "record_id": log.get("record_id")})
    return {"ok": True}


class AskIn(BaseModel):
    question: str


@router.post("/knowledge")
async def knowledge(body: AskIn, user=Depends(staff_user)):
    arts = await db.knowledge.find({"$text": {"$search": body.question}, "audience": {"$in": [user["active_role"], "all"]}}, {"_id": 0, "score": {"$meta": "textScore"}}).sort([("score", {"$meta": "textScore"})]).to_list(4)
    if not arts:
        return {"answer": None, "sources": [], "note": "No approved article matched. AI was not called."}
    ctx = "\n\n".join(f"[{a['id']}] {a['title']}: {a['body']}" for a in arts)
    out, model = await _call("Answer only from the supplied approved articles. Cite article ids in a 'sources' list. If the articles do not answer, say so. JSON keys: answer, sources.", f"Articles:\n{ctx}\n\nQuestion: {body.question}")
    await db.ai_logs.insert_one({"id": new_id("ai"), "task": "knowledge", "question": body.question, "output": out, "model": model, "by": user["id"], "at": iso(), "accepted": False})
    return {"answer": out.get("answer"), "sources": [a for a in arts if a["id"] in (out.get("sources") or [])] or arts, "label": "AI answer from approved articles - verify against cited source"}
