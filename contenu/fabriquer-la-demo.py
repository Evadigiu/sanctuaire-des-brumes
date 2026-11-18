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


def sonnerie():
    """La sonnerie de l'appel du commissaire : « drring, drring », puis un
    silence, 3 secondes jouées en boucle. Un vrai fichier audio et non un son
    synthétisé dans le navigateur : sur iPhone, un fichier sonne même en mode
    silencieux, un son synthétisé non."""
    import wave, struct, math
    taux = 22050
    motif = [(0.4, True), (0.2, False), (0.4, True), (2.0, False)]
    ech = []
    for duree, sonne in motif:
        n = int(duree * taux)
        for i in range(n):
            t = i / taux
            if sonne:
                v = 0.5 * math.sin(2 * math.pi * 400 * t) + 0.5 * math.sin(2 * math.pi * 450 * t)
                v *= 0.5 + 0.5 * (math.sin(2 * math.pi * 20 * t) > 0)      # le grésillement
                v *= min(1.0, i / 200, (n - i) / 200)                        # sans clic
                ech.append(int(v * 0.45 * 32767))
            else:
                ech.append(0)
    with wave.open(os.path.join(RACINE, DOSSIER, "sonnerie.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(taux)
        w.writeframes(b"".join(struct.pack("<h", x) for x in ech))
    return "sonnerie.wav"


def ecran(contenu, nom, num=None, suivant="Suivant", retour=True, attr="", passer=None):
    """Un écran = une carte, comme sur les bornes. Le nom de l'étape devient
    le grand titre de la page, et son numéro remplit la barre de progression."""
    if passer is None:
        passer = bool(num)
    h = ['<section class="ecran card" data-nom="%s"%s%s hidden>'
         % (e(nom), ' data-num="%d"' % num if num else "", attr)]
    h.append(contenu)
    if suivant:
        h.append('  <button data-suivant>%s</button>' % e(suivant))
    if retour:
        h.append('  <button class="btn-secondary" data-retour>Revenir en arrière</button>')
    if passer:
        # Un client pressé file directement aux écrans qui le concernent.
        h.append('  <button class="btn-lien" data-passer-demo>Passer la démo</button>')
    h.append('</section>')
    return "\n".join(h)


def video(fichier, legende, nom=None):
    return ('  <video controls preload="none" playsinline data-video>'
            '<source src="%s/%s" type="video/mp4"></video>\n'
            '  <p class="witness-name">%s</p>'
            % (MEDIA_BASE, e(fichier), e(legende)))


def galerie(fichiers, bouton, texte_alt):
    # Les images sont empilées et chargées d'avance : passer à la suivante est
    # un fondu, sans le rectangle noir d'une image qui se charge.
    imgs = "".join('<img class="photo-borne%s" data-galerie-photo src="../assets/img/%s" alt="%s">'
                   % (" actif" if i == 0 else "", e(f), e(texte_alt)) for i, f in enumerate(fichiers))
    return ('  <div class="galerie" data-galerie>\n'
            '    <button data-galerie-ouvrir>%s</button>\n'
            '    <div data-galerie-vue hidden><div class="galerie-pile">%s</div>\n'
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
    "Le Sanctuaire des Brumes", suivant="Commencer l'enquête", retour=False, passer=True))

E.append(ecran(video("le-commissaire-jean-2-79swb7.mp4", "Le commissaire Jean, votre supérieur", "Le commissaire Jean"),
               "Le commissaire Jean", 1))

E.append(ecran(video("greg-sens-a-sj7kmm.mp4", "Greg, agent technique, pas très rassurant", "Greg"),
               "Greg", 2))

E.append(ecran(
    '  <audio id="sonnerie" loop preload="auto"><source src="%s" type="audio/wav"></audio>\n' % sonnerie() +
    '  <button id="decrocher" class="btn-appel">Décrocher</button>\n'
    '  <div id="blocAppel" hidden><audio id="audioAppel" controls preload="none">'
    '<source src="%s/appel-du-commissaire-bm7fpb.mp3" type="audio/mpeg"></audio></div>\n'
    '  <img class="photo-borne" src="../assets/img/appel-commissaire.webp" alt="Appel entrant du commissaire Jean">\n'
    '  <p class="witness-name">Commissaire Jean, dubitatif</p>\n'
    '  <p>Vous avez un appel entrant du commissaire Jean.</p>' % MEDIA_BASE,
    "Appel du commissaire", 3, attr=' data-appel'))

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
    '  <div class="ecran-titre question-finale">Qu\'est-il arrivé à Isabelle ?</div>\n'
    '  <div data-conclusions>%s</div>' % props,
    "La serre", 6, suivant=None, attr=' data-qcm'))

E.append(ecran(video("la-serre-4.mp4", "La soirée d'Isabelle, vue de ses yeux", "La soirée d'Isabelle"), "La serre", 6))

E.append(ecran(
    '  <img class="photo-borne" src="../assets/img/aveu-greg.webp" alt="La lettre de Greg">\n'
    '  <p class="witness-name">Une dernière pièce au dossier : la lettre de Greg.</p>',
    "La serre", 6))

verdicts = "".join('<div class="card indice denouement" data-denouement="%s" hidden><div class="eyebrow">%s</div>%s</div>'
                   % (e(nom), e(titre), "".join("<p>%s</p>" % e(p.replace(" — ", ", ").replace(" – ", ", ")) for p in texte.split("\n") if p.strip()))
                   for nom, (titre, texte) in fins.items() if nom in {f for _, f in QCM})
E.append(ecran('  ' + verdicts + '\n  <p class="ecran-titre fin-classee">L\'affaire est classée.</p>',
               "La serre", 6, attr=' data-verdict'))

