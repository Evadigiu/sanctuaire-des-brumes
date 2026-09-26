# -*- coding: utf-8 -*-
"""
Fabrique les pages du jeu a partir du cahier de contenu.

    python3 contenu/fabriquer-les-pages.py

Ecrase entierement le dossier etapes/. Ne jamais corriger un texte
directement dans une page : le cahier fait foi, la page est jetable.

Les libelles de borne passes a logScan() sortent de la meme source que le
SQL des bornes, donc ils ne peuvent pas diverger. C'etait tout l'interet
de passer par un tableur.
"""
import os, re, sys, unicodedata, html
from openpyxl import load_workbook

ICI    = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
CAHIER = os.path.join(ICI, "sanctuaire-cahier-de-contenu.xlsx")
SORTIE = RACINE   # chaque borne a son dossier numerique a la racine

def propre(v): return "" if v is None else str(v).strip()

def slug(t):
    d = unicodedata.normalize("NFKD", t.lower())
    d = "".join(c for c in d if not unicodedata.combining(c))
    d = re.sub(r"[^a-z0-9]+", "-", d).strip("-")
    return re.sub(r"-+", "-", d)[:40]

def code_dans(txt):
    t = propre(txt).upper().replace("-", " ").replace(":", " ")
    for mot in t.split():
        m = mot.strip(".,;")
        if m.startswith("E") and m[1:].rstrip("B").isdigit(): return m
    return None

def num_ecran(libelle):
    m = re.match(r"\s*(\d+)", propre(libelle))
    return int(m.group(1)) if m else 99

# ============================================================
# Lecture du cahier
# ============================================================
wb  = load_workbook(CAHIER, data_only=True)
par, tex = wb["Parcours"], wb["Textes"]

etapes, ordre = {}, {"A": {}, "B": {}}
for r in par.iter_rows(min_row=3, values_only=True):
    c = propre(r[0])
    if not c: continue
    etapes[c] = {"code": c, "nom": propre(r[1]), "type": propre(r[2]),
                 "lieu": propre(r[3]), "lettre": propre(r[5]),
                 "suiteA": code_dans(r[7]), "suiteB": code_dans(r[9])}
    for s, i in (("A", 6), ("B", 8)):
        v = propre(r[i])
        if v.isdigit(): ordre[s][c] = int(v)

lignes = {}
for r in tex.iter_rows(min_row=3, values_only=True):
    c = propre(r[0])
    if not c: continue
    lignes.setdefault(c, []).append({
        "sens": propre(r[2]).lower(), "ecran": propre(r[3]),
        "texte": propre(r[5]), "rem": propre(r[6]), "n": num_ecran(r[3])})

# E00 est le ticket papier remis a l'accueil, pas une page du site.
PAGES = [c for c in etapes if c != "E00"]
PAGES.sort(key=lambda c: ordre["A"].get(c, ordre["B"].get(c, 99)))
# Le nom du dossier EST le code de secours : une seule reference pour le QR
# et pour la saisie manuelle. Et surtout, une adresse qui ne raconte rien.
# "/1868/" ne dit ni ce qu'on va trouver, ni combien d'etapes il reste ;
# "/etapes/e04-indice-les-jumelles-la-carcasse.html" disait les deux, dans la
# barre d'adresse, avant meme que la page s'affiche.

TOTAL = {s: len([c for c in ordre[s] if c != "E00"]) for s in ("A", "B")}

def code_secours(cle, sel=0):
    h = 5381
    for ch in ("brumes-%d-%s" % (sel, cle)):
        h = ((h * 33) ^ ord(ch)) & 0xFFFFFFFF
    return 1000 + (h % 9000)

def trop_proche(n, deja):
    """Deux codes ne doivent jamais differer d'un seul chiffre : sinon une
    faute de frappe mene a une autre borne valide au lieu d'une erreur, et
    le joueur atterrit ailleurs sans comprendre."""
    a = "%04d" % n
    for m in deja:
        b = "%04d" % m
        if sum(1 for x, y in zip(a, b) if x != y) < 2:
            return True
    return False

secours, decales = {}, []
for c in PAGES:
    n = code_secours(c)
    if trop_proche(n, secours.values()):
        decales.append(c)
        sel = 1
        # On retire un nouveau code au hasard plutot que de decaler celui-ci :
        # un decalage regulier finirait par tasser tous les codes dans la meme
        # tranche, et des nombres qui se ressemblent se confondent sur une
        # affichette lue a la lumiere du jour.
        while trop_proche(n, secours.values()):
            n = code_secours(c, sel); sel += 1
    secours[c] = n
