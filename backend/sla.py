from datetime import timedelta
from core import db, now, iso, parse_dt, get_config, new_id

# PLACEHOLDER SLA values (business minutes) - require confirmation against the Champion BRD/SRS.
DEFAULT_SLA = {
    "_note": "PLACEHOLDER values pending BRD/SRS confirmation",
    "warn_ratio": 0.8,
    "case": {
        "P1": {"calendar": "24x7", "first_response": 30, "assignment": 60, "initial_assessment": 120, "technician_scheduling": 240, "resolution": 1440},
        "P2": {"calendar": "business", "first_response": 120, "assignment": 240, "initial_assessment": 540, "technician_scheduling": 1080, "resolution": 2700},
        "P3": {"calendar": "business", "first_response": 240, "assignment": 540, "initial_assessment": 1080, "technician_scheduling": 1620, "resolution": 4320},
        "P4": {"calendar": "business", "first_response": 540, "assignment": 1080, "initial_assessment": 2160, "technician_scheduling": 2700, "resolution": 8640},
    },
    "appeal": {"P3": {"calendar": "business", "review": 5400}},
    "escalation": {"P3": {"calendar": "business", "response": 240}},
    "warranty": {"P3": {"calendar": "business", "decision": 1080}},
}
DEFAULT_CALENDAR = {"_note": "DEMO calendar - holidays are placeholders, not Champion holidays", "tz_offset_minutes": 330,
                    "workdays": [0, 1, 2, 3, 4, 5], "start": "09:00", "end": "18:00", "holidays": ["2026-11-09", "2026-12-25"]}


def _hm(s):
    h, m = s.split(":")
    return int(h), int(m)


def add_business_minutes(start, minutes, cal, mode="business"):
    if mode == "24x7":
        return start + timedelta(minutes=minutes)
    off = timedelta(minutes=cal.get("tz_offset_minutes", 0))
    sh, sm = _hm(cal["start"])
    eh, em = _hm(cal["end"])
    cur = start + off
    remaining = float(minutes)
    for _ in range(800):
        ds = cur.replace(hour=sh, minute=sm, second=0, microsecond=0)
        de = cur.replace(hour=eh, minute=em, second=0, microsecond=0)
        if cur.weekday() not in cal["workdays"] or cur.date().isoformat() in cal.get("holidays", []) or cur >= de:
            cur = (cur + timedelta(days=1)).replace(hour=sh, minute=sm, second=0, microsecond=0)
            continue
        if cur < ds:
            cur = ds
        avail = (de - cur).total_seconds() / 60
        if remaining <= avail:
            return cur + timedelta(minutes=remaining) - off
        remaining -= avail
        cur = (cur + timedelta(days=1)).replace(hour=sh, minute=sm, second=0, microsecond=0)
    return cur - off


async def policy_for(rec, milestone):
    pol = await get_config("sla_policies", DEFAULT_SLA) or DEFAULT_SLA
    tp = pol.get(rec["type"]) or {}
    pr = (rec.get("priority") or "P3")[:2]
    row = tp.get(pr) or tp.get("P3") or {}
    if milestone not in row:
        return None, None
    return row[milestone], row.get("calendar", "business")


def summarize(clocks):
    running = [c for c in clocks if c["state"] in ("running", "paused")]
    breached = any(c["state"] == "breached" for c in clocks) or any(c.get("breached_at") for c in running)
    if not running:
        return None, "breached" if breached else "none"
    nxt = min(running, key=lambda c: c["due"])
    st = "breached" if breached else ("warning" if any(c.get("warned") for c in running) else "on_track")
    return nxt["due"], st


async def _save(rec_id, clocks, coll=None):
    due, st = summarize(clocks)
    await (coll or db.records).update_one({"id": rec_id}, {"$set": {"sla": clocks, "sla_due": due, "sla_state": st}})


async def start(rec, milestone):
    minutes, mode = await policy_for(rec, milestone)
    if minutes is None:
        return
    cal = await get_config("business_calendar", DEFAULT_CALENDAR) or DEFAULT_CALENDAR
    fresh = await db.records.find_one({"id": rec["id"]}, {"_id": 0, "sla": 1}) or {}
    clocks = [c for c in fresh.get("sla", []) if not (c["m"] == milestone and c["state"] in ("running", "paused"))]
    st = now()
    clocks.append({"id": new_id("clk"), "m": milestone, "minutes": minutes, "calendar": mode, "start": iso(st),
                   "due": iso(add_business_minutes(st, minutes, cal, mode)), "state": "running", "warned": False,
                   "paused_at": None, "paused_minutes": 0, "history": [{"at": iso(st), "event": "started"}]})
    await _save(rec["id"], clocks)


