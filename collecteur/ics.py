"""Lecteur minimal de calendriers iCal (.ics), sans dépendance externe.

Gère : lignes repliées, DTSTART/DTEND avec TZID, en UTC (Z), en date seule (VALUE=DATE),
SUMMARY, LOCATION, URL, DESCRIPTION, STATUS. Les règles de répétition (RRULE) simples
FREQ=WEEKLY/DAILY avec COUNT ou UNTIL sont développées sur la fenêtre demandée.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

MTL = ZoneInfo("America/Toronto")


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _unescape(v: str) -> str:
    return (v.replace("\\n", "\n").replace("\\N", "\n").replace("\\,", ",")
             .replace("\\;", ";").replace("\\\\", "\\")).strip()


def _parse_prop(line: str) -> tuple[str, dict[str, str], str]:
    # NAME;PARAM=val;PARAM2=val:VALUE   (les deux-points dans une valeur entre guillemets sont ignorés)
    m = re.match(r'^([A-Za-z0-9-]+)((?:;[^:;"]+=(?:"[^"]*"|[^:;]*))*):(.*)$', line)
    if not m:
        return "", {}, ""
    name, params_raw, value = m.group(1).upper(), m.group(2), m.group(3)
    params = {}
    for p in re.findall(r';([^=;]+)=("[^"]*"|[^;]*)', params_raw):
        params[p[0].upper()] = p[1].strip('"')
    return name, params, value


def _parse_dt(value: str, params: dict[str, str]) -> tuple[datetime | date | None, bool]:
    """Renvoie (valeur, journée_entière). Les heures sont converties à l'heure de Montréal."""
    value = value.strip()
    try:
        if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", value):
            return datetime.strptime(value[:8], "%Y%m%d").date(), True
        if value.endswith("Z"):
            dt = datetime.strptime(value[:15], "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
            return dt.astimezone(MTL), False
        dt = datetime.strptime(value[:15], "%Y%m%dT%H%M%S")
        tz = params.get("TZID")
        if tz:
            try:
                dt = dt.replace(tzinfo=ZoneInfo(tz)).astimezone(MTL)
            except Exception:
                dt = dt.replace(tzinfo=MTL)  # fuseau inconnu : on suppose Montréal
        else:
            dt = dt.replace(tzinfo=MTL)  # heure « flottante »
        return dt, False
    except ValueError:
        return None, False


def parse_ics(text: str, debut: date, fin: date) -> list[dict]:
    """Événements dont la date tombe entre debut et fin (inclus).

    Chaque événement : titre, debut (datetime|date), fin (datetime|date|None), journee, lieu, url,
    description, annule.
    """
    out: list[dict] = []
    cur: dict | None = None
    for line in _unfold(text):
        if line.strip().upper() == "BEGIN:VEVENT":
            cur = {}
            continue
        if line.strip().upper() == "END:VEVENT":
            if cur is not None:
                out.extend(_expand(cur, debut, fin))
            cur = None
            continue
        if cur is None:
            continue
        name, params, value = _parse_prop(line)
        if name in ("DTSTART", "DTEND"):
            v, allday = _parse_dt(value, params)
            cur[name] = v
            if name == "DTSTART":
                cur["journee"] = allday
        elif name in ("SUMMARY", "LOCATION", "URL", "DESCRIPTION", "STATUS", "RRULE", "UID"):
            cur[name] = _unescape(value) if name != "RRULE" else value
    return out


def _day(v) -> date:
    return v.date() if isinstance(v, datetime) else v


def _expand(ev: dict, debut: date, fin: date) -> list[dict]:
    start = ev.get("DTSTART")
    if start is None or not ev.get("SUMMARY"):
        return []
    end = ev.get("DTEND")
    base = {
        "titre": ev.get("SUMMARY", ""),
        "lieu": ev.get("LOCATION", ""),
        "url": ev.get("URL", ""),
        "description": ev.get("DESCRIPTION", ""),
        "journee": bool(ev.get("journee")),
        "annule": ev.get("STATUS", "").upper() == "CANCELLED",
        "uid": ev.get("UID", ""),
    }
    starts = [start]
    rrule = ev.get("RRULE")
    if rrule:
        rule = dict(p.split("=", 1) for p in rrule.split(";") if "=" in p)
        step = {"DAILY": 1, "WEEKLY": 7}.get(rule.get("FREQ", "").upper())
        if step:
            step *= int(rule.get("INTERVAL", "1") or 1)
            count = int(rule.get("COUNT", "0") or 0) or 400
            until = None
            if "UNTIL" in rule:
                u, _ = _parse_dt(rule["UNTIL"], {})
                until = _day(u) if u else None
            starts = []
            cur = start
            for _ in range(count):
                if until and _day(cur) > until:
                    break
                if _day(cur) > fin:
                    break
                starts.append(cur)
                cur = cur + timedelta(days=step)
    duree = (end - start) if (end is not None and type(end) is type(start)) else None
    out = []
    for s in starts:
        e = (s + duree) if duree is not None else None
        last = _day(e) if e is not None else _day(s)
        if base["journee"] and e is not None:
            last = last - timedelta(days=1)  # DTEND exclusif pour les journées entières
        if _day(s) <= fin and last >= debut:
            out.append(dict(base, debut=s, fin=e))
    return out
