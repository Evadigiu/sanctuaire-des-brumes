# ============================================================
# FABRIQUER LA DEMO — Le Sanctuaire des Brumes
#
# Une version « bureau » de l'enquête, pour la plaquette commerciale :
# jouable en 10 à 15 minutes, sans se déplacer, sans billet, sans base de
# données. Les meilleurs moments du jeu s'enchaînent d'un bouton à l'autre,
# puis deux écrans présentent l'offre à un futur client.
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

e = lambda t: html.escape(t, quote=True)

# Les dénouements viennent du cahier, comme dans le vrai jeu.
wb = openpyxl.load_workbook(os.path.join(ICI, "sanctuaire-cahier-de-contenu.xlsx"), read_only=True)
fins = {}
for r in wb["Denouements"].iter_rows(values_only=True):
    if r and str(r[0] or "").strip().isdigit() and r[1]:
        fins[str(r[1]).strip()] = (str(r[4] or "").strip(), str(r[5] or "").strip())
for _, f in QCM:
    assert f in fins, "dénouement absent du cahier : %s" % f


def ecran(contenu, titre=None, etape=None, suivant="Suivant", retour=True, attr=""):
    h = ['<section class="ecran card"%s hidden>' % attr]
    if etape:
        h.append('  <div class="demo-etape">%s</div>' % e(etape))
    if titre:
        h.append('  <div class="ecran-titre">%s</div>' % e(titre))
    h.append(contenu)
    if suivant:
        h.append('  <button data-suivant>%s</button>' % e(suivant))
    if retour:
        h.append('  <button class="btn-secondary" data-retour>Revenir en arrière</button>')
    h.append('</section>')
    return "\n".join(h)


def video(fichier, legende):
    return ('  <video controls preload="none" playsinline data-video>'
            '<source src="%s/%s" type="video/mp4"></video>\n'
            '  <p class="witness-name">%s</p>\n'
            '  <button class="btn-lien" data-passer>Passer la vidéo</button>'
            % (MEDIA_BASE, e(fichier), e(legende)))


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
E.append(ecran('''  <p class="lead-demo">Une nuit de pleine lune, la brume a recouvert le Parc Zoologique &amp; Botanique de Mulhouse. Isabelle, soigneuse, a disparu près de l'enclos des loups.</p>
  <p>Vous êtes l'enquêteur chargé de l'affaire. Pendant l'opération, les joueurs ont parcouru tout le parc, de borne en borne, en scannant des QR codes. Dans cette démonstration, un simple bouton vous mène d'une étape à l'autre.</p>
  <p class="muted">Environ 10 à 15 minutes, avec le son.</p>''',
  titre="Une disparition", etape="Démonstration", suivant="Commencer l'enquête", retour=False))
E.append(ecran(video("le-commissaire-jean-2-79swb7.mp4", "Le commissaire Jean, votre supérieur"),
  titre="Le briefing", etape="Étape 1 sur 6 · Le commissaire Jean"))
E.append(ecran(video("greg-sens-a-sj7kmm.mp4", "Greg, agent technique, pas très rassurant")
  + '\n  <p>Chaque témoin a sa version. À vous de démêler le vrai du faux.</p>',
  titre="Un témoin", etape="Étape 2 sur 6 · Greg"))
E.append(ecran('''  <button id="decrocher" class="btn-appel">Décrocher</button>
  <div id="blocAppel" hidden><audio id="audioAppel" controls preload="none"><source src="%s/appel-du-commissaire-bm7fpb.mp3" type="audio/mpeg"></audio></div>
  <img class="photo-borne" src="../assets/img/appel-commissaire.webp" alt="Appel entrant du commissaire Jean">
  <p>Vous avez un appel entrant du commissaire Jean.</p>''' % MEDIA_BASE,
  titre="Un appel inattendu", etape="Étape 3 sur 6 · L'appel du commissaire"))
E.append(ecran('  <p>Le commissaire vous a envoyé 4 images. Examinez-les bien.</p>\n'
  + galerie(["commissaire-%d.webp" % i for i in range(1, 5)], "Voir les images", "Image envoyée par le commissaire"),
  titre="Les images du commissaire", etape="Étape 3 sur 6 · L'appel du commissaire"))
E.append(ecran('  <p>Vous venez de tomber sur un sac qui ne semble pas être à sa place. Faites défiler son contenu.</p>\n'
  + galerie(["sac-%d.webp" % i for i in range(1, 7)], "Voir le contenu du sac", "Objet trouvé dans le sac")
  + '''
  <p>Certains objets portaient un chiffre. Dans l'ordre où vous les avez vus, ils forment le code qui ouvre la serre.</p>
  <input type="text" id="codeDemo" inputmode="numeric" maxlength="6" placeholder="4 chiffres" autocomplete="off">
  <button id="validerCode">Ouvrir la serre</button>
  <p class="quiz-verdict quiz-faux" id="codeFaux" hidden></p>
  <button class="btn-lien" id="codeAide">Je n'y arrive pas</button>
  <div class="card indice" id="codeBon" hidden><div class="eyebrow">La porte s'ouvre</div><p>Entrez dans la serre.</p></div>''',
  titre="Le sac du botaniste", etape="Étape 4 sur 6 · Une énigme", attr=' data-bloque="code"'))
