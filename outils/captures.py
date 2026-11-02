"""Captures d'écran du site avec les vraies polices (lancé dans GitHub) : outils/diag/captures/."""
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "outils" / "diag" / "captures"
SORTIE.mkdir(parents=True, exist_ok=True)
serveur = subprocess.Popen(["python3", "-m", "http.server", "8765", "-d", str(RACINE / "docs")])
time.sleep(2)
VUES = [("fr-ordi", "/", 1280, 900, True), ("fr-ordi-haut", "/", 1280, 900, False), ("fr-tel", "/", 390, 844, True),
        ("en-ordi", "/en/", 1280, 900, False), ("fr-ordi-jour", "/?vue=jour", 1280, 900, False), ("salles", "/salles.html", 1280, 900, True)]
try:
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for nom, chemin, l, h, pleine in VUES:
            pg = nav.new_page(viewport={"width": l, "height": h}, device_scale_factor=2 if l < 500 else 1)
            pg.goto("http://localhost:8765" + chemin, wait_until="networkidle")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(2500)
            if nom == "fr-ordi-jour":
                pg.click("#v-day")
                pg.wait_for_timeout(1000)
                pg.click(".ev, #list a, #list button")
                pg.wait_for_timeout(1200)
            pg.screenshot(path=str(SORTIE / f"{nom}.png"), full_page=pleine)
        nav.close()
finally:
    serveur.terminate()
print(sorted(x.name for x in SORTIE.iterdir()))
