#!/bin/bash
# ccmtl.ca : installe sur un Raspberry Pi (ou tout Linux) la lecture quotidienne des fiches de la Ville de Montréal
# et des pages de salles qui refusent les serveurs de GitHub. Même programme que sur le Mac.
# Utilisation (Terminal du Pi) :  curl -s https://ccmtl.ca/mac/installer_pi.sh | bash
# Désinstaller :                  crontab -l | grep -v ccmtl | crontab - ; rm -rf ~/.ccmtl
set -e
D="$HOME/.ccmtl"
mkdir -p "$D"
curl -s https://ccmtl.ca/mac/ville_mac.py -o "$D/ville_mac.py"

if [ ! -s "$D/jeton" ]; then
  echo "Collez le jeton GitHub « mac ccmtl » (il ne s'affichera pas), puis appuyez sur Entrée :"
  read -r -s JETON < /dev/tty
  printf "%s" "$JETON" > "$D/jeton"
  chmod 600 "$D/jeton"
fi

PY=$(command -v python3)
# toutes les heures ; le programme ne travaille qu'une fois par jour
# (« || true » : sans tâche existante, crontab -l et grep échouent, ce qui arrêtait le script avec set -e)
{ crontab -l 2>/dev/null | grep -v "ccmtl" || true; echo "17 * * * * nice -n 10 $PY $D/ville_mac.py >> $D/sortie.txt 2>&1 # ccmtl"; } | crontab -
crontab -l | grep -q ccmtl && echo "Tâche programmée : toutes les heures à la 17e minute." || echo "ATTENTION : la tâche programmée n'a pas pu être enregistrée."
echo ""
echo "Essai (5 fiches, rien n'est envoyé) :"
"$PY" "$D/ville_mac.py" --essai || true
echo ""
echo "C'est installé. Le Pi lira les fiches une fois par jour, en arrière-plan. Journal : ~/.ccmtl/journal.txt"