if decales:
    print("  (codes de secours ecartes pour eviter une confusion de frappe : %s)"
          % ", ".join(decales))

FICHIER = {c: "%d/" % secours[c] for c in PAGES}


# ============================================================
# Mecaniques particulieres, declarees explicitement plutot que
# devinees a partir du texte des remarques.
# ============================================================
EPREUVE_REPONSE = {"E08": ("11", "S")}   # etape -> (bonne reponse, lettre debloquee)
APPEL_AUDIO     = {"E12"}
# ============================================================
# LES MEDIAS (videos et audio)
#
# Les videos NE SONT PAS dans ce depot, et ne doivent pas y entrer :
# GitHub Pages est fait pour servir des pages, pas des heures de video a
# des milliers de visiteurs. Elles vivent chez un hebergeur de fichiers,
# et le jeu va les y chercher.
#
# MEDIA_BASE : l'adresse de cet hebergeur, sans le / final. C'est le SEUL
# endroit a changer le jour ou l'on change d'hebergeur.
#
# MEDIAS : le fichier de chaque borne. Une borne absente de cette liste
# garde son emplacement vide, comme avant, avec son commentaire.
#
# POSTERS : l'image fixe affichee avant que le joueur appuie sur lecture.
# Facultative, mais sans elle il voit un rectangle noir. Les posters, eux,
# sont assez legers pour vivre dans le depot (assets/img/).
# ============================================================
MEDIA_BASE = ""

# Les six caracteres au bout de chaque nom ne sont pas decoratifs. Sans eux,
# un visiteur qui lit le code source d'une seule page devine les dix autres
# adresses ("bill.mp4" donc surement "greg-sens-a.mp4") et regarde toute
# l'enquete avant de la jouer. C'est la meme precaution que les dossiers
# numeriques des bornes et les QR sans legende : le nom ne doit rien dire
# a qui ne l'a pas deja.
#
# CES NOMS FONT FOI. Le fichier depose chez l'hebergeur porte exactement
# ce nom-la, sinon la borne affiche un rectangle noir.
MEDIAS = {
 # "E01": "le-commissaire-jean-79swb7.mp4",
 "E02": "la-collegue-soigneuse-8bdz93.mp4",
 # "E03": "la-videosurveillance-yag6qs.mp4",
 # "E05": "la-passante-qri7tr.mp4",
 # "E06": "sabri-et-arez-zc9ddy.mp4",
 # "E07": "le-veterinaire-66ckyk.mp4",
 # "E09": "greg-sens-a-sj7kmm.mp4",
 "E10": "bill-t87isj.mp4",
 # "E12": "l-epouvantail-ymjcwc.mp3",
 # "E14": "la-conversion-u8tg7w.mp4",
 # "E15": "le-botaniste-rybneg.mp4",
 # "E16": "greg-sens-b-wuwfvp.mp4",
}

POSTERS = {}


NON_CONSTRUIT   = {
 "E14": "L'épreuve de conversion des 4 lettres en chiffres reste à construire.",
 "E15": "Le champ de conclusions jugé par une IA reste à construire. Il ne peut pas "
        "fonctionner tant que les tables quiz_responses et conclusions n'ont aucune "
        "règle d'accès dans Supabase : les réponses seraient rejetées en silence.",
}

def e(t): return html.escape(t, quote=True)

