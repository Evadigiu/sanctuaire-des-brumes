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
SORTIE = os.path.join(RACINE, "etapes")

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
FICHIER = {c: "%s-%s.html" % (c.lower(), slug(etapes[c]["nom"])) for c in PAGES}

TOTAL = {s: len([c for c in ordre[s] if c != "E00"]) for s in ("A", "B")}

# ============================================================
# Mecaniques particulieres, declarees explicitement plutot que
# devinees a partir du texte des remarques.
# ============================================================
EPREUVE_REPONSE = {"E08": ("11", "S")}   # etape -> (bonne reponse, lettre debloquee)
APPEL_AUDIO     = {"E12"}
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
        h.append('  <!-- Remplacer la source par la vraie vidéo une fois tournée -->')
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
        h.append('  <a href="%s" class="btn">Continuer l\'enquête</a>' % e(lg["lien"]) if lg.get("lien")
                 else '  <p class="muted">Fin du parcours.</p>')
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
<link rel="stylesheet" href="../assets/css/style.css">
</head>
<!-- PAGE FABRIQUÉE AUTOMATIQUEMENT depuis contenu/sanctuaire-cahier-de-contenu.xlsx
     Toute correction faite ici sera perdue à la prochaine fabrication.
     Corriger le cahier, puis relancer contenu/fabriquer-les-pages.py -->
<body data-borne="{borne}">

<div class="wrap">
  <div class="timer" id="timer">Chargement du chrono...</div>
  <div class="eyebrow" id="position" data-A="{posA}" data-B="{posB}"></div>
  <h1>{titre}</h1>
{ecrans}
</div>

<footer>Le Sanctuaire des Brumes</footer>

<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
<script src="../assets/js/supabase-client.js"></script>
<script src="../assets/js/game.js"></script>
<script src="../assets/js/etape.js"></script>
<script>
  demarrerEtape();
{extra}</script>

</body>
</html>
"""

if os.path.isdir(SORTIE):
    for f in os.listdir(SORTIE):
        if f.endswith(".html"): os.remove(os.path.join(SORTIE, f))
else:
    os.makedirs(SORTIE)

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
            x = dict(x, lien=FICHIER.get(suite) if suite else None)
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

    page = GABARIT.format(titre=e(et["nom"]), borne=e(et["nom"]),
                          posA=e(posA), posB=e(posB),
                          ecrans="\n".join(blocs), extra=extra)
    open(os.path.join(SORTIE, FICHIER[c]), "w", encoding="utf-8").write(page)
    print("  %-38s %-3s A:%-3s B:%-3s %d écran(s)" % (
        FICHIER[c], c, ordre["A"].get(c, "-"), ordre["B"].get(c, "-"), len(blocs)))

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

print("\n%d pages fabriquees dans etapes/" % len(PAGES))
print("SQL des %d bornes ecrit dans contenu/bornes.sql" % len(PAGES))
