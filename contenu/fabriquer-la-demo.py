# ============================================================
# FABRIQUER LA DEMO — Le Sanctuaire des Brumes
#
# Une version « bureau » de l'enquête, pour la plaquette commerciale :
# jouable en 15 minutes environ, sans se déplacer, sans billet, sans base de
# données. Les meilleurs moments du jeu s'enchaînent d'un bouton à l'autre,
# puis deux écrans présentent l'offre à un futur client.
#
# La mise en page reprend exactement celle des bornes : barre de
# progression, nom de l'étape en grand titre, une carte par écran.
#
# Adresse volontairement impossible à deviner, pour qu'un ancien joueur ne
# tombe pas dessus : https://enquete.pomelolab.fr/demo-enquete-k7q3x/
# La page n'est liée nulle part sur le site et demande aux moteurs de
# recherche de ne pas l'indexer.
#
# Comme les bornes, la page est FABRIQUÉE : ne pas modifier le HTML à la
# main, relancer ce script.
#   python3 contenu/fabriquer-la-demo.py
# ============================================================
import html, os, json
import openpyxl

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
DOSSIER = "demo-enquete-k7q3x"          # l'adresse de la démo
MEDIA_BASE = "https://sanctuaire-brumes.b-cdn.net"

# Le bouton de contact de la fin. Vide : seul le lien vers le site s'affiche.
CONTACT_MAIL = ""
SITE_POMELO = "https://www.pomelolab.fr"

CODE_SAC = "5824"
QCM = [
    ("Greg l'a kidnappée.", "Mauvais"),
    ("Deux hommes entrés dans le parc après sa fermeture sont à l'origine de sa disparition.", "Mauvais"),
    ("Louis l'a empoisonnée avec sa tisane.", "Moyen"),
    ("Elle s'est endormie.", "Bon"),
    ("Elle a eu un accident de voiture.", "Mauvais"),
]
TOTAL = 6   # les étapes numérotées, du commissaire à la serre
os.makedirs(os.path.join(RACINE, DOSSIER), exist_ok=True)

e = lambda t: html.escape(t, quote=True)

# Les dénouements viennent du cahier, comme dans le vrai jeu.
wb = openpyxl.load_workbook(os.path.join(ICI, "sanctuaire-cahier-de-contenu.xlsx"), read_only=True)
fins = {}
for r in wb["Denouements"].iter_rows(values_only=True):
    if r and str(r[0] or "").strip().isdigit() and r[1]:
        fins[str(r[1]).strip()] = (str(r[4] or "").strip(), str(r[5] or "").strip())
for _, f in QCM:
    assert f in fins, "dénouement absent du cahier : %s" % f


def ecran(contenu, nom, num=None, suivant="Suivant", retour=True, attr=""):
    """Un écran = une carte, comme sur les bornes. Le nom de l'étape devient
    le grand titre de la page, et son numéro remplit la barre de progression."""
    h = ['<section class="ecran card" data-nom="%s"%s%s hidden>'
         % (e(nom), ' data-num="%d"' % num if num else "", attr)]
    h.append(contenu)
    if suivant:
        h.append('  <button data-suivant>%s</button>' % e(suivant))
    if retour:
        h.append('  <button class="btn-secondary" data-retour>Revenir en arrière</button>')
    h.append('</section>')
    return "\n".join(h)


