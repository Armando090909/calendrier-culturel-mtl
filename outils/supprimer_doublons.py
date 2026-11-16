"""Supprime des publications en double (outils/reseaux/demande-suppression.json) : Bluesky (le fil entier), Facebook
(publication et story), Threads (si l'API le permet). Instagram ne permet pas d'effacer par l'API : à la main.
16 nov. 2026 : la semaine du 16 nov. est partie deux fois (9 h 27 et 9 h 30) ; on efface la 2e."""
import json
import os
import sys
from pathlib import Path

import requests

DEMANDE = Path(__file__).parent / "reseaux" / "demande-suppression.json"


def bluesky(uris):
    ident, mdp = os.environ["BLUESKY_IDENTIFIANT"], os.environ["BLUESKY_MOT_DE_PASSE"]
    did = "did:plc:gu5qsdm7glxvc2cb7vdjtxaq"
    s = None
    for i in dict.fromkeys([ident, did]):
        s = requests.post("https://bsky.social/xrpc/com.atproto.server.createSession", json={"identifier": i, "password": mdp}, timeout=30)
        if s.ok:
            break
    s.raise_for_status()
    h = {"Authorization": "Bearer " + s.json()["accessJwt"]}
    # réponses du fil (même si le premier message est déjà effacé) : nos messages dont la racine est l'un de ces fils
    lr = requests.get("https://bsky.social/xrpc/com.atproto.repo.listRecords", headers=h, timeout=30,
                      params={"repo": did, "collection": "app.bsky.feed.post", "limit": 100})
    for rec in lr.json().get("records", []) if lr.ok else []:
        racine = (((rec.get("value") or {}).get("reply") or {}).get("root") or {}).get("uri")
        if racine in uris:
            r = requests.post("https://bsky.social/xrpc/com.atproto.repo.deleteRecord", headers=h, timeout=30,
                              json={"repo": did, "collection": "app.bsky.feed.post", "rkey": rec["uri"].rsplit("/", 1)[-1]})
            print(f"bluesky réponse {rec['uri']} : {'effacé' if r.ok else r.text[:200]}")
    for uri in uris:
        # le fil entier (le premier message et ses réponses), seulement nos propres messages
        t = requests.get("https://bsky.social/xrpc/app.bsky.feed.getPostThread", headers=h, params={"uri": uri, "depth": 20}, timeout=30)
        a_effacer = []
        def parcourir(n):
            p = (n or {}).get("post") or {}
            if p.get("uri", "").startswith(f"at://{did}/"):
                a_effacer.append(p["uri"])
            for r in (n or {}).get("replies") or []:
                parcourir(r)
        if t.ok:
            parcourir(t.json().get("thread"))
        for u in reversed(a_effacer or [uri]):
            rkey = u.rsplit("/", 1)[-1]
            r = requests.post("https://bsky.social/xrpc/com.atproto.repo.deleteRecord", headers=h, timeout=30,
                              json={"repo": did, "collection": "app.bsky.feed.post", "rkey": rkey})
            print(f"bluesky {u} : {'effacé' if r.ok else r.text[:200]}")


def facebook(ids):
    jeton, page = os.environ["FACEBOOK_JETON"], os.environ["FACEBOOK_PAGE_ID"]
    r = requests.get(f"https://graph.facebook.com/v26.0/{page}", params={"fields": "access_token", "access_token": jeton}, timeout=30)
    if r.ok and r.json().get("access_token"):
        jeton = r.json()["access_token"]
    for i in ids:
        r = requests.delete(f"https://graph.facebook.com/v26.0/{i}", params={"access_token": jeton}, timeout=30)
        print(f"facebook {i} : {'effacé' if r.ok else r.text[:200]}")


def threads(ids):
    jeton = os.environ["THREADS_JETON"]
    for i in ids:
        r = requests.delete(f"https://graph.threads.net/v1.0/{i}", params={"access_token": jeton}, timeout=30)
        print(f"threads {i} : {'effacé' if r.ok else r.text[:200]}")


def main():
    d = json.loads(DEMANDE.read_text(encoding="utf-8"))
    for nom, f in (("bluesky", bluesky), ("facebook", facebook), ("threads", threads)):
        if d.get(nom):
            try:
                f(d[nom])
            except Exception as exc:
                print(f"{nom} : échec ({exc})")
    if d.get("instagram"):
        print("instagram : à effacer à la main (pas permis par l'API) :", ", ".join(d["instagram"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
