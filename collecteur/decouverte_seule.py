"""Découverte (affiches, billets, liens d'écoute) lancée à part par collecte.py, dans un processus séparé.

Pourquoi à part (12 nov. 2026) : deux assemblages de suite ont été annulés après 2 heures parce que la découverte
restait bloquée quelque part, et même un arrêt programmé à 35 minutes ne réussissait pas à l'interrompre. Un processus
séparé, lui, peut toujours être arrêté de l'extérieur ; la mémoire est enregistrée en cours de route, rien n'est perdu,
et la publication du site n'attend plus jamais la découverte au-delà du délai fixé.

Entrée : cache/_decouverte_evenements.json (les événements). Sortie : cache/_decouverte_resultat.json (nombre, journal).
"""
from __future__ import annotations

import faulthandler
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import connecteurs  # noqa: E402
import decouverte  # noqa: E402

CACHE = Path(__file__).parent / "cache"

if __name__ == "__main__":
    max_recherches, delai_min = int(sys.argv[1]), int(sys.argv[2])
    # Si ça bloque encore : la pile d'appels est écrite dans le journal 2 minutes avant l'arrêt, pour voir OÙ.
    faulthandler.dump_traceback_later(max(60, (delai_min - 2) * 60), exit=False)
    events = json.loads((CACHE / "_decouverte_evenements.json").read_text(encoding="utf-8"))
    n = decouverte.enrichir(events, date.fromisoformat(sys.argv[3]), connecteurs.telecharger, max_recherches,
                            page_rendue=connecteurs.page_rendue)
    (CACHE / "_decouverte_resultat.json").write_text(json.dumps(
        {"n": n, "catalogues": decouverte.JOURNAL_CATALOGUES[-300:]}, ensure_ascii=False), encoding="utf-8")
    print(f"Découverte : {n} concerts ou films avec des liens vérifiés.", flush=True)