def affiche(nom):
    """L'affiche d'une vidéo, tant qu'elle n'est pas lancée : le fond brumeux
    du jeu, le nom du personnage et un bouton lecture. Sans elle, le joueur
    voit un rectangle gris vide. Fabriquée ici, au format 9/16 des témoignages."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import re, unicodedata
    W, H = 720, 1280
    fond = Image.open(os.path.join(RACINE, "assets/img/fond.webp")).convert("RGB")
    k = max(W / fond.width, H / fond.height)
    fond = fond.resize((int(fond.width * k) + 1, int(fond.height * k) + 1))
    x0, y0 = (fond.width - W) // 2, (fond.height - H) // 2
    img = fond.crop((x0, y0, x0 + W, y0 + H)).filter(ImageFilter.GaussianBlur(2))
    voile = Image.new("RGB", (W, H), (11, 13, 20))
    img = Image.blend(img, voile, 0.45)
    d = ImageDraw.Draw(img)
    cx, cy, r = W // 2, H // 2 - 60, 92
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(201, 162, 75), width=6)
    d.polygon([(cx - 30, cy - 46), (cx - 30, cy + 46), (cx + 52, cy)], fill=(228, 200, 122))
    titre = ImageFont.truetype(os.path.join(RACINE, "assets/fonts/dcc-ash-fr.otf"), 64)
    lignes, ligne = [], ""
    for mot in nom.upper().split():
        essai = (ligne + " " + mot).strip()
        if d.textlength(essai, font=titre) > W - 100 and ligne:
            lignes.append(ligne); ligne = mot
        else:
            ligne = essai
    lignes.append(ligne)
    y = cy + r + 60
    for l in lignes:
        d.text((W // 2, y), l, font=titre, fill=(219, 218, 125), anchor="ma"); y += 72
    petit = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    d.text((W // 2, y + 18), "Appuyez pour lancer la vidéo", font=petit, fill=(191, 183, 172), anchor="ma")
    nomfic = "affiche-" + re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFD", nom.lower())
                                 .encode("ascii", "ignore").decode()).strip("-") + ".webp"
    img.save(os.path.join(RACINE, DOSSIER, nomfic), "WEBP", quality=78)
    return nomfic


def video(fichier, legende, nom):
    return ('  <video controls preload="none" playsinline data-video poster="%s">'
            '<source src="%s/%s" type="video/mp4"></video>\n'
            '  <p class="witness-name">%s</p>\n'
            '  <button class="btn-lien" data-passer>Passer la vidéo</button>'
            % (e(affiche(nom)), MEDIA_BASE, e(fichier), e(legende)))


def galerie(fichiers, bouton, texte_alt):
    imgs = "".join('<img class="photo-borne" loading="lazy" data-galerie-photo src="../assets/img/%s" alt="%s"%s>'
                   % (e(f), e(texte_alt), "" if i == 0 else " hidden") for i, f in enumerate(fichiers))
    return ('  <div class="galerie" data-galerie>\n'
            '    <button data-galerie-ouvrir>%s</button>\n'
            '    <div data-galerie-vue hidden>%s\n'
            '      <div class="galerie-barre"><button class="btn-secondary" data-galerie-prec>‹ Précédente</button>'
            '<span class="galerie-compte" data-galerie-compte></span>'
            '<button class="btn-secondary" data-galerie-suiv>Suivante ›</button></div>\n'
            '    </div>\n  </div>' % (e(bouton), imgs))


E = []

E.append(ecran(
    '  <div class="eyebrow">Une enquête de démonstration</div>\n'
    '  <p class="lead-demo">Une nuit de pleine lune, la brume a recouvert le Parc Zoologique &amp; Botanique '
    'de Mulhouse. Isabelle, soigneuse, a disparu près de l\'enclos des loups.</p>\n'
    '  <p>Vous êtes l\'enquêteur chargé de l\'affaire. Pendant l\'opération, les joueurs ont parcouru tout le '
    'parc de borne en borne, en scannant des QR codes. Ici, un simple bouton vous mène d\'une étape à l\'autre.</p>\n'
    '  <p class="muted">Environ 15 minutes. Montez le son.</p>',
    "Le Sanctuaire des Brumes", suivant="Commencer l'enquête", retour=False))

E.append(ecran(video("le-commissaire-jean-2-79swb7.mp4", "Le commissaire Jean, votre supérieur", "Le commissaire Jean"),
               "Le commissaire Jean", 1))

E.append(ecran(video("greg-sens-a-sj7kmm.mp4", "Greg, agent technique, pas très rassurant", "Greg"),
               "Greg", 2))

E.append(ecran(
    '  <button id="decrocher" class="btn-appel">Décrocher</button>\n'
    '  <div id="blocAppel" hidden><audio id="audioAppel" controls preload="none">'
    '<source src="%s/appel-du-commissaire-bm7fpb.mp3" type="audio/mpeg"></audio></div>\n'
    '  <img class="photo-borne" src="../assets/img/appel-commissaire.webp" alt="Appel entrant du commissaire Jean">\n'
    '  <p class="witness-name">Commissaire Jean, dubitatif</p>\n'
    '  <p>Vous avez un appel entrant du commissaire Jean.</p>' % MEDIA_BASE,
    "Appel du commissaire", 3))

E.append(ecran(
    '  <p>Le commissaire vous a envoyé 4 images.</p>\n'
    + galerie(["commissaire-%d.webp" % i for i in range(1, 5)], "Voir les images", "Image envoyée par le commissaire"),
    "Appel du commissaire", 3))

E.append(ecran(
    '  <p>Vous venez de tomber sur un sac qui ne semble pas être à sa place. Faites défiler son contenu.</p>\n'
    + galerie(["sac-%d.webp" % i for i in range(1, 7)], "Voir le contenu du sac", "Objet trouvé dans le sac")
    + '\n  <p>Certains objets portaient un chiffre. Dans l\'ordre où vous les avez vus, ils forment un nombre '
      'à quatre chiffres. Notez-le : vous ne savez pas encore à quoi il sert.</p>',
    "Le sac du botaniste", 4))

E.append(ecran(video("le-botaniste-acanpa-2.mp4", "Louis, botaniste au Parc Zoologique & Botanique de Mulhouse", "Louis, le botaniste"),
               "Louis, le botaniste", 5))

E.append(ecran(
    '  <p>Pour pénétrer dans la serre, entrez le code que vous avez trouvé un peu plus tôt.</p>\n'
    '  <input type="text" id="codeDemo" inputmode="numeric" maxlength="6" placeholder="4 chiffres" autocomplete="off">\n'
    '  <button id="validerCode">Ouvrir</button>\n'
    '  <p class="quiz-verdict quiz-faux" id="codeFaux" hidden></p>\n'
    '  <button class="btn-lien" id="codeAide">J\'ai perdu le code</button>\n'
    '  <div class="card indice" id="codeBon" hidden><div class="eyebrow">La porte s\'ouvre</div>'
    '<p>Entrez dans la serre.</p></div>',
    "Louis, le botaniste", 5, attr=' data-bloque="code"'))

props = "".join('<button class="quiz-prop" data-fin="%s">%s</button>' % (e(f), e(p)) for p, f in QCM)
E.append(ecran(
    '  <p>Vous êtes à deux doigts d\'élucider le mystère.</p>\n'
    '  <div class="ecran-titre">Qu\'est-il arrivé à Isabelle ?</div>\n'
    '  <div data-conclusions>%s</div>' % props,
    "La serre", 6, suivant=None, attr=' data-qcm'))

E.append(ecran(video("la-serre-4.mp4", "La soirée d'Isabelle, vue de ses yeux", "La soirée d'Isabelle"), "La serre", 6))

E.append(ecran(
    '  <img class="photo-borne" src="../assets/img/aveu-greg.webp" alt="La lettre de Greg">\n'
    '  <p class="witness-name">Une dernière pièce au dossier : la lettre de Greg.</p>',
    "La serre", 6))

verdicts = "".join('<div class="card indice denouement" data-denouement="%s" hidden><div class="eyebrow">%s</div>%s</div>'
                   % (e(nom), e(titre), "".join("<p>%s</p>" % e(p) for p in texte.split("\n") if p.strip()))
                   for nom, (titre, texte) in fins.items() if nom in {f for _, f in QCM})
E.append(ecran('  ' + verdicts + '\n  <p class="ecran-titre fin-classee">L\'affaire est classée.</p>',
               "La serre", 6, attr=' data-verdict'))

E.append(ecran(
    '  <div class="eyebrow">Dans les coulisses</div>\n'
    '  <p>Pendant que les joueurs enquêtent, l\'organisateur suit chaque groupe en direct : où il en est, '
    'depuis combien de temps, et qui a besoin d\'aide.</p>\n'
    '  <img class="photo-borne capture" src="suivi-en-direct-fictif.webp" '
    'alt="Le tableau de bord de suivi en direct, avec des données fictives">\n'
    '  <p class="witness-name">Le suivi en direct, avec des données fictives</p>\n'
    '  <ul class="demo-liste">\n'
    '    <li>Un groupe bloqué est débloqué à distance, en quelques minutes.</li>\n'
    '    <li>Les joueurs signalent un problème depuis leur téléphone.</li>\n'
    '    <li>Un bilan chiffré à la fin : fréquentation, parcours, avis.</li>\n'
    '  </ul>',
    "Côté organisateur"))

contact = ('<a class="btn" href="mailto:%s?subject=%s">Demander un rendez-vous</a>'
           % (e(CONTACT_MAIL), e("Une enquête dans notre établissement")) if CONTACT_MAIL else "")
E.append(ecran(
    '  <p class="lead-demo">Imaginez cette enquête dans vos murs, écrite à partir de vos collections, '
    'de vos lieux et de vos histoires.</p>\n'
    '  <div class="demo-chiffres">\n'
    '    <div><b>1 745</b><span>enquêteurs en 16 jours</span></div>\n'
    '    <div><b>4,71/5</b><span>de satisfaction</span></div>\n'
    '    <div><b>2h17</b><span>de visite en médiane</span></div>\n'
    '  </div>\n'
    '  <ul class="demo-liste">\n'
    '    <li>De nouveaux publics : familles, groupes d\'amis, de tous âges.</li>\n'
    '    <li>Une visite plus longue, des lieux redécouverts.</li>\n'
    '    <li>Clé en main : scénario, tournage, outil numérique, accueil et suivi.</li>\n'
    '  </ul>\n'
    '  %s\n'
    '  <a class="btn%s" href="%s" target="_blank" rel="noopener">Découvrir Pomelo</a>'
    % (contact, " btn-secondary" if contact else "", e(SITE_POMELO)),
    "Et chez vous ?", suivant=None))

STYLE = """
  .demo-badge { font-family: var(--texte); font-weight: 700; font-size: 0.68rem; letter-spacing: 2px;
                text-transform: uppercase; color: var(--bg); background: var(--gold); border-radius: 999px;
                padding: 3px 9px; flex: none; }
  .lead-demo { font-size: 1.1rem; }
  .demo-liste { padding-left: 18px; margin: 0 0 16px; }
  .demo-liste li { margin-bottom: 6px; }
  .demo-chiffres { display: flex; gap: 12px; margin: 16px 0 18px; }
  .demo-chiffres div { flex: 1; border-top: 2px solid var(--gold); padding-top: 8px; }
  .demo-chiffres b { display: block; font-size: 1.4rem; color: var(--gold-bright); font-weight: 700; }
  .demo-chiffres span { font-size: 0.78rem; color: var(--fog); line-height: 1.3; display: block; }
  .capture { border: 1px solid var(--hair); }
  .denouement { margin-bottom: 14px; }
  .fin-classee { margin: 6px 0 16px; }
  .etincelle { position: fixed; top: -12px; width: 8px; height: 14px; border-radius: 2px; z-index: 50;
               animation: tombe linear forwards; pointer-events: none; }
  @keyframes tombe { to { transform: translateY(110vh) rotate(540deg); opacity: .2; } }
