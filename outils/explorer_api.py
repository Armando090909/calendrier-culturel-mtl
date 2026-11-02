"""Essai des API à clé (Tidal, YouTube, Last.fm) depuis GitHub : extraits des réponses dans outils/diag/api.json.
Aucune clé ni jeton n'est écrit dans le résultat."""
import json
import os
import sys
from datetime import date
from pathlib import Path

import requests

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "collecteur"))
out = {}


def court(x, n=3000):
    return json.dumps(x, ensure_ascii=False)[:n]


# Tidal
try:
    cid, sec = os.environ.get("TIDAL_CLIENT_ID"), os.environ.get("TIDAL_CLIENT_SECRET")
    t = requests.post("https://auth.tidal.com/v1/oauth2/token", data={"grant_type": "client_credentials"}, auth=(cid, sec), timeout=30)
    out["tidal_jeton"] = {"statut": t.status_code, "champs": sorted(t.json().keys()) if t.ok else t.text[:300]}
    if t.ok:
        h = {"Authorization": "Bearer " + t.json()["access_token"], "accept": "application/vnd.api+json"}
        q = requests.utils.quote("Les Louanges", safe="")
        for i, (chemin, params) in enumerate([
                (f"/v2/searchResults/{q}/relationships/artists", {"countryCode": "CA", "include": "artists"}),
                (f"/v2/searchResults/{q}", {"countryCode": "CA", "include": "artists", "explicitFilter": "include"}),
                ("/v2/searchResults", {"query": "Les Louanges", "countryCode": "CA", "include": "artists"}),
                (f"/v2/searchresults/{q}/relationships/topHits", {"countryCode": "CA", "include": "topHits"})]):
            r = requests.get("https://openapi.tidal.com" + chemin, params=params, headers=h, timeout=30)
            out[f"tidal_variante_{i}"] = {"chemin": chemin, "statut": r.status_code, "extrait": court(r.json() if r.ok else r.text, 2500)}
        for nom in ():
            r = requests.get(f"https://openapi.tidal.com/v2/searchResults/{requests.utils.quote(nom)}",
                             params={"countryCode": "CA", "include": "artists"}, headers=h, timeout=30)
            out[f"tidal_recherche_{nom}"] = {"statut": r.status_code, "extrait": court(r.json() if r.ok else r.text)}
            if r.ok:
                arts = [x for x in r.json().get("included", []) if x.get("type") == "artists"]
                if arts:
                    aid = arts[0]["id"]
                    a = requests.get(f"https://openapi.tidal.com/v2/artists/{aid}", headers=h, timeout=30,
                                     params={"countryCode": "CA", "include": "albums"})
                    out[f"tidal_artiste_{nom}"] = {"statut": a.status_code, "extrait": court(a.json() if a.ok else a.text, 5000)}
except Exception as exc:
    out["tidal_erreur"] = str(exc)[:300]

# YouTube
try:
    raise RuntimeError("déjà essayé")
    import decouverte as d
    get_json = lambda u: requests.get(u, timeout=30).json()  # noqa: E731
    for titre in ("Mille secrets, mille dangers", "Au nord des hommes", "Paradis"):
        out[f"youtube_{titre}"] = d.bande_annonce_youtube(titre, date.today().year, get_json, {}, date.today())
    r = requests.get("https://www.googleapis.com/youtube/v3/search", timeout=30, params={
        "part": "snippet", "type": "video", "maxResults": 10, "regionCode": "CA",
        "q": "Mille secrets, mille dangers bande-annonce trailer", "key": os.environ.get("YOUTUBE_API_KEY", "")})
    out["youtube_brut"] = {"statut": r.status_code, "titres": [(i["snippet"]["title"], i["snippet"]["channelTitle"])
                                                              for i in r.json().get("items", [])] if r.ok else r.text[:300]}
except Exception as exc:
    out["youtube_erreur"] = str(exc)[:300]

# Last.fm
try:
    import decouverte as d
    get_json = lambda u: requests.get(u, timeout=30).json()  # noqa: E731
    for nom in ("Rabaska", "Les Louanges", "Lewis Lines"):
        out[f"lastfm_{nom}"] = d.fiche_lastfm(nom, get_json)
except Exception as exc:
    out["lastfm_erreur"] = str(exc)[:300]

(RACINE / "outils" / "diag" / "api.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(court(out, 2000))
