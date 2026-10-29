"""Ouvre un « issue » GitHub pour chaque proposition du formulaire mise de côté par le tri automatique.

GitHub envoie un courriel au propriétaire du dépôt à chaque nouvel issue : c'est l'avis.
Lancé par la collecte, après l'enregistrement. Rien n'est envoyé pour les propositions publiées.
"""
import json
import subprocess
import sys
from pathlib import Path

rapport = json.loads(Path("docs/rapport.json").read_text(encoding="utf-8"))
a_juger = [p for p in (rapport.get("notes") or {}).get("formulaire_tri", []) if p.get("nouveau") and p["decision"] == "mis de côté"]
for p in a_juger:
    corps = (f"Le tri automatique a **mis de côté** cette proposition du formulaire.\n\n"
             f"- **Titre** : {p['titre']}\n- **Date** : {p.get('date') or '?'}\n- **Lieu** : {p.get('lieu') or '?'}\n"
             f"- **Raison** : {p['raison']}\n\n"
             "**À vous de juger**, dans la feuille Google « Calendrier MTL · Événements proposés », colonne « Approuvé » :\n"
             "- `oui` : publiée à la prochaine collecte ;\n- rien ou `non` : reste de côté.\n\n"
             "Ensuite, fermez cet avis (bouton « Close issue »).")
    r = subprocess.run(["gh", "issue", "create", "--title", f"Proposition à juger : {p['titre'][:80]}", "--body", corps],
                       capture_output=True, text=True)
    print(r.stdout or r.stderr)
print(f"{len(a_juger)} avis envoyés.")
sys.exit(0)
