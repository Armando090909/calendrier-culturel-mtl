"""Publications à épingler en haut d'Instagram (et Facebook) : 3 carrousels qui présentent ccmtl.
1. Qui on est (mission) ; 2. Mode d'emploi du site ; 3. Fais passer le mot (partage et don).
Même style que les publications de la semaine (fond crème, Figtree, couleurs du logo), avec des morceaux du dessin
du logo (docs/logos/morceaux/) qui dépassent des bords. Sortie : outils/reseaux/epingles/{fr,en}/.
Rendu par .github/workflows/apercu-reseaux.yml (les polices viennent de Google Fonts)."""
import base64
import sys
from html import escape
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "outils"))
sys.path.insert(0, str(RACINE / "collecteur"))
import faits_saillants as fs  # noqa: E402

MORCEAUX = RACINE / "docs" / "logos" / "morceaux"
SORTIE = RACINE / "outils" / "reseaux" / "epingles"
C = fs.COUL2
T = fs.T


def m(n):
    f = MORCEAUX / f"m{n}.png"
    return "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else ""


# Morceaux du dessin : 1 spirale, 2 bouche rose, 3 orange « ccmtl », 4 vert, 5 jaune, 6 goutte, 7 point orange, 8 bulle bleue
def deco(*places):
    """places : (morceau, css de position) ; les morceaux sont posés derrière le texte et dépassent des bords."""
    return "".join(f'<img class="mx" src="{m(n)}" style="{css}" alt="">' for n, css in places)


CSS = """
body{position:relative}
.mx{position:absolute;z-index:0;pointer-events:none}
.z{position:relative;z-index:1;display:flex;flex-direction:column;gap:40px;flex:1;min-height:0}
.k{font-size:30px;font-weight:900;letter-spacing:.06em;text-transform:uppercase}
h1{margin:0;font-size:150px;line-height:.9;font-weight:900;letter-spacing:-.055em}
h2{margin:0;font-size:108px;line-height:.92;font-weight:900;letter-spacing:-.05em}
p{margin:0;font-size:44px;line-height:1.28;font-weight:500;max-width:900px}
p b{font-weight:900}
.pills{display:flex;flex-wrap:wrap;gap:14px}
.pl{font-size:38px;font-weight:900;border-radius:999px;padding:12px 28px;color:#000}
.pl.o{border:3px solid #000}
.liste{display:flex;flex-direction:column;gap:18px}
.li{display:flex;gap:22px;align-items:flex-start;font-size:42px;line-height:1.25;font-weight:500}
.li i{flex:none;width:30px;height:30px;border-radius:50%;margin-top:9px}
.li b{font-weight:900}
.carte{background:var(--c);border-radius:26px;padding:22px 28px;display:flex;flex-direction:column;gap:4px;max-width:760px}
.carte .h{display:flex;justify-content:space-between;align-items:baseline}
.carte .d{font-size:26px;font-weight:700}.carte .t2{font-size:46px;font-weight:900;line-height:1}
.carte .t{font-size:40px;font-weight:900;line-height:1.05}.carte .l{font-size:28px;font-weight:500}
.bt{font-size:34px;font-weight:700;border:3px solid #000;border-radius:999px;padding:10px 24px;background:transparent}
.bt.n{background:#000;color:#F5EFE3}
.jours{display:flex;gap:12px}
.jr{width:118px;border:3px solid #000;border-radius:20px;display:flex;flex-direction:column;align-items:center;padding:10px 0 12px}
.jr span{font-size:24px;font-weight:700}.jr b{font-size:56px;font-weight:900;line-height:1}
.jr.on{background:#000;color:#F5EFE3}
.rond{width:420px;height:420px;display:block}
"""


def page(corps, n, tot, decor=""):
    return fs.page2(1080, 1350, f"""{decor}<div class="z">{corps}</div>{fs.pied(f"{n} / {tot}" if tot > 1 else "")}""", CSS)


def avatar(taille=420):
    f = RACINE / "docs" / "logos" / "avatar.png"
    src = "data:image/png;base64," + base64.b64encode(f.read_bytes()).decode() if f.exists() else ""
    return f'<img class="rond" src="{src}" style="width:{taille}px;height:{taille}px" alt="ccmtl">'


