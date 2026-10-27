"""Position des salles avec OpenStreetMap (Nominatim).

Règles d'usage de Nominatim : au plus une requête par seconde, un User-Agent identifiable,
et un cache (lieux.json) pour ne jamais redemander une salle déjà connue.
"""
from __future__ import annotations

import time

import requests

from normalisation import VILLES_ILE, plat

URL = "https://nominatim.openstreetmap.org/search"
_dernier = 0.0


def localiser(requete: str, user_agent: str) -> dict | None:
    """Renvoie {lat, lon, quartier, ville} pour un lieu sur l'île de Montréal, sinon None."""
    global _dernier
    attente = 1.1 - (time.time() - _dernier)
    if attente > 0:
        time.sleep(attente)
    _dernier = time.time()
    try:
        r = requests.get(URL, params={
            "q": requete, "format": "jsonv2", "addressdetails": 1, "limit": 1, "countrycodes": "ca",
            "viewbox": "-73.98,45.71,-73.47,45.40", "bounded": 1,
        }, headers={"User-Agent": user_agent, "Accept-Language": "fr"}, timeout=20)
        r.raise_for_status()
        res = r.json()
    except Exception as exc:  # réseau ou quota : on réessaiera au prochain passage
        print(f"  [géo] échec pour « {requete} » : {exc}")
        return None
    if not res:
        return None
    a = res[0].get("address", {})
    ville = a.get("city") or a.get("town") or a.get("village") or a.get("municipality") or ""
    if ville and not any(plat(ville).startswith(v) or v in plat(ville) for v in VILLES_ILE):
        return {"hors_ile": True, "ville": ville}
    quartier = a.get("suburb") or a.get("neighbourhood") or a.get("city_district") or ""
    return {"lat": round(float(res[0]["lat"]), 5), "lon": round(float(res[0]["lon"]), 5), "quartier": quartier}
