"""Un petit fichier .ics par événement, publié avec le site (docs/ics/<id>.ics).

Pourquoi : un lien vers un vrai fichier .ics en ligne (servi comme « text/calendar ») ouvre directement la fenêtre
« Ajouter au calendrier » sur iPhone, iPad et Mac, et s'ouvre dans l'agenda d'un clic sur Android et Windows.
Un fichier fabriqué dans le navigateur, lui, est seulement téléchargé.
"""
from __future__ import annotations

import hashlib
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

FUSEAU = [
    "BEGIN:VTIMEZONE", "TZID:America/Toronto",
    "BEGIN:DAYLIGHT", "TZOFFSETFROM:-0500", "TZOFFSETTO:-0400", "TZNAME:EDT", "DTSTART:19700308T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU", "END:DAYLIGHT",
    "BEGIN:STANDARD", "TZOFFSETFROM:-0400", "TZOFFSETTO:-0500", "TZNAME:EST", "DTSTART:19701101T020000",
    "RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU", "END:STANDARD", "END:VTIMEZONE",
]


def _esc(t: str) -> str:
    return str(t).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _plier(ligne: str) -> str:
    """Lignes de 75 octets au plus (règle du format iCalendar)."""
    b = ligne.encode("utf-8")
    if len(b) <= 75:
        return ligne
    morceaux, cur = [], b""
    for ch in ligne:
        c = ch.encode("utf-8")
        if len(cur) + len(c) > (75 if not morceaux else 74):
            morceaux.append(cur.decode("utf-8"))
            cur = b""
        cur += c
    morceaux.append(cur.decode("utf-8"))
    return "\r\n ".join(morceaux)


def identifiant(e: dict) -> str:
    """Nom de fichier lisible : date et titre (« 2026-11-21-mesdames-et-messieurs-brian-mulroney-3f2a91 »)."""
    import re
    import unicodedata
    t = unicodedata.normalize("NFD", e["titre"]).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:50].strip("-") or "evenement"
    h = hashlib.sha1(f"{e['date']}|{e.get('heure') or ''}|{e['titre']}|{e['lieu']}".encode()).hexdigest()[:6]
    return f"{e['date']}-{t}-{h}"


def contenu(e: dict, maintenant: datetime) -> str:
    j = date.fromisoformat(e["date"])
    if e.get("heure"):
        h, m = (int(x) for x in e["heure"].split(":"))
        debut = datetime(j.year, j.month, j.day, h, m)
        fin = debut + timedelta(hours=2)
        quand = [f"DTSTART;TZID=America/Toronto:{debut:%Y%m%dT%H%M%S}", f"DTEND;TZID=America/Toronto:{fin:%Y%m%dT%H%M%S}"]
    else:
        quand = [f"DTSTART;VALUE=DATE:{j:%Y%m%d}", f"DTEND;VALUE=DATE:{j + timedelta(days=1):%Y%m%d}"]
    descr = ("" if e.get("heure") else "Heure à confirmer. ") + (e.get("resume", "") + "\n" if e.get("resume") else "") \
        + (f"Prix : {e['prix']}\n" if e.get("prix") else "") + f"Détails : {e.get('billets') or e.get('url', '')}\n(ccmtl.ca)"
    lignes = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ccmtl.ca//Calendrier culturel//FR", "CALSCALE:GREGORIAN",
              "METHOD:PUBLISH", *FUSEAU, "BEGIN:VEVENT", f"UID:{identifiant(e)}@ccmtl.ca", f"DTSTAMP:{maintenant:%Y%m%dT%H%M%SZ}",
              *quand, f"SUMMARY:{_esc(e['titre'])}", f"LOCATION:{_esc(e['lieu'] + ', Montréal')}",
              f"URL:{e.get('url', '')}", f"DESCRIPTION:{_esc(descr)}", "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(_plier(x) for x in lignes) + "\r\n"


def publier(events: list[dict], dossier: Path) -> int:
    """Réécrit docs/ics/ et ajoute à chaque événement son identifiant (« ics »). Renvoie le nombre de fichiers."""
    if dossier.exists():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True)
    # Date fixe : un événement inchangé donne un fichier identique d'un jour à l'autre (pas de modification inutile)
    maintenant = datetime(2026, 1, 1)
    for e in events:
        e["ics"] = identifiant(e)
        (dossier / f"{e['ics']}.ics").write_bytes(contenu(e, maintenant).encode("utf-8"))
    return len(events)