E.append(ecran(
    '  <div class="eyebrow">Dans les coulisses</div>\n'
    '  <p class="lead-demo">Pendant que vos visiteurs enquêtent, vous gardez la main, en direct, depuis votre téléphone.</p>\n'
    '  <div class="coulisse">\n'
    '    <div class="coulisse-titre"><span>1</span>Le suivi en direct</div>\n'
    '    <p>Combien de groupes jouent, où en est chacun, qui est bloqué : tout se voit en temps réel, '
    'et chaque problème signalé par un joueur arrive aussitôt.</p>\n'
    '    <img class="photo-borne capture" src="suivi-en-direct-fictif.webp" alt="Le suivi en direct, avec des données fictives">\n'
    '  </div>\n'
    '  <div class="coulisse">\n'
    '    <div class="coulisse-titre"><span>2</span>Les statistiques</div>\n'
    '    <p>Fréquentation, temps passé à chaque étape, enquêtes terminées : vous suivez votre opération '
    'chiffres en main, jour après jour.</p>\n'
    '    <img class="photo-borne capture" src="statistiques-fictives.webp" alt="Les statistiques, avec des données fictives">\n'
    '  </div>\n'
    '  <p class="witness-name">Captures avec des données fictives.</p>',
    "Côté organisateur"))

contact = ('<a class="btn" href="mailto:%s?subject=%s">Demander un rendez-vous</a>'
           % (e(CONTACT_MAIL), e("Une enquête dans notre établissement")) if CONTACT_MAIL else "")
AVANTAGES = [
    ("Plus de visiteurs", "1 745 enquêteurs en 16 jours, et presque deux fois plus de joueurs en deuxième semaine."),
    ("Des visites plus longues", "2h17 de jeu en médiane : plus de temps sur place, et autant d'occasions de passer au café et à la boutique."),
    ("Des visiteurs conquis", "4,71/5 de satisfaction, et des joueurs qui réclament déjà la prochaine enquête."),
    ("Zéro charge pour vos équipes", "Scénario, tournage, outil numérique, billetterie, accueil et suivi : nous nous occupons de tout."),
]
E.append(ecran(
    '  <div class="eyebrow">Pomelo Événementiel</div>\n'
    '  <p class="accroche-fin">Votre lieu mérite son enquête.</p>\n'
    '  <p>Nous l\'écrivons à partir de vos collections, de vos lieux et de vos histoires. Vous, vous récoltez :</p>\n'
    '  <div class="avantages">%s</div>\n'
    '  <blockquote class="citation-demo">« On n\'a jamais autant visité le parc&nbsp;!&nbsp;»<span>Une joueuse du Sanctuaire des Brumes</span></blockquote>\n'
    '  %s\n'
    '  <a class="btn%s" href="%s" target="_blank" rel="noopener">Découvrir Pomelo</a>\n'
    '  <button class="btn-secondary" data-rejouer>Rejouer la démo</button>'
    % ("".join('<div class="avantage"><b>%s</b><span>%s</span></div>' % (e(a), e(b)) for a, b in AVANTAGES),
       contact, " btn-secondary" if contact else "", e(SITE_POMELO)),
    "Et chez vous ?", suivant=None, retour=False))

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
  .btn-appel.sonne { animation: sonne 1s ease-in-out infinite; }
  @keyframes sonne { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); box-shadow: 0 0 0 8px rgba(123,178,125,.25); } }
  @media (prefers-reduced-motion: reduce) { .btn-appel.sonne { animation: none; } }
  .galerie-pile { display: grid; }
  .galerie-pile > img { grid-area: 1 / 1; opacity: 0; transition: opacity .35s ease; margin: 0; }
  .galerie-pile > img.actif { opacity: 1; }
  .question-finale { margin-top: 30px; }
  .coulisse { margin: 26px 0 8px; }
  .coulisse-titre { display: flex; align-items: center; gap: 10px; font-weight: 700; color: var(--gold-bright);
                    text-transform: uppercase; letter-spacing: 1px; font-size: 0.9rem; margin-bottom: 8px; }
  .coulisse-titre span { width: 26px; height: 26px; border-radius: 50%; background: var(--gold); color: var(--bg);
                         display: inline-flex; align-items: center; justify-content: center; font-size: 0.8rem; }
  .coulisse p { margin-bottom: 12px; }
  .accroche-fin { font-family: var(--titre); color: var(--titre-or); font-size: 1.7rem; line-height: 1.15;
                  text-transform: uppercase; letter-spacing: 1px; margin: 4px 0 12px; }
  .avantages { display: grid; gap: 12px; margin: 18px 0 22px; }
  .avantage { background: var(--panel2); border-left: 3px solid var(--gold); border-radius: 6px; padding: 12px 14px; }
  .avantage b { display: block; color: var(--gold-bright); font-size: 1.02rem; margin-bottom: 3px; }
  .avantage span { color: var(--ink); font-size: 0.9rem; line-height: 1.45; }
  .citation-demo { margin: 0 0 22px; padding: 4px 0 4px 14px; border-left: 2px solid var(--hair);
                   font-style: italic; color: var(--ink); font-size: 1.05rem; }
  .citation-demo span { display: block; font-style: normal; font-size: 0.78rem; color: var(--fog); margin-top: 4px; }
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
    '  Le Sanctuaire des Brumes, version démo - une enquête Pomelo',
    '</footer>',
    '<script src="demo.js"></script>',
    '<script>demarrerDemo(%s);</script>' % json.dumps(CODE_SAC),
    '</body>',
    '</html>',
    ''])

open(os.path.join(RACINE, DOSSIER, "index.html"), "w", encoding="utf-8").write(page)
print("Démo fabriquée : %s/index.html (%d écrans)" % (DOSSIER, len(E)))
