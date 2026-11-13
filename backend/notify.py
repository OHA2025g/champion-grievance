import os
import re
import asyncio
import hashlib
import ipaddress
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse
import httpx
from pymongo.errors import DuplicateKeyError
from core import db, iso, new_id, get_config, log

EMAIL_BASE_URL = "https://integrations.emergentagent.com"
EMAIL_KEY = os.environ.get("EMERGENT_EMAIL_KEY")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "")
DEMO_DOMAINS = (".test", "example.com", "example.org")

TEMPLATES = {
    "ticket_created": ("Complaint {ref} registered", "We have registered your request {ref}: {title}. Keep this reference for all future contact."),
    "acknowledgement": ("We are working on {ref}", "Your request {ref} has been reviewed and routed to an accountable case owner."),
    "ownership_assigned": ("Case owner assigned for {ref}", "{owner} is now the accountable owner for {ref}."),
    "evidence_request": ("Information needed for {ref}", "To continue with {ref} we need: {message}"),
    "appointment_confirmation": ("Service visit proposed for {ref}", "A service visit has been proposed for {ref}. Please confirm the visit window in your portal."),
    "technician_assigned": ("Engineer assigned for {ref}", "An authorised service engineer has been assigned to {ref}."),
    "status_update": ("Update on {ref}", "{message}"),
    "approval_request": ("Approval requested for {ref}", "An approval is required for {ref}: {message}"),
    "approval_decision": ("Decision recorded for {ref}", "A decision has been recorded for {ref}."),
    "sla_warning": ("Service milestone approaching for {ref}", "A service milestone for {ref} is approaching its target time."),
    "escalation": ("{ref} has been escalated", "{ref} has been escalated to a specialist team. {message}"),
    "resolution": ("{ref} is resolved - please verify", "We believe {ref} is resolved. Please confirm the outcome or tell us what remains unresolved."),
    "closure": ("{ref} is closed", "{ref} has been closed. You can reopen it within the permitted window or request a decision review."),
    "reopening": ("{ref} has been reopened", "{ref} has been reopened and returned to the accountable owner."),
    "appeal_outcome": ("Decision review outcome for {ref}", "The independent review of {ref} is complete. {message}"),
}


async def templates():
    cfg = await get_config("templates", {}) or {}
    out = {k: {"subject": s, "body": b} for k, (s, b) in TEMPLATES.items()}
    for k, v in cfg.items():
        if isinstance(v, dict) and k in out:
            out[k].update({kk: vv for kk, vv in v.items() if kk in ("subject", "body")})
    return out


def _fmt(s, ctx):
    return re.sub(r"\{(\w+)\}", lambda m: str(ctx.get(m.group(1), "")), s)


async def to_users(user_ids, title, body, rec=None, tone="info"):
    ids = [u for u in dict.fromkeys(user_ids or []) if u]
    docs = [{"id": new_id("ntf"), "user_id": u, "title": title, "body": body, "record_id": (rec or {}).get("id"),
             "record_ref": (rec or {}).get("ref"), "tone": tone, "read": False, "at": iso()} for u in ids]
    if docs:
        await db.notifications.insert_many(docs)


async def to_roles(roles, title, body, rec=None, tone="info", region=None, centre=None):
    q = {"roles": {"$in": roles}, "status": "active"}
    if region:
        q["$or"] = [{"regions": region}, {"regions": {"$size": 0}}, {"regions": {"$exists": False}}]
    if centre:
        q["centre_id"] = centre
    ids = [u["id"] async for u in db.users.find(q, {"_id": 0, "id": 1})]
    await to_users(ids, title, body, rec, tone)


def is_demo_address(email):
    return not email or email.lower().endswith(DEMO_DOMAINS)


async def recipient_for(rec):
    if rec.get("customer_user_id"):
        u = await db.users.find_one({"id": rec["customer_user_id"]}, {"_id": 0})
        if u:
            return {"user_id": u["id"], "name": u["name"], "email": u.get("email"), "phone": u.get("phone"),
                    "channel": (u.get("preferences") or {}).get("contact_channel", "Email")}
    if rec.get("customer_id"):
        c = await db.customers.find_one({"id": rec["customer_id"]}, {"_id": 0})
        if c:
            return {"user_id": c.get("user_id"), "name": c["name"], "email": c.get("email"), "phone": c.get("phone"), "channel": c.get("preferred_contact", "SMS")}
    if rec.get("org_id"):
        u = await db.users.find_one({"org_id": rec["org_id"], "roles": {"$in": ["R02", "R03"]}}, {"_id": 0})
        if u:
            return {"user_id": u["id"], "name": u["name"], "email": u.get("email"), "phone": u.get("phone"), "channel": "Email"}
    return None


def _channel(c):
    c = (c or "").lower()
    if "whatsapp" in c:
        return "whatsapp"
    if "sms" in c or "phone" in c:
        return "sms"
    if "portal" in c:
        return "portal"
    return "email"