"""

page = "\n".join([
    '<!DOCTYPE html>',
    '<html lang="fr">',
    '<head>',
    '<meta charset="UTF-8">',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    '<meta name="robots" content="noindex, nofollow">',
    '<title>Le Sanctuaire des Brumes, démonstration</title>',
    '<link rel="preconnect" href="https://fonts.googleapis.com">',
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Mulish:wght@300;700&display=swap">',
    '<link rel="stylesheet" href="../assets/css/style.css">',
    '<style>%s</style>' % STYLE,
    '</head>',
    '<body>',
    '<div class="wrap">',
    '  <div class="progression" id="position" role="progressbar" aria-valuemin="0" aria-valuemax="100">',
    '    <span class="demo-badge">Démo</span>',
    '    <div class="progression-barre"><span></span></div>',
    '    <div class="progression-compte" data-total="%d"></div>' % TOTAL,
    '  </div>',
    '  <h1 id="titreEtape">Le Sanctuaire des Brumes</h1>',
    "\n".join(E),
    '</div>',
    '<footer>',
    '  <img class="signature" src="../assets/img/logo-pomelo.webp" alt="Pomelo Événementiel">',
    '  Le Sanctuaire des Brumes, une enquête Pomelo Événementiel',
    '</footer>',
    '<script src="demo.js"></script>',
    '<script>demarrerDemo(%s);</script>' % json.dumps(CODE_SAC),
    '</body>',
    '</html>',
    ''])

open(os.path.join(RACINE, DOSSIER, "index.html"), "w", encoding="utf-8").write(page)
print("Démo fabriquée : %s/index.html (%d écrans)" % (DOSSIER, len(E)))
