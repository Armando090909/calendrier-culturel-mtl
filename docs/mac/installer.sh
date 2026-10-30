#!/bin/bash
# ccmtl.ca : installe sur ce Mac la lecture quotidienne des fiches de la Ville de Montréal.
# Utilisation (Terminal) :  curl -s https://ccmtl.ca/mac/installer.sh | bash
# Désinstaller :            launchctl unload ~/Library/LaunchAgents/ca.ccmtl.ville.plist; rm -rf ~/.ccmtl ~/Library/LaunchAgents/ca.ccmtl.ville.plist
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
P="$HOME/Library/LaunchAgents/ca.ccmtl.ville.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$P" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>ca.ccmtl.ville</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$D/ville_mac.py</string></array>
  <key>StartInterval</key><integer>3600</integer>
  <key>RunAtLoad</key><true/>
  <key>LowPriorityIO</key><true/>
  <key>Nice</key><integer>10</integer>
  <key>StandardOutPath</key><string>$D/sortie.txt</string>
  <key>StandardErrorPath</key><string>$D/sortie.txt</string>
</dict></plist>
EOF
launchctl unload "$P" 2>/dev/null || true
launchctl load "$P"
echo ""
echo "C'est installé. Toutes les heures où le Mac est allumé, le programme vérifie s'il a déjà travaillé aujourd'hui ;"
echo "sinon il lit les fiches de la Ville (5 à 15 minutes, en arrière-plan). Journal : ~/.ccmtl/journal.txt"