async def customer(rec, tpl, message="", channel=None, actor=None):
    """Customer-facing communication: portal message always, plus the preferred external channel."""
    r = await recipient_for(rec)
    if not r:
        return
    t = (await templates())[tpl]
    ctx = {"ref": rec.get("root_ref") or rec["ref"], "title": rec.get("title", ""), "owner": rec.get("owner_name") or "Your case owner", "message": message or ""}
    subject, body = _fmt(t["subject"], ctx), _fmt(t["body"], ctx)
    if r.get("user_id"):
        await to_users([r["user_id"]], subject, body, rec)
    ch = _channel(channel or r.get("channel"))
    target = r.get("email") if ch == "email" else r.get("phone")
    await _record_comm(rec, tpl, "portal", r["name"], subject, body, "delivered_in_app", actor)
    if ch != "portal":
        await _record_comm(rec, tpl, ch, target, subject, body, None, actor)


async def _record_comm(rec, tpl, channel, to, subject, body, state, actor):
    key = hashlib.sha256(f"{rec['id']}:{tpl}:{rec.get('version')}:{channel}:{to}:{body}".encode()).hexdigest()
    doc = {"id": new_id("com"), "record_id": rec["id"], "root_id": rec.get("root_id") or rec["id"], "ref": rec["ref"], "template": tpl,
           "channel": channel, "direction": "outbound", "recipient": to, "subject": subject, "body": body, "at": iso(),
           "actor": (actor or {}).get("name", "system"), "dedupe_key": key, "visibility": "customer"}
    if state:
        doc["state"] = state
    elif channel == "email":
        if not EMAIL_KEY or not EMAIL_FROM_NAME:
            doc["state"] = "not_sent_unconfigured"
        elif is_demo_address(to):
            doc["state"] = "suppressed_demo_recipient"
        else:
            doc["state"] = "queued"
    else:
        doc["state"] = "dev_adapter_not_sent"
        doc["adapter_note"] = f"{channel.upper()} DEV ADAPTER - no real message was sent (provider not configured)"
    try:
        await db.communications.insert_one(dict(doc))
    except DuplicateKeyError:
        log.info("duplicate notification suppressed %s", key[:10])
        return
    if doc["state"] == "queued":
        asyncio.create_task(deliver_email(doc["id"]))


def email_html(subject, body):
    return (f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#17243c">'
            f'<p style="font-size:16px;font-weight:bold">{escape(subject)}</p><p>{escape(body)}</p>'
            f'<p>Sign in to your Champion service portal to view details.</p>'
            f'<p style="font-size:12px;color:#888">Sent by {escape(EMAIL_FROM_NAME)}. We never ask for your password, OTP or card details by email.</p></td></tr></table>')


async def deliver_email(comm_id):
    c = await db.communications.find_one({"id": comm_id}, {"_id": 0})
    if not c:
        return
    try:
        pid = await send_email(to=c["recipient"], subject=c["subject"], html=email_html(c["subject"], c["body"]))
        await db.communications.update_one({"id": comm_id}, {"$set": {"state": "sent", "provider_ref": pid, "sent_at": iso()}})
    except Exception as e:
        await db.communications.update_one({"id": comm_id}, {"$set": {"state": "failed", "error": str(e)[:300]}})
        await db.integration_events.update_one({"comm_id": comm_id}, {"$set": {"comm_id": comm_id, "adapter": "Email (Resend)", "event": f"send {c['template']}",
                                                "record_id": c["record_id"], "ref": c["ref"], "error": str(e)[:300], "state": "failed", "at": iso()},
                                               "$inc": {"attempts": 1}, "$setOnInsert": {"id": new_id("evt")}}, upsert=True)


async def send_plain_email(to, subject, body):
    """Account emails (OTP/recovery). Returns delivery state honestly."""
    if not EMAIL_KEY or not EMAIL_FROM_NAME:
        return "not_sent_unconfigured"
    if is_demo_address(to):
        return "suppressed_demo_recipient"
    try:
        await send_email(to=to, subject=subject, html=email_html(subject, body))
        return "sent"
    except Exception as e:
        log.warning("account email failed: %s", e)
        return "failed"


# ---- Emergent managed email (Resend) - guardrail gate copied from the integration playbook ----
_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\b(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})", re.I)


def _host_ok(host):
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown, real):
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject, html):
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} differs from link host {real!r} (G3)")


async def send_email(*, to, subject, html):
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": EMAIL_FROM_NAME}
    if os.environ.get("EMAIL_REPLY_TO"):
        payload["contact_email"] = os.environ["EMAIL_REPLY_TO"]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": EMAIL_KEY}, json=payload)
    if resp.status_code >= 400:
        try:
            code = resp.json().get("code", "")
        except ValueError:
            code = ""
        raise RuntimeError(f"email provider {resp.status_code} {code}".strip())
    return resp.json().get("id")