def bloc_ecran(etape, lg, dernier, sens_attr):
    """Un ecran = une carte. sens_attr vaut None, 'A' ou 'B'."""
    c, lib, txt = etape["code"], lg["ecran"], lg["texte"]
    est_media  = bool(re.search(r"vid[ée]o|audio", lib, re.I))
    est_sortie = "aller ensuite" in lib.lower()
    attr = ' data-sens="%s"' % sens_attr if sens_attr else ""
    h = ['<section class="ecran card"%s hidden>' % attr]
    h.append('  <div class="ecran-titre">%s</div>' % e(lib))

    if est_media:
        fichier = MEDIAS.get(c)
        poster  = POSTERS.get(c, "")
        if fichier and MEDIA_BASE:
            # preload="none" : rien ne se telecharge tant que le joueur n'a pas
            # appuye sur lecture. Sur le reseau mobile d'un parc, c'est la
            # difference entre une page qui s'ouvre et une page qui rame.
            h.append('  <video controls playsinline preload="none" poster="%s">'
                     % e(poster))
            h.append('    <source src="%s/%s" type="video/mp4">' % (MEDIA_BASE, e(fichier)))
            h.append('    <p>Votre navigateur ne lit pas cette vidéo. '
                     'Prévenez un membre de l\'équipe sur place.</p>')
            h.append('  </video>')
        else:
            h.append('  <!-- Vidéo pas encore intégrée : ajouter le fichier dans')
            h.append('       MEDIAS (contenu/fabriquer-les-pages.py) et renseigner')
            h.append('       MEDIA_BASE. Ne jamais mettre la vidéo dans le dépôt. -->')
            h.append('  <video controls playsinline poster=""><source src="" type="video/mp4">')
            h.append('  Votre navigateur ne supporte pas la vidéo.</video>')
    if c in APPEL_AUDIO and lg["n"] == 1:
        h.append('  <button id="decrocher" class="btn-appel">Décrocher</button>')
        h.append('  <div id="blocAppel" hidden>')
        h.append('    <!-- Remplacer la source par le vrai fichier audio -->')
        h.append('    <audio id="audioAppel" controls><source src="" type="audio/mpeg"></audio>')
        h.append('  </div>')

    if txt and txt != "/":
        for p in [x.strip() for x in txt.split("\n") if x.strip()]:
            h.append('  <p>%s</p>' % e(p))

    if c in EPREUVE_REPONSE and lg["n"] == 3:
        rep, lettre = EPREUVE_REPONSE[c]
        h.append('  <input type="text" id="reponse" inputmode="numeric" placeholder="Votre réponse">')
        h.append('  <button id="valider">Valider</button>')
        h.append('  <div id="resultat" class="card indice" hidden>')
        h.append('    <div class="eyebrow">Vous avez trouvé une lettre</div>')
        h.append('    <p class="lettre">%s</p>' % e(lettre))
        h.append('  </div>')
    elif etape["lettre"] and etape["lettre"] not in ("-", "/") and lg["n"] == 1 and c not in EPREUVE_REPONSE:
        h.append('  <div class="card indice">')
        h.append('    <div class="eyebrow">Vous avez trouvé une lettre</div>')
        h.append('    <p class="lettre">%s</p>' % e(etape["lettre"]))
        h.append('  </div>')

    if c in NON_CONSTRUIT and lg["n"] == 3:
        h.append('  <!-- A CONSTRUIRE : %s -->' % NON_CONSTRUIT[c])
        h.append('  <p class="a-construire">%s</p>' % e(NON_CONSTRUIT[c]))

    if est_sortie:
        h.append('  <!-- A AJOUTER : la photo qui montre où aller.')
        h.append('       <img src="../assets/img/XXX.jpg" alt="Le chemin à prendre"> -->')

    if lg["rem"]:
        h.append('  <!-- Note du cahier de contenu : %s -->' % lg["rem"].replace("--", "—"))

    if dernier:
        if lg.get("lien"):
            # Le lien n'est PAS un bouton offert au joueur : l'enquete ne doit
            # pas se derouler au clic depuis un canape. Seul le scan du QR code
            # de la borne suivante ouvre la page. etape.js ne revele ce lien
            # qu'aux codes de test, pour que l'equipe puisse repeter le
            # parcours sans courir dans le parc.
            h.append('  <p class="consigne-scan">Rendez-vous sur place, puis scannez le QR code de la borne.</p>')
            h.append('  <a href="%s" class="btn btn-test" data-lien-test hidden>Raccourci de test</a>' % e(lg["lien"]))
        else:
            h.append('  <p class="muted">Fin du parcours.</p>')
    else:
        h.append('  <button data-suivant>Suivant</button>')
        h.append('  <button class="btn-secondary" data-retour>Revenir en arrière</button>')
    h.append('</section>')
    return "\n".join(h)

GABARIT = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{titre} — Le Sanctuaire des Brumes</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mulish:wght@300;700&display=swap">
<link rel="stylesheet" href="../assets/css/style.css">
</head>
<!-- PAGE FABRIQUÉE AUTOMATIQUEMENT depuis contenu/sanctuaire-cahier-de-contenu.xlsx
     Toute correction faite ici sera perdue à la prochaine fabrication.
     Corriger le cahier, puis relancer contenu/fabriquer-les-pages.py -->
