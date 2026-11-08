"""Rapport hebdomadaire des visites de ccmtl.ca (GoatCounter), envoyé comme avis GitHub chaque lundi matin.
La semaine finie (lundi à dimanche) comparée à la précédente : visites, pages et événements les plus vus, provenance,
pays, appareils. Clé de lecture : secret GitHub GOATCOUNTER_JETON (permission « lire les statistiques » seulement).
Lancé par .github/workflows/statistiques.yml ; sans clé, le rapport explique quoi faire au lieu d'échouer."""
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta

SITE = os.environ.get("GOATCOUNTER_SITE", "https://ccmtl.goatcounter.com")
JETON = os.environ.get("GOATCOUNTER_JETON", "").strip()
DEPOT = os.environ.get("GITHUB_REPOSITORY", "Armando090909/calendrier-culturel-mtl")


def api(chemin, **params):
    url = f"{SITE}/api/v0/{chemin}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {JETON}", "Content-Type": "application/json",
                                               "User-Agent": "ccmtl.ca-statistiques"})
    for essai in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and essai < 3:  # limite de requêtes : on patiente
                time.sleep(5 * (essai + 1))
                continue
            print(f"GoatCounter {chemin} : {exc.code} {exc.read()[:300]!r}")
            raise
    return {}


def periode(lundi):
    return {"start": f"{lundi.isoformat()}T00:00:00Z", "end": f"{(lundi + timedelta(days=7)).isoformat()}T00:00:00Z"}


def total(p):
    d = api("stats/total", **p)
    return int(d.get("total") or d.get("total_utc") or 0)


def pages(p, limite=15):
    d = api("stats/hits", limit=limite, **p)
    out = []
    for h in d.get("hits") or []:
        if h.get("event"):
            continue
        out.append((h.get("path") or "", h.get("title") or "", int(h.get("count") or 0)))
    return out


def liste(nom, p, limite=8):
    d = api(f"stats/{nom}", limit=limite, **p)
    noms = {"ig": "Instagram", "l.instagram.com": "Instagram", "instagram.com": "Instagram", "www.instagram.com": "Instagram",
            "www.facebook.com": "Facebook", "m.facebook.com": "Facebook", "l.facebook.com": "Facebook", "lm.facebook.com": "Facebook",
            "facebook.com": "Facebook", "www.google.com": "Google", "google.com": "Google", "bsky.app": "Bluesky",
            "www.threads.net": "Threads", "threads.net": "Threads", "l.threads.com": "Threads", "": "(direct ou inconnu)"}
    out = {}
    for x in d.get("stats") or []:
        n = noms.get((x.get("name") or "").lower(), x.get("name"))
        out[n] = out.get(n, 0) + int(x.get("count") or 0)
    return sorted(out.items(), key=lambda kv: -kv[1])


def ecart(n, avant):
    if not avant:
        return ""
    v = round(100 * (n - avant) / avant)
    return f" ({'+' if v >= 0 else ''}{v} % par rapport à la semaine d'avant)"


def libelle(chemin, titre):
    if chemin.startswith(("/e/", "/en/e/")):
        return f"Événement : {titre.split(' · ')[0] or chemin}"
    c = chemin.split("?")[0].removesuffix("index.html").rstrip("/") or "/"
    if c in ("/", "/en"):
        return "Accueil" + (" (anglais)" if c == "/en" else "")
    return titre.split(" · ")[0] or chemin


def rapport(lundi):
    p, p0 = periode(lundi), periode(lundi - timedelta(days=7))
    n, n0 = total(p), total(p0)
    dim = lundi + timedelta(days=6)
    L = [f"## Visites de ccmtl.ca du {lundi.day} au {dim.day} {MOIS[dim.month]}", "",
         f"**{n} visites**{ecart(n, n0)}.", ""]
    pg = pages(p)
    if pg:
        L += ["### Pages les plus vues", "", "| Page | Visites |", "|---|---|"]
        L += [f"| {libelle(c, t)} | {k} |" for c, t, k in pg[:10]]
        ev = [(c, t, k) for c, t, k in pages(p, 100) if "/e/" in c][:5]
        if ev:
            L += ["", "### Événements les plus consultés", ""] + [f"1. {libelle(c, t)[12:]} : {k}" for c, t, k in ev]
        L.append("")
    for nom, titre in (("toprefs", "D'où viennent les visiteurs"), ("locations", "Pays"), ("systems", "Appareils")):
        try:
            x = liste(nom, p)
        except Exception as exc:  # une section indisponible n'empêche pas le reste du rapport
            print(f"{nom} : {exc}")
            continue
        if x:
            L += [f"### {titre}", ""] + [f"- {a} : {b}" for a, b in x] + [""]
    L += ["---", f"Détails : {SITE}"]
    return "\n".join(L)


MOIS = ["", "janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre",
        "décembre"]


def main():
    lundi = date.today() - timedelta(days=date.today().weekday() + 7)  # la semaine finie (lundi à dimanche)
    if len(sys.argv) > 1:
        lundi = date.fromisoformat(sys.argv[1])
    if not JETON:
        corps = ("La clé de lecture GoatCounter manque : ajoutez le secret GOATCOUNTER_JETON dans GitHub "
                 "(Settings → Secrets and variables → Actions). Le rapport partira dès le lundi suivant.")
        print(corps)
        return
    if os.environ.get("ESSAI") == "1":  # essai : vérifier la clé et le site d'abord
        try:
            print("compte :", json.dumps(api("me"))[:300])
        except Exception as exc:
            print("me :", exc)
    corps = rapport(lundi)
    print(corps)
    if os.environ.get("ESSAI") == "1":
        return
    titre = f"Statistiques de la semaine du {lundi.isoformat()}"
    r = subprocess.run(["gh", "issue", "create", "--repo", DEPOT, "--title", titre, "--label", "statistiques",
                        "--body-file", "-"], input=corps, capture_output=True, text=True)
    if r.returncode and "label" in r.stderr:  # première fois : l'étiquette n'existe pas encore
        subprocess.run(["gh", "label", "create", "statistiques", "--repo", DEPOT, "--color", "3A75F0"], capture_output=True)
        r = subprocess.run(["gh", "issue", "create", "--repo", DEPOT, "--title", titre, "--label", "statistiques",
                            "--body-file", "-"], input=corps, capture_output=True, text=True)
    print(r.stdout or r.stderr)


if __name__ == "__main__":
    main()
