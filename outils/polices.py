"""Héberge les polices sur le site lui-même (au moment de la publication, dans GitHub Actions).

Pourquoi : certains navigateurs (Firefox Focus, bloqueurs de pub, réseaux d'entreprise) bloquent Google Fonts ;
le site s'affichait alors avec des polices de secours. Ici, on télécharge les fichiers .woff2 et on les publie
avec le site (docs/fonts/). En cas d'échec, rien ne change : le site garde le lien vers Google Fonts.
"""
import re
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOCS = RACINE / "docs"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def lire(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
        return r.read()


def main() -> int:
    index = (DOCS / "index.html").read_text(encoding="utf-8")
    m = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/css2\?[^"]+)">', index)
    if not m:
        print("Aucun lien Google Fonts : rien à faire.")
        return 0
    lien = m.group(1).replace("&amp;", "&")
    try:
        css = lire(lien).decode("utf-8")
        dossier = DOCS / "fonts"
        dossier.mkdir(exist_ok=True)
        n = 0
        for i, url in enumerate(dict.fromkeys(re.findall(r"url\((https://[^)]+\.woff2)\)", css))):
            nom = f"police-{i}.woff2"
            (dossier / nom).write_bytes(lire(url))
            css = css.replace(url, nom)
            n += 1
        if not n:
            raise RuntimeError("aucun fichier de police trouvé")
        (dossier / "polices.css").write_text(css, encoding="utf-8")
    except Exception as exc:  # le site garde Google Fonts
        print(f"Polices non hébergées ({exc}) : le site garde le lien vers Google Fonts.")
        return 0
    for page in DOCS.glob("*.html"):
        h = page.read_text(encoding="utf-8")
        h = re.sub(r'\s*<link rel="preconnect" href="https://fonts\.(googleapis|gstatic)\.com"[^>]*>', "", h)
        h = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com/css2\?[^"]+">',
                   '<link rel="stylesheet" href="fonts/polices.css">', h)
        page.write_text(h, encoding="utf-8")
    print(f"{n} fichiers de police hébergés sur le site.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