# ---------------------------------------------------------------- 1. Qui on est
def qui():
    tot = 4
    s1 = page(f"""{fs.marque2()}
<div style="display:flex;justify-content:center;margin:auto 0 0">{avatar(380)}</div>
{T('<h1>C’est quoi,<br><span class="ov">ccmtl</span>&nbsp;?</h1>', '<h1>What is<br><span class="ov">ccmtl</span>?</h1>')}
<p>{T("Le calendrier culturel de l’île de Montréal.", "Montréal’s cultural calendar, for the whole island.")}</p>""", 1, tot,
              deco((6, "left:110px;top:230px;width:70px"), (1, "right:120px;top:210px;width:110px")))
    s2 = page(f"""<span class="k">{T("Qui on est", "Who we are")}</span>
<h2>{T('Tout ce qui se passe sur l’île, <span class="ov">au même endroit</span>.', 'Everything happening on the island, <span class="ov">in one place</span>.')}</h2>
<p>{T("Théâtre, concerts, danse, humour, cinéma, poésie, expos, conférences, sorties pour les enfants… Près de 3 000 sorties à venir, des grandes salles aux bars de quartier.",
      "Theatre, concerts, dance, comedy, film, poetry, exhibitions, talks, kids’ outings… Nearly 3,000 upcoming events, from big halls to neighbourhood bars.")}</p>
<div class="pills"><span class="pl" style="background:{C['jeune']}">{T("Gratuit", "Free")}</span><span class="pl" style="background:{C['danse']}">{T("Sans pub", "No ads")}</span>
<span class="pl" style="background:{C['fete']}">{T("Bénévole", "Volunteer-run")}</span><span class="pl" style="background:{C['cinema']}">{T("Indépendant", "Independent")}</span>
<span class="pl o">{T("Sans compte à créer", "No account needed")}</span></div>""", 2, tot,
              deco((4, "right:72px;bottom:135px;width:245px"), (7, "left:80px;bottom:190px;width:70px")))
    s3 = page(f"""<span class="k">{T("Notre mission", "Our mission")}</span>
<h2>{T('Mieux connecter les artistes et <span class="ov">leur public</span>.', 'Connecting artists with <span class="ov">their audience</span>.')}</h2>
<div class="liste">
<div class="li"><i style="background:{C['musique']}"></i><span>{T("<b>Chaque matin</b>, on relit automatiquement plus de 200 agendas : salles, festivals, bibliothèques, maisons de la culture.",
  "<b>Every morning</b>, we automatically read over 200 listings: venues, festivals, libraries, community arts centres.")}</span></div>
<div class="li"><i style="background:{C['theatre']}"></i><span>{T("<b>La petite salle compte autant que la grande.</b> Aucune commandite, aucune place achetée.",
  "<b>The small room counts as much as the big hall.</b> No sponsors, no paid placement.")}</span></div>
<div class="li"><i style="background:{C['conference']}"></i><span>{T("<b>On ne vend rien</b> : pas de billetterie, pas de pub. Les billets se prennent chez l’artiste ou la salle.",
  "<b>We sell nothing</b>: no ticketing, no ads. Tickets come straight from the artist or venue.")}</span></div>
</div>""", 3, tot, deco((2, "right:30px;bottom:30px;width:150px;transform:rotate(-80deg)"), (6, "left:90px;bottom:200px;width:70px")))
    s4 = page(f"""<div style="display:flex;flex-direction:column;align-items:center;gap:40px;margin:auto 0;text-align:center">
<h2 style="font-size:130px">{T('Qu’est-ce qu’on fait <span class="ov">ce soir</span>&nbsp;?', 'What’s on <span class="ov">tonight</span>?')}</h2>
<p style="margin:0 auto">{T("La réponse est sur ccmtl.ca. Lien dans la bio.", "The answer is on ccmtl.ca. Link in bio.")}</p></div>""", 4, tot,
              deco((5, "right:-110px;bottom:100px;width:250px;transform:rotate(8deg)"), (8, "left:-90px;top:-40px;width:360px"),
                   (1, "right:110px;top:110px;width:110px")))
    return [("1-qui-1", s1), ("1-qui-2", s2), ("1-qui-3", s3), ("1-qui-4", s4)]