<body data-borne="{borne}" data-etape="{code}" data-racine="../">

<div class="wrap">
  <div class="timer" id="timer">Chargement du chrono...</div>
  <div class="eyebrow" id="position" data-A="{posA}" data-B="{posB}"></div>
  <h1>{titre}</h1>
{ecrans}
</div>

<div class="wrap secours-zone">
  <div class="secours-boutons">
    <button class="btn-lien" id="boutonSecours">Le QR code ne fonctionne pas</button>
    <button class="btn-lien" id="boutonProbleme">J'ai un problème</button>
  </div>

  <div class="card" id="zoneSecours" hidden>
    <p>Sur l'affichette, à côté du QR code, se trouve un nombre à quatre chiffres. Saisissez-le.</p>
    <input type="text" id="champSecours" inputmode="numeric" maxlength="4" placeholder="Ex. 4172">
    <div class="error-box visible" id="erreurSecours" hidden></div>
    <button id="validerSecours">Ouvrir cette borne</button>
  </div>

  <div class="card" id="zoneProbleme" hidden>
    <div id="formProbleme">
      <p>Dites-nous ce qui ne va pas, l'équipe est prévenue tout de suite.</p>
      <label for="categorieProbleme">De quoi s'agit-il ?</label>
      <select id="categorieProbleme">
        <option value="qr">Un QR code illisible ou décollé</option>
        <option value="decor">Un décor abîmé ou manquant</option>
        <option value="bug">Un problème sur le site</option>
        <option value="autre">Autre chose</option>
      </select>
      <label for="messageProbleme">Quelques mots (facultatif)</label>
      <textarea id="messageProbleme" rows="3" maxlength="500" placeholder="Ce que vous avez constaté"></textarea>
      <button id="envoyerProbleme">Envoyer</button>
    </div>
    <p class="muted" id="retourProbleme" hidden></p>
  </div>
</div>

<footer>
  <img class="signature" src="../assets/img/logo-pomelo.webp" alt="Pomelo Événementiel">
  Le Sanctuaire des Brumes
</footer>

<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
<script src="../assets/js/supabase-client.js"></script>
<script src="../assets/js/parcours.js"></script>
<script src="../assets/js/game.js"></script>
<script src="../assets/js/etape.js"></script>
<script>
  demarrerEtape();
{extra}</script>