props = "".join('<button class="quiz-prop" data-fin="%s">%s</button>' % (e(f), e(p)) for p, f in QCM)
E.append(ecran('''  <p>Vous êtes à deux doigts d'élucider le mystère. Une dernière question avant la vérité :</p>
  <div class="ecran-titre">Qu'est-il arrivé à Isabelle ?</div>
  <div data-conclusions>%s</div>''' % props,
  titre="La serre", etape="Étape 5 sur 6 · Vos conclusions", suivant=None, attr=' data-qcm'))
E.append(ecran(video("la-serre-4.mp4", "La soirée d'Isabelle, vue de ses yeux"),
  titre="La vérité", etape="Étape 6 sur 6 · Le dénouement"))
E.append(ecran('  <img class="photo-borne" src="../assets/img/aveu-greg.webp" alt="La lettre de Greg">\n'
  '  <p class="witness-name">Une dernière pièce au dossier : la lettre de Greg.</p>',
  titre="La lettre de Greg", etape="Étape 6 sur 6 · Le dénouement"))
verdicts = "".join('<div class="card indice denouement" data-denouement="%s" hidden><div class="eyebrow">%s</div>%s</div>'
                   % (e(nom), e(titre), "".join("<p>%s</p>" % e(p) for p in texte.split("\n") if p.strip()))
                   for nom, (titre, texte) in fins.items() if nom in {f for _, f in QCM})
E.append(ecran('  ' + verdicts + '\n  <p class="ecran-titre fin-classee">L\'affaire est classée.</p>',
  titre="Le verdict", etape="Fin de l'enquête", attr=' data-verdict'))
E.append(ecran('''  <p>Pendant que les joueurs enquêtent, l'organisateur suit chaque groupe en direct : où il en est, depuis combien de temps, et qui a besoin d'aide.</p>
  <img class="photo-borne capture" src="suivi-en-direct-fictif.webp" alt="Le tableau de bord de suivi en direct, avec des données fictives">
  <p class="muted">Capture avec des données fictives.</p>
  <ul class="demo-liste">
    <li>Un groupe bloqué est débloqué à distance, en quelques minutes.</li>
    <li>Les joueurs signalent un problème depuis leur téléphone.</li>
    <li>Un bilan chiffré à la fin : fréquentation, parcours, avis.</li>
  </ul>''', titre="Côté organisateur", etape="Dans les coulisses"))
contact = ('<a class="btn" href="mailto:%s?subject=%s">Demander un rendez-vous</a>'
           % (e(CONTACT_MAIL), e("Une enquête dans notre établissement")) if CONTACT_MAIL else "")
E.append(ecran('''  <p class="lead-demo">Imaginez cette enquête dans vos murs, écrite à partir de vos collections, de vos lieux et de vos histoires.</p>
  <div class="demo-chiffres">
    <div><b>1 745</b><span>enquêteurs en 16 jours</span></div>
    <div><b>4,71/5</b><span>de satisfaction</span></div>
    <div><b>2h17</b><span>de visite en médiane</span></div>
  </div>
  <ul class="demo-liste">
    <li>De nouveaux publics : familles, groupes d'amis, de tous âges.</li>
    <li>Une visite plus longue, des lieux redécouverts.</li>
    <li>Clé en main : scénario, tournage, outil numérique, accueil et suivi.</li>
  </ul>
  %s
  <a class="btn%s" href="%s" target="_blank" rel="noopener">Découvrir Pomelo</a>''' % (contact, " btn-secondary" if contact else "", e(SITE_POMELO)),
  titre="Et chez vous ?", etape="Pomelo Événementiel", suivant=None))

page = '''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow">
<title>Le Sanctuaire des Brumes, démonstration</title>
<link rel="stylesheet" href="../assets/css/style.css">
<style>
  .demo-etape { font-size: 0.72rem; letter-spacing: 2px; text-transform: uppercase; color: var(--gold); margin-bottom: 6px; }
  .lead-demo { font-size: 1.1rem; color: var(--ink); }
  .demo-liste { padding-left: 18px; color: var(--ink); }
  .demo-liste li { margin-bottom: 6px; }
  .demo-chiffres { display: flex; gap: 12px; margin: 14px 0; }
  .demo-chiffres div { flex: 1; border-top: 3px solid var(--gold); padding-top: 8px; }
  .demo-chiffres b { display: block; font-size: 1.5rem; color: var(--gold-bright); }
  .demo-chiffres span { font-size: 0.8rem; color: var(--fog); }
  .capture { border: 1px solid var(--hair); }
  .fin-classee { margin-top: 18px; }
  .etincelle { position: fixed; top: -12px; width: 8px; height: 14px; border-radius: 2px; z-index: 50;
               animation: tombe linear forwards; pointer-events: none; }
  @keyframes tombe { to { transform: translateY(110vh) rotate(540deg); opacity: .2; } }
</style>
</head>
<body>
<div class="wrap">
  <div class="eyebrow">Pomelo Événementiel · Démonstration</div>
  <h1>Le Sanctuaire des Brumes</h1>
%s
</div>
<footer>
  <img class="signature" src="../assets/img/logo-pomelo.webp" alt="Pomelo Événementiel">
  Pomelo Événementiel
</footer>
<script src="demo.js"></script>
<script>demarrerDemo(%s);</script>
</body>
</html>
''' % ("\n".join(E), json.dumps(CODE_SAC))

os.makedirs(os.path.join(RACINE, DOSSIER), exist_ok=True)
open(os.path.join(RACINE, DOSSIER, "index.html"), "w", encoding="utf-8").write(page)
print("Démo fabriquée : %s/index.html (%d écrans)" % (DOSSIER, len(E)))
