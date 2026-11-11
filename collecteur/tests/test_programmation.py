import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import connecteurs  # noqa: E402


class Programmation(unittest.TestCase):
    def test_saison_en_cours_preferee(self):
        html = ('<a href="/saison/saison-2025-2026">Saison 2025-2026</a><a href="/saison/saison-2026-2027">Saison 2026-2027</a>'
                '<a href="/abonnements">Abonnements</a><a href="/spectacle/a/b">Un spectacle</a>'
                '<a href="https://facebook.com/x">Programmation FB</a><a href="/calendrier/">Calendrier</a>')
        p = connecteurs.pages_programmation(html, "https://usine-c.com/", date(2026, 11, 10))
        self.assertEqual(p[0], "https://usine-c.com/saison/saison-2026-2027")
        self.assertIn("https://usine-c.com/calendrier/", p)
        self.assertNotIn("https://usine-c.com/saison/saison-2025-2026", p)
        self.assertFalse(any("abonn" in x or "facebook" in x for x in p))

    def test_printemps(self):  # en mars 2027, la saison en cours est encore 2026-2027
        html = '<a href="/saisons/2026-2027/">Saison</a><a href="/saisons/2025-2026/">Archives</a>'
        p = connecteurs.pages_programmation(html, "https://theatrelalicorne.com/", date(2027, 3, 1))
        self.assertEqual(p, ["https://theatrelalicorne.com/saisons/2026-2027/"])


if __name__ == "__main__":
    unittest.main()