</body>
</html>
"""

# On efface les anciens dossiers de bornes (repertoires purement numeriques)
# et l'ancien dossier etapes/, pour qu'aucune adresse perimee ne subsiste.
import shutil
for nom in os.listdir(SORTIE):
    chemin = os.path.join(SORTIE, nom)
    if os.path.isdir(chemin) and (nom.isdigit() or nom == "etapes"):
        shutil.rmtree(chemin)

for c in PAGES:
    et = etapes[c]
    lg = sorted(lignes.get(c, []), key=lambda x: (x["n"], x["sens"]))
    communs = [x for x in lg if x["sens"] == "les deux"]
    sorties = {s: [x for x in lg if x["sens"] == "sens " + s.lower()] for s in ("A", "B")}

    blocs = []
    for i, x in enumerate(communs):
        dernier = (i == len(communs) - 1) and not (sorties["A"] or sorties["B"])
        blocs.append(bloc_ecran(et, x, dernier, None))
    for s in ("A", "B"):
        for x in sorties[s]:
            suite = et["suite" + s]
            x = dict(x, lien=("../" + FICHIER[suite]) if suite else None)
            blocs.append(bloc_ecran(et, x, True, s))

    # Garde-fou terrain : les bornes sont physiques et un groupe peut tomber
    # sur celle de l'autre sens en se promenant. Sans cet ecran, il arriverait
    # sur une page sans aucune sortie.
    for s in ("A", "B"):
        if sorties[s]: continue
        autre = "B" if s == "A" else "A"
        prem = ordre[s].get(c)
        if prem is not None: continue          # l'etape existe dans ce sens
        blocs.append(
            '<section class="ecran card" data-sens="%s" hidden>\n'
            '  <div class="ecran-titre">Ce n\'est pas votre borne</div>\n'
            '  <p>Cette borne appartient à l\'autre parcours. La vôtre vous attend '
            'ailleurs, reprenez le chemin indiqué à l\'étape précédente.</p>\n'
            '  <p class="muted">Votre temps continue de tourner, mais rien n\'est perdu : '
            'ce détour ne compte pas dans votre enquête.</p>\n'
            '</section>' % s)

    extra = ""
    if c in EPREUVE_REPONSE:
        rep, _ = EPREUVE_REPONSE[c]
        extra += '  epreuveReponse("reponse", "valider", "%s", "resultat");\n' % rep
    if c in APPEL_AUDIO:
        extra += '  appelEntrant("decrocher", "audioAppel", "blocAppel");\n'

    posA = "Étape %d sur %d" % (ordre["A"][c], TOTAL["A"]) if c in ordre["A"] else ""
    posB = "Étape %d sur %d" % (ordre["B"][c], TOTAL["B"]) if c in ordre["B"] else ""

    page = GABARIT.format(titre=e(et["nom"]), borne=e(et["nom"]), code=c,
                          posA=e(posA), posB=e(posB),
                          ecrans="\n".join(blocs), extra=extra)
    dossier = os.path.join(SORTIE, str(secours[c]))
    os.makedirs(dossier, exist_ok=True)
    open(os.path.join(dossier, "index.html"), "w", encoding="utf-8").write(page)
    print("  /%-6s %-5s %-34s A:%-3s B:%-3s %d écran(s)" % (
        FICHIER[c], c, etapes[c]["nom"][:34], ordre["A"].get(c, "-"),
        ordre["B"].get(c, "-"), len(blocs)))

# ------------------------------------------------------------
# Le SQL des bornes, fabrique depuis la meme source que les pages.
# ------------------------------------------------------------
TYPE_SQL = {"temoin": "temoin", "témoin": "temoin", "depart": "temoin", "départ": "temoin",
            "indice": "side_quest", "lettre": "side_quest", "epreuve": "side_quest",
            "épreuve": "side_quest", "enigme": "final", "énigme": "final", "final": "final"}
sql = ["-- ============================================================",
       "-- LES BORNES DU PARCOURS",
       "-- Fabrique automatiquement depuis le cahier de contenu.",
       "-- Les libelles sont RIGOUREUSEMENT identiques a ceux que les pages",
       "-- envoient a logScan() : les deux sortent du meme fichier.",
       "--",
       "-- A coller dans Supabase : SQL Editor > New query > Run.",
       "-- ============================================================",
       "--",
       "--  /!\\  CETTE REQUETE EFFACE TOUT L'HISTORIQUE DES PASSAGES  /!\\",
       "--",
       "--  Sans danger aujourd'hui : la base ne contient que des passages de",
       "--  test. Apres le lancement du 17 octobre, ce serait la perte de toutes",
       "--  les donnees du jeu, sans retour possible.",
       "--",
       "--  Avant de lancer, verifier ce qu'on s'apprete a perdre :",
       "--      select count(*) from scans;",
       "--  Si le chiffre n'est pas proche de zero, NE PAS CONTINUER.",
       "-- ============================================================",
       "",
       "delete from scans;              -- les passages, d'abord",
       "delete from qr_points;          -- puis les anciennes bornes",
       "",
       "insert into qr_points (label, type) values"]
vals = []
for c in PAGES:
    t = TYPE_SQL.get(etapes[c]["type"].lower(), "side_quest")
    # La virgule de separation se colle au tuple, JAMAIS apres le commentaire :
    # sinon elle se retrouve dans le commentaire et le SQL devient invalide.
    vals.append(("  ('%s', '%s')" % (etapes[c]["nom"].replace("'", "''"), t),
                 "%s, %s" % (c, etapes[c]["lieu"] or "lieu a preciser")))
larg = max(len(v[0]) for v in vals)
for i, (tuple_sql, commentaire) in enumerate(vals):
    fin = ";" if i == len(vals) - 1 else ","
    sql.append("%-*s%s  -- %s" % (larg, tuple_sql, fin, commentaire))
sql.append("")
sql.append("-- Controle : doit renvoyer %d." % len(vals))
sql.append("select count(*) as bornes_enregistrees from qr_points;")
open(os.path.join(ICI, "bornes.sql"), "w", encoding="utf-8").write("\n".join(sql) + "\n")

# ------------------------------------------------------------
# Le plan du parcours, pour le navigateur.
#
# Les pages doivent savoir quelle est la position de chaque borne dans
# chaque sens, pour refuser une borne trop en avance sur la progression
# du groupe. Ce fichier sort du cahier, comme tout le reste.
#
# Le code de secours est un nombre a 4 chiffres, imprime sur l'affichette
# a cote du QR. Il est derive du code d'etape de facon stable, et
# volontairement NON sequentiel : E01 ne doit pas donner 1001 et E02 1002,
# sinon il suffirait de lire une affichette pour deviner toutes les autres
# et sauter la moitie du parcours.
# ------------------------------------------------------------
plan = {
    "pages":   {c: FICHIER[c] for c in PAGES},
    "noms":    {c: etapes[c]["nom"] for c in PAGES},
    "ordre":   {"A": {c: ordre["A"][c] for c in ordre["A"] if c != "E00"},
                "B": {c: ordre["B"][c] for c in ordre["B"] if c != "E00"}},
    "secours": {str(n): c for c, n in secours.items()},
}
import json as _json
open(os.path.join(RACINE, "assets", "js", "parcours.js"), "w", encoding="utf-8").write(
    "// ============================================================\n"
    "// LE PLAN DU PARCOURS\n"
    "// Fabrique automatiquement depuis le cahier de contenu.\n"
    "// Ne pas modifier a la main : relancer fabriquer-les-pages.py.\n"
    "// ============================================================\n"
    "const PARCOURS = " + _json.dumps(plan, ensure_ascii=False, indent=2) + ";\n")

# ------------------------------------------------------------
# La liste des adresses a encoder dans les QR codes.
# Le domaine est en tete, a un seul endroit : le jour ou le site change
# d'adresse, tous les QR deja imprimes deviennent caducs, donc ce choix
# doit etre arrete AVANT la fabrication des affichettes.
# ------------------------------------------------------------
DOMAINE = "https://enquete.pomelolab.fr"

lignes_url = [
 "# Adresses des bornes a encoder dans les QR codes",
 "",
 "Domaine utilise : `%s`" % DOMAINE,
 "",
 "> **A verifier avant toute impression.** Un QR code encode une adresse en dur.",
 "> Si le site passe un jour sur un nom de domaine personnalise, toutes les",
 "> affichettes deja posees dans le parc cessent de fonctionner. Ce choix doit",
 "> etre arrete avant la fabrication, pas apres.",
 "",
 "Le depart (E00) n'a pas de QR dans le parc : le code est remis sur un ticket",
 "papier a la caisse, et le joueur arrive sur la page d'accueil du site.",
 "",
 "Chaque affichette porte le QR code ET le nombre a 4 chiffres, a saisir dans",
 "le jeu si le QR refuse de se lire.",
 "",
 "| Code | Borne | Lieu | Sens A | Sens B | Secours | Adresse a encoder |",
 "|---|---|---|---|---|---|---|",
]
for c in PAGES:
    et = etapes[c]
    lignes_url.append("| %s | %s | %s | %s | %s | **%d** | `%s/%s` |" % (
        c, et["nom"], et["lieu"] or "*a preciser*",
        ordre["A"].get(c, "—"), ordre["B"].get(c, "—"), secours[c], DOMAINE, FICHIER[c]))
lignes_url += ["", "## Page d'accueil (remise du ticket)", "",
               "`%s/` — le joueur y arrive avec le code imprime sur son ticket." % DOMAINE,
               "", "## Pourquoi des adresses en chiffres", "",
               "L'adresse s'affiche dans la barre du navigateur avant meme que la",
               "page se charge. `/etapes/e04-indice-les-jumelles-la-carcasse.html`",
               "annoncait l'enigme et le nombre d'etapes ; `/3208/` ne dit rien.",
               "",
               "Le nombre est aussi celui a saisir si le QR refuse de se lire : une",
               "seule reference a imprimer sur l'affichette, pour les deux usages.", ""]
open(os.path.join(ICI, "adresses-des-bornes.md"), "w", encoding="utf-8").write("\n".join(lignes_url) + "\n")

print("\n%d pages fabriquees dans etapes/" % len(PAGES))
print("Adresses des bornes ecrites dans contenu/adresses-des-bornes.md")
print("SQL des %d bornes ecrit dans contenu/bornes.sql" % len(PAGES))