# ---------------------------------------------------------------- 2. Mode d'emploi
def mode():
    tot = 6
    s1 = page(f"""{fs.marque2()}
<div style="margin-top:auto"></div>
{T('<h1>Mode<br>d’<span class="ov">emploi</span></h1>', '<h1>How it<br><span class="ov">works</span></h1>')}
<p>{T("Le site en 5 gestes.", "The site in 5 moves.")}</p>""", 1, tot,
              deco((3, "right:-90px;top:90px;width:430px;transform:rotate(-6deg)"), (6, "right:430px;top:330px;width:70px")))
    s2 = page(f"""<style>.z{{gap:26px}}.li{{font-size:40px !important;gap:18px}}.li i{{width:26px;height:26px;margin-top:10px}}</style><span class="k">1 · {T("Choisis ta vue", "Pick your view")}</span>
<h2 style="font-size:90px;white-space:nowrap">{T('La semaine ou <span class="ov">le jour</span>&nbsp;?', 'The week or <span class="ov">the day</span>?')}</h2>
<div class="liste">
<div class="li"><i style="background:{C['musique']}"></i><span>{T("Le mode <b>Semaine</b> te donne une vue d’ensemble : les 7 jours côte à côte, pour repérer rapidement ce qui s’en vient. Sur téléphone, tu glisses d’un jour à l’autre.",
  "<b>Week</b> view gives you the big picture: all 7 days side by side, to spot quickly what’s coming. On your phone, you swipe from one day to the next.")}</span></div>
<div class="li"><i style="background:{C['jeune']}"></i><span>{T("Le mode <b>Jour</b> montre une seule journée, avec tous les détails de chaque sortie.",
  "<b>Day</b> view shows a single day, with every detail of each event.")}</span></div>
</div>
<div class="pills" style="align-items:center"><span style="font-size:30px;font-weight:700">{T("En festival :", "Festivals on:")}</span>
<span class="pl" style="background:{C['musique']};font-size:30px;padding:8px 20px">Monde Arabe 8</span><span class="pl" style="background:{C['jeune']};font-size:30px;padding:8px 20px">La Mèche courte 25</span></div>
<div class="li"><i style="background:{C['fete']}"></i><span>{T("Les <b>festivals</b> en cours sont affichés en haut de la semaine. Touche-en un pour voir toute sa programmation.",
  "<b>Festivals</b> on now are shown at the top of the week. Tap one to see its whole program.")}</span></div>
<div class="li"><i style="background:{C['expo']}"></i><span>{T("Les <b>expositions</b> durent souvent des semaines. Plutôt que de les répéter chaque jour, on les regroupe dans une carte « expos ouvertes » au bas de chaque journée.",
  "<b>Exhibitions</b> often run for weeks. Instead of repeating them every day, they’re grouped in an “exhibitions open” card at the bottom of each day.")}</span></div>
""", 2, tot)
    cats = [("theatre", T("Théâtre", "Theatre")), ("musique", T("Musique", "Music")), ("danse", T("Danse", "Dance")),
            ("humour", T("Humour", "Comedy")), ("cinema", T("Cinéma", "Film")), ("poesie", T("Poésie", "Poetry")),
            ("jeune", T("Jeune public", "Kids")), ("fete", T("Fêtes", "Parties")), ("conference", T("Conférences", "Talks")),
            ("lettres", T("Littérature", "Literature"))]
    s3 = page(f"""<span class="k">2 · {T("Filtre", "Filter")}</span>
<h2>{T('Tout voir, ou <span class="ov">seulement</span> ce qui t’intéresse.', 'See it all, or <span class="ov">only</span> what you like.')}</h2>
<div class="pills" style="align-items:center"><span class="bt" style="display:flex;gap:30px;padding:10px 30px"><b>{T("tout", "all")}</b><b>{T("aucun", "none")}</b></span></div>
<div class="pills">{''.join(f'<span class="pl" style="background:{C[k]}">{n}</span>' for k, n in cats)}</div>
<p>{T("Tu peux choisir toutes les catégories d’un coup, ou seulement celles qui t’intéressent : touche une catégorie pour l’ajouter ou l’enlever. Tu peux aussi chercher un artiste, une salle ou un festival.",
      "You can pick all categories at once, or only the ones you like: tap a category to add or remove it. You can also search for an artist, a venue or a festival.")}</p>""", 3, tot,
              deco((1, "right:60px;top:70px;width:120px")))
    s4 = page(f"""<span class="k">3 · {T("Ouvre une sortie", "Open an event")}</span>
<h2>{T('Tout ce qu’il faut <span class="ov">savoir</span>.', 'All you need <span class="ov">to know</span>.')}</h2>
<div class="carte" style="--c:{C['musique']}"><div class="h"><span class="d">{T("Musique", "Music")}</span><span class="t2">20:00</span></div>
<span class="t">{T("Nom du spectacle", "Show title")}</span><span class="l">{T("Salle · Métro Mont-Royal", "Venue · Mont-Royal metro")}</span></div>
<div class="liste">
<div class="li"><i style="background:{C['jeune']}"></i><span>{T("Chaque sortie montre l’affiche, l’heure, la salle et <b>la station de métro la plus proche</b>.", "Each event shows the poster, time, venue and <b>the nearest metro station</b>.")}</span></div>
<div class="li"><i style="background:{C['theatre']}"></i><span>{T("Tu y trouves aussi le prix, et tu achètes <b>tes billets directement chez l’artiste ou la salle</b>.", "You also get the price, and you buy <b>tickets straight from the artist or venue</b>.")}</span></div>
<div class="li"><i style="background:{C['lettres']}"></i><span>{T("Une sortie est passée&nbsp;? Les <b>archives</b> gardent tout ce qui s’est présenté sur l’île depuis le lancement, par jour, semaine ou mois.",
  "Missed something? The <b>archives</b> keep everything that played on the island since launch, by day, week or month.")}</span></div>
</div>""", 4, tot)
    s5 = page(f"""<span class="k">4 · {T("Avant d’y aller", "Before you go")}</span>
<h2>{T('Écoute, planifie, <span class="ov">vas-y</span>.', 'Listen, plan, <span class="ov">go</span>.')}</h2>
<div class="pills"><span class="bt n">{T("Acheter des billets", "Buy tickets")}</span><span class="bt">▶ {T("Bande-annonce", "Trailer")}</span>
<span class="bt">Spotify</span><span class="bt">Apple Music</span><span class="bt">+ Google</span><span class="bt">+ Outlook</span><span class="bt">+ Apple</span>
<span class="bt">{T("Itinéraire", "Directions")}</span><span class="bt">{T("Partager", "Share")}</span></div>
<div class="liste">
<div class="li"><i style="background:{C['cinema']}"></i><span>{T("<b>Écoute</b> l’artiste ou regarde la bande-annonce directement depuis la fiche.", "<b>Listen</b> to the artist or watch the trailer right from the event.")}</span></div>
<div class="li"><i style="background:{C['musique']}"></i><span>{T("<b>Ajoute la sortie à ton agenda</b> en une touche, puis trouve l’<b>itinéraire</b> jusqu’à la salle.", "<b>Add the event to your calendar</b> in one tap, then get <b>directions</b> to the venue.")}</span></div>
</div>""", 5, tot, deco((8, "right:-140px;bottom:170px;width:360px;transform:rotate(-8deg)")))
    s6 = page(f"""<span class="k">5 · {T("Tu fais de la programmation ?", "You program events?")}</span>
<h2>{T('Ajoute tes shows, <span class="ov">c’est gratuit</span>.', 'Add your shows, <span class="ov">it’s free</span>.')}</h2>
<div class="pills"><span class="bt n">{T("Propose un événement", "Submit an event")}</span><span class="bt">{T("Partage un calendrier", "Share a calendar")}</span></div>
<p>{T("Artistes, salles, festivals : donne-nous le lien de ton agenda en ligne et on le relit chaque jour. Ou propose un événement en deux minutes, au bas du site.",
      "Artists, venues, festivals: give us your online calendar link and we read it every day. Or submit an event in two minutes, at the bottom of the site.")}</p>
<p style="font-size:34px">{T("Le site existe aussi en anglais : ccmtl.ca/en", "The site is also in French: ccmtl.ca")}</p>""", 6, tot,
              deco((2, "right:40px;bottom:30px;width:150px;transform:rotate(-80deg)"), (6, "left:80px;bottom:200px;width:70px")))
    return [("2-mode-1", s1), ("2-mode-2", s2), ("2-mode-3", s3), ("2-mode-4", s4), ("2-mode-5", s5), ("2-mode-6", s6)]


