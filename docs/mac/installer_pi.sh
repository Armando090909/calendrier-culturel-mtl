#!/bin/bash
# ccmtl.ca : installe sur un Raspberry Pi (ou tout Linux) la lecture quotidienne des fiches de la Ville de Montréal
# et des pages de salles qui refusent les serveurs de GitHub. Même programme que sur le Mac.
# Utilisation (Terminal du Pi) :  curl -s https://ccmtl.ca/mac/installer_pi.sh | bash
# Désinstaller :                  crontab -l | grep -v ccmtl | crontab - ; rm -rf ~/.ccmtl
set -e
D="$HOME/.ccmtl"
mkdir -p "$D"
curl -s https://ccmtl.ca/mac/ville_mac.py -o "$D/ville_mac.py"
curl -s https://ccmtl.ca/mac/lundi.py -o "$D/lundi.py"

if [ ! -s "$D/jeton" ]; then
  echo "Collez le jeton GitHub « mac ccmtl » (il ne s'affichera pas), puis appuyez sur Entrée :"
  read -r -s JETON < /dev/tty
  printf "%s" "$JETON" > "$D/jeton"
  chmod 600 "$D/jeton"
fi

PY=$(command -v python3)
# toutes les heures ; le programme ne travaille qu'une fois par jour
# (« || true » : sans tâche existante, crontab -l et grep échouent, ce qui arrêtait le script avec set -e)
# + chaque lundi à 8 h 30 (heure du Pi) : signal de départ de la publication de la semaine (23 nov. 2026)
{ crontab -l 2>/dev/null | grep -v "ccmtl" || true; echo "17 * * * * nice -n 10 $PY $D/ville_mac.py >> $D/sortie.txt 2>&1 # ccmtl"; echo "30 8 * * 1 $PY $D/lundi.py >> $D/sortie.txt 2>&1 # ccmtl-lundi"; } | crontab -
crontab -l | grep -q ccmtl-lundi && echo "Tâches programmées : lecture toutes les heures (17e minute), publication chaque lundi à 8 h 30." || echo "ATTENTION : la tâche programmée n'a pas pu être enregistrée."
echo ""
echo "Fuseau horaire du Pi : $(cat /etc/timezone 2>/dev/null || date +%Z)  (doit être America/Toronto pour 8 h 30 à Montréal)"
"$PY" "$D/lundi.py" --essai || true
echo "Essai (5 fiches, rien n'est envoyé) :"
"$PY" "$D/ville_mac.py" --essai || true
echo ""
echo "C'est installé. Le Pi lira les fiches une fois par jour, en arrière-plan. Journal : ~/.ccmtl/journal.txt"