async def _mutate(rec_id, fn):
    rec = await db.records.find_one({"id": rec_id}, {"_id": 0, "sla": 1})
    if not rec or not rec.get("sla"):
        return
    clocks = rec["sla"]
    changed = False
    for c in clocks:
        changed = fn(c) or changed
    if changed:
        await _save(rec_id, clocks)


async def meet(rec_id, milestone):
    def fn(c):
        if c["m"] == milestone and c["state"] in ("running", "paused"):
            c["state"] = "breached_met" if c.get("breached_at") else "met"
            c["met_at"] = iso()
            c["history"].append({"at": iso(), "event": "met"})
            return True
    await _mutate(rec_id, fn)


async def stop_all(rec_id):
    def fn(c):
        if c["state"] in ("running", "paused"):
            c["state"] = "stopped"
            c["history"].append({"at": iso(), "event": "stopped on closure"})
            return True
    await _mutate(rec_id, fn)


async def pause_all(rec_id, reason):
    def fn(c):
        if c["state"] == "running":
            c["state"] = "paused"
            c["paused_at"] = iso()
            c["history"].append({"at": iso(), "event": f"paused: {reason}"})
            return True
    await _mutate(rec_id, fn)


async def resume_all(rec_id):
    def fn(c):
        if c["state"] == "paused":
            mins = (now() - parse_dt(c["paused_at"])).total_seconds() / 60
            c["paused_minutes"] = c.get("paused_minutes", 0) + mins
            c["due"] = iso(parse_dt(c["due"]) + timedelta(minutes=mins))
            c["state"] = "running"
            c["paused_at"] = None
            c["history"].append({"at": iso(), "event": f"resumed after {int(mins)} min approved pause"})
            return True
    await _mutate(rec_id, fn)


async def age(rec_id, minutes):
    """DEV ONLY: shift running clocks earlier to simulate elapsed time."""
    def fn(c):
        if c["state"] in ("running", "paused"):
            c["start"] = iso(parse_dt(c["start"]) - timedelta(minutes=minutes))
            c["due"] = iso(parse_dt(c["due"]) - timedelta(minutes=minutes))
            c["history"].append({"at": iso(), "event": f"DEV time simulation -{minutes} min"})
            return True
    await _mutate(rec_id, fn)


async def tick():
    """Generate SLA warnings and breaches; breaches raise an escalation for the regional manager."""
    import engine
    import notify
    pol = await get_config("sla_policies", DEFAULT_SLA) or DEFAULT_SLA
    ratio = pol.get("warn_ratio", 0.8)
    t = now()
    cursor = db.records.find({"sla": {"$elemMatch": {"state": "running"}}}, {"_id": 0})
    async for rec in cursor:
        clocks = rec["sla"]
        changed = False
        for c in clocks:
            if c["state"] != "running":
                continue
            s, d = parse_dt(c["start"]), parse_dt(c["due"])
            total = max((d - s).total_seconds(), 1)
            if t >= d and not c.get("breached_at"):
                c["breached_at"] = iso(t)
                c["history"].append({"at": iso(t), "event": "breached"})
                changed = True
                await engine.log_event(rec, None, "sla_breach", f"SLA breached: {c['m'].replace('_', ' ')}", None, None)
                await notify.to_users([rec.get("owner_id")], f"SLA breached on {rec['ref']}", f"{c['m'].replace('_', ' ').title()} milestone breached.", rec, "urgent")
                await engine.sla_breach_escalation(rec, c)
            elif not c.get("warned") and (t - s).total_seconds() / total >= ratio:
                c["warned"] = True
                c["history"].append({"at": iso(t), "event": "warning issued"})
                changed = True
                await engine.log_event(rec, None, "sla_warning", f"SLA warning: {c['m'].replace('_', ' ')} approaching breach", None, None)
                await notify.to_users([rec.get("owner_id") or rec.get("proposed_owner_id")], f"SLA warning on {rec['ref']}", f"{c['m'].replace('_', ' ').title()} due {c['due'][:16]}", rec, "pending")
        if changed:
            await _save(rec["id"], clocks)