# ---------------------------------------------------------------- 3. Fais passer le mot
def partage():
    tot = 3
    s1 = page(f"""{fs.marque2()}
<div style="margin-top:auto"></div>
{T('<h1>Fais passer<br>le <span class="ov">mot</span></h1>', '<h1>Spread<br>the <span class="ov">word</span></h1>')}
<p>{T("Un calendrier, c’est utile seulement si on le connaît.", "A calendar only helps if people know about it.")}</p>""", 1, tot,
              deco((5, "right:-90px;top:90px;width:330px;transform:rotate(-10deg)"), (7, "right:380px;top:260px;width:80px")))
    s2 = page(f"""<span class="k">{T("Comment aider", "How to help")}</span>
<h2>{T('Trois façons de <span class="ov">nous aider</span>.', 'Three ways to <span class="ov">help us</span>.')}</h2>
<div class="liste">
<div class="li"><i style="background:{C['theatre']}"></i><span>{T("<b>Abonne-toi</b> et partage nos publications du lundi : la sélection de la semaine.", "<b>Follow us</b> and share our Monday posts: the week’s picks.")}</span></div>
<div class="li"><i style="background:{C['jeune']}"></i><span>{T("<b>Envoie ccmtl.ca</b> au groupe d’amis qui ne sait jamais quoi faire le samedi.", "<b>Send ccmtl.ca</b> to the group chat that never knows what to do on Saturday.")}</span></div>
<div class="li"><i style="background:{C['cinema']}"></i><span>{T("<b>Parles-en</b> à ta salle, ton band, ta troupe : leurs événements y ont leur place, gratuitement.", "<b>Tell</b> your favourite venue, band or company: their events belong here, for free.")}</span></div>
</div>""", 2, tot, deco((8, "right:-110px;bottom:120px;width:400px;transform:rotate(-8deg)"), (1, "left:70px;bottom:200px;width:100px")))
    s3 = page(f"""<span class="k">{T("Et si tu peux", "And if you can")}</span>
<h2>{T('Un don de <span class="ov">2 $</span>, ça compte.', 'A <span class="ov">$2</span> donation counts.')}</h2>
<p>{T("ccmtl est gratuit, sans pub et fait par des bénévoles. Il y a quand même des frais : les dons servent seulement à la maintenance du site.",
      "ccmtl is free, ad-free and volunteer-run. There are still some costs: donations only go to maintaining the site.")}</p>
<div class="carte" style="--c:{C['fete']};max-width:none"><span class="d" style="font-size:28px;font-weight:700">{T("Virement Interac, sans frais", "Interac e-Transfer, no fees")}</span>
<span class="t" style="font-size:54px">info@ccmtl.ca</span></div>
<p style="font-size:34px">{T("Merci ♥", "Thank you ♥")}</p>""", 3, tot,
              deco((3, "right:-90px;bottom:110px;width:340px;transform:rotate(10deg)"), (6, "left:80px;bottom:200px;width:70px")))
    return [("3-partage-1", s1), ("3-partage-2", s2), ("3-partage-3", s3)]


def main():
    for langue in ("fr", "en"):
        fs.LANGUE = langue
        dossier = SORTIE / langue
        fs.rendre(qui() + mode() + partage(), dossier)
    fs.LANGUE = "fr"


if __name__ == "__main__":
    main()
