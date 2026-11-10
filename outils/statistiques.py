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
            if exc.code in (404, 429, 502, 503) and essai < 3:  # limite de requêtes ou réponse passagère : on patiente
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


def pages(p, limite=15, actions=False):
    """Pages vues ; avec actions=True, les actions comptées dans le site (événement ouvert, festival, vue)."""
    d = api("stats/hits", limit=limite, **p)
    out = []
    for h in d.get("hits") or []:
        if bool(h.get("event")) != actions:
            continue
        out.append((h.get("path") or "", h.get("title") or "", int(h.get("count") or 0)))
    return out


VUES = {"week": "Semaine", "day": "Jour", "fest": "Festivals", "musee": "Expositions", "month": "Mois"}


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
        L.append("")
    try:
        act = pages(p, 100, actions=True)
    except Exception as exc:
        print(f"actions : {exc}")
        act = []
    # événements ouverts dans le site, plus les pages d'événement arrivées par un lien partagé ou Google
    ev = {}
    for c, t, k in act:
        if c.startswith("evenement/"):
            ev[t] = ev.get(t, 0) + k
    for c, t, k in pages(p, 100):
        if "/e/" in c:
            n = libelle(c, t)[12:]
            ev[n] = ev.get(n, 0) + k
    if ev:
        L += ["### Événements les plus consultés", ""]
        L += [f"1. {t} : {k}" for t, k in sorted(ev.items(), key=lambda kv: -kv[1])[:10]] + [""]
    fe = sorted([(t, k) for c, t, k in act if c.startswith("festival/")], key=lambda x: -x[1])[:5]
    if fe:
        L += ["### Festivals consultés", ""] + [f"- {t} : {k}" for t, k in fe] + [""]
    vu = [(VUES.get(c[4:], c[4:]), k) for c, t, k in act if c.startswith("vue/")]
    if vu:
        L += ["### Vues utilisées", ""] + [f"- {t} : {k}" for t, k in sorted(vu, key=lambda x: -x[1])] + [""]
    for nom, titre in (("toprefs", "D'où viennent les visiteurs"), ("locations", "Pays"), ("systems", "Appareils")):
        try:
            x = liste(nom, p)
        except Exception as exc:  # une section indisponible n'empêche pas le reste du rapport
            print(f"{nom} : {exc}")
            continue
        if x:
            L += [f"### {titre}", ""] + [f"- {a} : {b}" for a, b in x] + [""]
    L += exactitude(lundi)
    L += ["---", f"Détails : {SITE}"]
    return "\n".join(L)


def exactitude(lundi):
    """Section « Exactitude » : ce que les contrôles de chaque collecte ont corrigé, retiré ou signalé dans la semaine
    (collecteur/qualite.py), le contrôle aléatoire du lundi et les sources à surveiller."""
    from collections import Counter
    from pathlib import Path
    f = Path(__file__).resolve().parent.parent / "collecteur" / "cache" / "qualite_historique.json"
    try:
        h = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    jours = [(lundi + timedelta(days=i)).isoformat() for i in range(8)]  # jusqu'au lundi matin inclus
    regles, cv, exemples = Counter(), Counter(), []
    for j in jours:
        x = h.get(j) or {}
        for r in x.get("journal") or []:
            regles[(r["regle"], r["action"])] += 1
            if len(exemples) < 8 and r["regle"] not in ("date absente de la page officielle",):
                exemples.append(r)
        cv.update(x.get("contreverif") or {})
    L = ["### Exactitude", ""]
    if regles:
        L += ["| Contrôle | Action | Nombre |", "|---|---|---|"]
        L += [f"| {r} | {a} | {n} |" for (r, a), n in regles.most_common()]
        L.append("")
    else:
        L += ["Aucune correction cette semaine.", ""]
    if cv:
        t = sum(cv.values())
        L += [f"**Contre-vérification des sorties à 3 jours** : {t} vérifications — "
              + ", ".join(f"{k} : {v}" for k, v in cv.most_common()), ""]
    ctl = [v for k, v in (h.get("_controles") or {}).items() if k in jours]
    if ctl:
        c = ctl[-1]
        L += [f"**Contrôle aléatoire** : {c['exactes']} sorties exactes sur {c['verifiees']} ({c['taux']} %)."]
        for e in c.get("erreurs", [])[:6]:
            L.append(f"- {e['titre']} ({e['date']}, {e['lieu']}) : " + ", ".join(f"{k} → {v}" for k, v in e["faux"].items()))
        L.append("")
    if exemples:
        L += ["Exemples :"] + [f"- {r['regle']} : {r['titre']} ({r['date']}, {r['lieu']}) — {r['action']}" for r in exemples] + [""]
    try:
        q = json.loads((f.parent.parent.parent / "docs" / "qualite.json").read_text(encoding="utf-8"))
        if q.get("sources_a_surveiller"):
            L += ["**Sources à surveiller** (erreurs sur 28 jours) :"]
            L += [f"- {s['source']} : {s['erreurs']} erreurs sur {s['sorties']} sorties ({s['taux']} %)" for s in q["sources_a_surveiller"][:8]]
            L.append("")
    except (OSError, ValueError):
        pass
    return L


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
    # GoatCounter répond parfois « not found » aux statistiques tant que le compte n'a pas été lu : on le lit d'abord
    try:
        print("compte :", str((api("me").get("user") or {}).get("site", "?")))
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
