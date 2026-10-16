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
import os, re, sys, json, unicodedata, html
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

# ------------------------------------------------------------
# LE QUIZ QUI SUIT UNE VIDEO
#
# Les questions s'affichent SOUS la video pendant qu'elle tourne, chacune
# au moment indique dans le cahier. Le joueur repond sans arreter la
# lecture : c'est tout l'interet, et c'est pour cela que cette video ne
# part pas en plein ecran comme les autres (elle cacherait les reponses).
#
# Une question reste affichee jusqu'a l'arrivee de la suivante. Un groupe
# qui discute n'est donc pas puni par une fenetre de trois secondes.
# ------------------------------------------------------------
def en_secondes(v):
    """"0:48" ou "1:20" -> un nombre de secondes."""
    t = propre(v).replace("'", ":").replace("h", ":")
    if not t: return None
    morceaux = [m for m in t.split(":") if m.strip() != ""]
    try: morceaux = [int(float(m)) for m in morceaux]
    except ValueError: return None
    sec = 0
    for m in morceaux: sec = sec * 60 + m
    return sec

def colonnes_du_quiz(ws):
    """Ou se trouve chaque colonne de l'onglet Quiz.

    On les cherche par leur titre au lieu de compter les cases. Le jour ou
    une cinquieme proposition est ajoutee, ou une colonne deplacee, le
    generateur suit sans qu'on y touche — et il le dit clairement si un
    titre manque, plutot que de lire la mauvaise case en silence.
    """
    titres = {}
    for i, c in enumerate(ws[2]):
        t = slug(propre(c.value))
        if t: titres[t] = i
    manquant = [n for n in ("code", "apparait-a", "question") if n not in titres]
    bonne = next((i for t, i in titres.items() if t.startswith("bonne")), None)
    if bonne is None: manquant.append("bonne reponse")
    if manquant:
        sys.exit("Onglet Quiz : colonne(s) introuvable(s) : %s. "
                 "Verifier la ligne 2 du tableur." % ", ".join(manquant))
    props = sorted(i for t, i in titres.items() if t.startswith("proposition"))
    if not props:
        sys.exit("Onglet Quiz : aucune colonne \"Proposition N\".")
    return titres["code"], titres["apparait-a"], titres["question"], props, bonne


quiz = {}
if "Quiz" in wb.sheetnames:
    ws = wb["Quiz"]
    cCode, cT, cQ, cProps, cBonne = colonnes_du_quiz(ws)
    for r in ws.iter_rows(min_row=3, values_only=True):
        def case(i): return propre(r[i]) if i < len(r) else ""
        c = case(cCode)
        t = en_secondes(case(cT))
        question = case(cQ)
        props = [case(i) for i in cProps if case(i)]
        if not (c and question and props): continue
        try: bonne = int(float(case(cBonne))) - 1
        except ValueError: bonne = 0
        quiz.setdefault(c, []).append({
            "t": t or 0, "question": question, "props": props,
            "bonne": max(0, min(bonne, len(props) - 1)),
        })
    for c in quiz:
        quiz[c].sort(key=lambda q: q["t"])

# ------------------------------------------------------------
# LES QUESTIONS BONUS
#
# Elles surgissent sans QR code, au milieu du parcours. Une seule tentative :
# qui repond juste du premier coup gagne un indice que les autres n'auront
# pas. On ne bloque jamais — une mauvaise reponse coute l'indice, pas la
# suite du jeu.
#
# C'est un ECRAN comme les autres, pas une fenetre qui se superpose. Sur un
# telephone tenu a bout de bras par quatre personnes, un ecran plein se lit ;
# une vignette qu'on peut fermer par megarde, non. Et il herite ainsi de
# toute la navigation deja eprouvee : retour, memoire de l'ecran quitte,
# bouton suivant.
# ------------------------------------------------------------
def colonnes_du_popquiz(ws):
    titres = {}
    for i, c in enumerate(ws[2]):
        t = slug(propre(c.value))
        if t: titres[t] = i
    props = sorted(i for t, i in titres.items() if t.startswith("proposition"))
    bonne = next((i for t, i in titres.items() if t.startswith("bonne")), None)
    indice = next((i for t, i in titres.items() if t.startswith("indice")), None)
    rate = next((i for t, i in titres.items() if t.startswith("message")), None)
    manque = [n for n in ("code", "moment", "question") if n not in titres]
    for nom, v in (("bonne reponse", bonne), ("indice gagne", indice),
                   ("message si faux", rate)):
        if v is None: manque.append(nom)
    if not props: manque.append("proposition 1")
    if manque:
        sys.exit("Onglet Pop quiz : colonne(s) introuvable(s) : %s."
                 % ", ".join(manque))
    return (titres["code"], titres["moment"], titres["question"],
            props, bonne, indice, rate)


popquiz = {}
if "Pop quiz" in wb.sheetnames:
    ws = wb["Pop quiz"]
    cC, cM, cQ, cP, cB, cI, cR = colonnes_du_popquiz(ws)
    for r in ws.iter_rows(min_row=3, values_only=True):
        def case(i): return propre(r[i]) if i < len(r) else ""
        c = case(cC)
        props = [case(i) for i in cP if case(i)]
        if not (c and case(cQ) and props): continue
        try: bonne = int(float(case(cB))) - 1
        except ValueError: bonne = 0
        popquiz[c] = {
            "moment": "sortie" if "sortie" in slug(case(cM)) else "scan",
            "question": case(cQ), "props": props,
            "bonne": max(0, min(bonne, len(props) - 1)),
            "indice": case(cI), "rate": case(cR),
        }

# ------------------------------------------------------------
# LES TROIS FINS DE L'ENQUETE
#
# Le joueur ecrit ses conclusions, et le jeu cherche dans sa phrase les
# idees attendues. Pas d'intelligence artificielle : le jugement porte sur
# des mots precis, et un test ecrit dans la page est instantane, gratuit,
# ne depend d'aucune cle et ne tombe pas en panne un dimanche a 15 h.
#
# C'est aussi, de toute facon, le filet qu'il faudrait ecrire DERRIERE une
# IA : trois heures d'enquete ne peuvent pas se terminer sur un ecran de
# chargement parce qu'un service repond mal.
#
# Les fins sont essayees de haut en bas, la derniere servant de defaut.
# ------------------------------------------------------------
denouements = []
if "Denouements" in wb.sheetnames:
    ws = wb["Denouements"]
    titres = {}
    for i, c in enumerate(ws[2]):
        t = slug(propre(c.value))
        if t: titres[t] = i
    manque = [n for n in ("rang", "nom", "mots-attendus", "mots-qui-disqualifient",
                          "titre-affiche", "texte-du-denouement") if n not in titres]
    if manque:
        sys.exit("Onglet Denouements : colonne(s) introuvable(s) : %s."
                 % ", ".join(manque))
    for r in ws.iter_rows(min_row=3, values_only=True):
        def case(i): return propre(r[i]) if i < len(r) else ""
        if not case(titres["nom"]): continue
        try: rang = int(float(case(titres["rang"])))
        except ValueError: rang = 99
        denouements.append({
            "rang": rang, "nom": case(titres["nom"]),
            "attendus": case(titres["mots-attendus"]),
            "interdits": case(titres["mots-qui-disqualifient"]),
            "titre": case(titres["titre-affiche"]),
            "texte": case(titres["texte-du-denouement"]),
        })
    denouements.sort(key=lambda d: d["rang"])
    if denouements and (denouements[-1]["attendus"] or denouements[-1]["interdits"]):
        sys.exit("Onglet Denouements : la derniere fin sert de defaut, elle ne "
                 "doit avoir ni mot attendu ni mot qui disqualifie. Sans elle, "
                 "une conclusion inattendue ne recevrait aucune reponse.")

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

# ------------------------------------------------------------
# LES PHOTOS DANS LES BORNES
#
# PHOTO : une image posee sur le premier ecran de la borne.
# GALERIE : plusieurs images qu'on fait defiler sur place.
#
# Elles vivent DANS le depot, comme les plans de chemin : quelques dizaines
# de kilo-octets chacune, c'est sans commune mesure avec une video, et ca
# evite de dependre d'un credit chez l'hebergeur.
# ------------------------------------------------------------
# etape -> (fichier, texte de remplacement, numero d'ecran du cahier)
PHOTO = {
 "E08": ("empreinte-renard.webp", "Une empreinte fraîche dans la boue", 3),
 "E12": ("appel-commissaire.webp", "Appel entrant", 1),
 # L'aveu de Greg, apres la video de la serre : la derniere piece au dossier.
 "E15": ("aveu-greg.webp", "L'aveu de Greg", 5),
}

# Les carrousels de photos : l'ecran ou ils apparaissent, le texte du
# bouton qui les ouvre, et les photos dans l'ordre.
GALERIE = {
 "E11": {"ecran": 1, "bouton": "Voir le contenu du sac",
         "photos": [("sac-%d.webp" % i, "Objet trouvé dans le sac") for i in range(1, 7)]},
 # Les images que le commissaire envoie juste apres son appel.
 "E12": {"ecran": 3, "bouton": "Voir les images",
         "photos": [("commissaire-%d.webp" % i, "Image envoyée par le commissaire")
                    for i in range(1, 5)]},
}

# ------------------------------------------------------------
# LE NOMBRE CACHE DANS LE SAC
#
# Les objets du sac portent des chiffres. Lus dans l'ordre des photos, ils
# donnent le code de la serre — mais on ne le dit pas au joueur a ce
# moment-la : il note un nombre sans savoir a quoi il sert, et c'est ce
# silence qui fait l'effet trois bornes plus loin.
#
# etape -> (le nombre, l'etape ou il s'utilise)
# ------------------------------------------------------------
CODE_CACHE  = {"E11": "5824"}
CODE_DEMANDE = {"E14": "5824"}

# ------------------------------------------------------------
# LES BORNES OU L'ON CHERCHE AVANT DE SAVOIR
#
# Sur ces bornes, la lettre s'affichait des le scan : le joueur recevait la
# reponse avant d'avoir leve les yeux, et l'enigme posee juste au-dessus
# devenait decorative.
#
# La lettre passe donc derriere une question. Qui a trouve repond oui et
# continue ; qui n'a pas trouve repond non et obtient la lettre. On ne
# bloque personne : un groupe coince devant un enclos de loups un dimanche
# de novembre abandonne, il ne cherche pas plus longtemps.
# ------------------------------------------------------------
CONFIRMATION_INDICE = {"E04", "E13"}

# Sur ces bornes, la lettre n'est PAS dans le decor : le groupe observe une
# saynette, et la borne lui donne la lettre a la fin, d'un bouton. On ne lui
# demande pas s'il l'a trouvee, puisqu'il n'y a rien a trouver.
LETTRE_DONNEE = {"E13"}

# Le coup de pouce : un bouton « Demander un indice » sous la consigne de
# l'ecran 1, qui devoile une phrase d'aide. Il ne donne pas la reponse.
COUP_DE_POUCE = {
    "E04": "N'hésitez pas à lever la tête pour chercher votre objet mystère.",
}

# LES QUESTIONS DE REFLEXION. Une question fermee, posee avant « Ou aller
# ensuite », pour faire avancer le raisonnement du groupe. Il n'y a pas de
# mauvaise reponse qui coute quelque chose : chaque reponse a son
# explication, ecrite d'avance. Elle s'affiche donc meme sans reseau.
REFLEXION = {
    "E08": {
        "question": "À votre avis, Isabelle aurait-elle pu entrer dans l'enclos "
                    "des loups et se faire dévorer ?",
        "oui": ("Très peu probable",
                "On comprend le frisson, mais c'est très improbable. Un soigneur "
                "n'entre jamais seul dans l'enclos des loups. Et le loup n'a rien "
                "du monstre des contes : "
                "il craint l'homme et l'évite. En Europe, les attaques de loups sur "
                "des humains sont rarissimes depuis plus d'un siècle. D'ailleurs, "
                "l'empreinte que vous venez d'identifier n'est pas celle d'un loup…"),
        "non": ("Bien vu",
                "En effet. Un soigneur n'entre jamais seul dans l'enclos des loups. "
                "Le loup, lui, craint "
                "l'homme et l'évite : en Europe, les attaques de loups sur des "
                "humains sont rarissimes depuis plus d'un siècle. Et l'empreinte que "
                "vous venez d'identifier n'est pas celle d'un loup…"),
    },
}

# LE MOT DES QUATRE LETTRES. Apres la derniere lettre de chaque sens, le
# groupe ecrit le mot qu'elles forment. Juste : on lui revele le dernier
# lieu. Faux deux fois : on lui donne le mot, et le lieu quand meme. Le
# bouton du scanner n'apparait qu'ensuite, pour qu'il ne parte pas sans.
MOT_FINAL = {
    "mot": "IRIS",
    "ecrans": {("E13", "A"), ("E08", "B")},
    "trouve": "Félicitations, vous avez trouvé le bon mot ! Il ne vous reste plus "
              "qu'à trouver l'endroit où il vous mène.",
    # A la place de « trouve », quand le jeu a du donner le mot.
    "donne": "Il ne vous reste plus qu'à trouver l'endroit où il vous mène.",
    # Derriere « Demander un indice » : le groupe cherche d'abord le lieu.
    "indice": "Rendez-vous au Jardin des Iris.",
}

# ------------------------------------------------------------
# LE TEMPS DE REPONSE DU QUIZ
#
# Une question apparait, le groupe a ce nombre de secondes pour repondre,
# puis elle se verrouille et montre la bonne reponse. Elle reste affichee
# jusqu'a l'arrivee de la suivante, qui la remplace.
#
# Ce compte a rebours suit le temps de la VIDEO, pas l'horloge du telephone.
# Sur le reseau d'un parc, une video qui se recharge aurait sinon mange les
# dix secondes sans que personne ait rien lu.
#
# Les minutes du cahier marquent le DEBUT du son a reconnaitre. Le compte a
# rebours part donc pendant que le son joue : treize secondes couvrent le son
# lui-meme, la lecture des quatre propositions, et l'accord du groupe.
#
# Consequence a surveiller dans le cahier : deux questions separees de moins
# de SECONDES_POUR_REPONDRE + 3 se coupent la parole. verifier-le-cahier.py
# le signale, et il lit cette valeur-ci pour ne jamais en annoncer une autre.
# ------------------------------------------------------------
SECONDES_POUR_REPONDRE = 13

# Combien de temps le verdict reste affiche, une fois la reponse donnee ou
# le delai ecoule. Passe ce temps la question s'efface, et l'ecran invite a
# ecouter le son suivant : une question morte qui traine quarante secondes
# sous une video detourne l'oreille de ce qu'il y a a entendre.
#
# Ce compte part de la REPONSE, pas du depart de la question. A zero, la
# question disparaitrait pile a la treizieme seconde, et celui qui repond a
# la douzieme verrait son verdict une seconde : il ne saurait meme pas s'il
# a eu juste.
SECONDES_DE_VERDICT = 4
# ------------------------------------------------------------
# LE TITRE AFFICHE EN HAUT DE LA BORNE
#
# Le nom du cahier sert a DEUX choses qui n'ont rien a voir : le titre que
# lit le joueur, et l'identite de la borne dans la base de donnees, celle
# qui relie un passage a un point du parc.
#
# Les deux bornes de Greg doivent s'appeler « GREG » a l'ecran — « version
# sens A » sur un panneau, ca fait tache. Mais elles ne peuvent pas porter
# le meme nom dans la base : ce sont deux endroits differents du parc, et
# le tableau de bord ne saurait plus lequel un groupe vient de passer.
#
# Le cahier garde donc le nom technique, unique, et cette liste donne le
# titre vu par le joueur. Changer un titre ici ne touche ni la base ni les
# QR codes deja imprimes.
# ------------------------------------------------------------
TITRE_BORNE = {
 "E09": "GREG",
 "E16": "GREG",
 "E11": "Indice : le sac perdu",
 "E14": "LOUIS, LE BOTANISTE",
}

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
MEDIA_BASE = "https://sanctuaire-brumes.b-cdn.net"

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
 # Le commissaire et la passante portent un nom neuf (« -2- ») : remplaces
 # sous leur ancien nom, ils calaient en cours de lecture. Un fichier
 # remplace a l'identique peut etre servi par morceaux, anciens et nouveaux
 # melanges, par le cache et la replication de l'hebergeur. Un nom neuf,
 # c'est un cache neuf. A retenir pour toute nouvelle version d'une video.
 "E01": "le-commissaire-jean-2-79swb7.mp4",
 "E02": "la-collegue-soigneuse-8bdz93.mp4",
 "E03": "la-videosurveillance-yag6qs.mp4",
 "E05": "la-passante-2-qri7tr.mp4",
 "E06": "quiz-animalier-2-hwqbca.mp4",   # version raccourcie, 6 questions
 "E07": "le-veterinaire-66ckyk-2.mp4",
 "E09": "greg-sens-a-sj7kmm.mp4",
 "E10": "bill-t87isj-2.mp4",
 # L'appel du commissaire n'est pas une video : c'est l'audio que joue
 # le bouton « Décrocher ».
 "E12": "appel-du-commissaire-bm7fpb.mp3",
 "E14": "le-botaniste-acanpa-2.mp4",
 "E15": "la-serre-4.mp4",
 # Greg ne dit pas autre chose selon le sens par lequel on arrive : les
 # deux bornes portent la meme legende et renvoient toutes deux vers
 # Bill. Une seule video, donc, servie aux deux endroits. Ce ne sont pas
 # les memes bornes pour autant : chacune a son QR code, dans un coin
 # different du parc, pour que chaque sens croise Greg au bon moment.
 "E16": "greg-sens-a-sj7kmm.mp4",
}

POSTERS = {}

# ------------------------------------------------------------
# LES PLANS QUI MONTRENT LE CHEMIN
#
# Un joueur qui sort d'une borne doit trouver la suivante dans un parc de
# vingt-cinq hectares. La phrase ("rendez-vous au bureau des soigneurs")
# suppose qu'il sait ou c'est ; le plan le lui montre.
#
# La cle est le code de la borne ET le sens, parce que le chemin n'est pas
# le meme selon le cote par lequel on tourne. Une borne absente de cette
# liste garde son emplacement vide, sans rien casser.
#
# Contrairement aux videos, ces images vivent DANS le depot : quelques
# dizaines de kilo-octets chacune, servies une fois puis gardees en memoire
# par le telephone.
# ------------------------------------------------------------
# Un plan par TRAJET, pas par ecran : de l'enclos des loups a la passante,
# le chemin est le meme dans les deux sens, et une seule image le sert.
# Son nom se deduit du trajet : chemin-e04-vers-e05.webp. Chaque ecran
# « Ou aller ensuite » le demande ; s'il n'est pas encore dans assets/img/,
# l'image se retire d'elle-meme (onerror), sans cadre casse. Deposer un
# plan suffit donc a le faire apparaitre, sans refabriquer les pages.
def nom_du_plan(depart, arrivee):
    return "chemin-%s-vers-%s.webp" % (depart.lower(), arrivee.lower())

CHEMINS = {}   # exceptions eventuelles : (code, sens) -> fichier


# L'etape ou le joueur rend ses conclusions.
CONCLUSIONS = "E15"

# Les partenaires, pour le texte de remplacement de leur planche de logos
# (assets/img/partenaires.webp) : c'est ce que lit un lecteur d'ecran.
PARTENAIRES = ("Les Pouss'murs, Melfor, Maisons Clever'Hom, Mercedes-Benz Kroely, Fimaris, Olivia's Garden, Xperience Park, Aveline, Costco Wholesale, Énergie de l'Est, L'Alsace, JDS")

NON_CONSTRUIT   = {}

def e(t): return html.escape(t, quote=True)

# ------------------------------------------------------------
# LES TITRES D'ECRAN VUS PAR LE JOUEUR
#
# Les etiquettes du cahier ("3. Texte ou epreuve", "1. Accueil apres le
# scan") sont des reperes de travail : numerotes, sans accents, ecrits pour
# celle qui remplit le tableau. Elles s'affichaient telles quelles a des
# gens qui ont paye.
#
# Le cahier garde donc ses etiquettes, c'est l'outil de travail. Seules
# celles listees ici apparaissent a l'ecran, reecrites pour le joueur ;
# toutes les autres disparaissent, et l'ecran commence directement par son
# contenu.
#
# La cle passe par slug(), donc un accent ou une majuscule de travers dans
# le cahier ne fait pas manquer la correspondance.
# ------------------------------------------------------------
TITRES = {
 "4-ou-aller-ensuite": "Où aller ensuite",
}

def titre_joueur(libelle):
    return TITRES.get(slug(libelle), "")


def fusionner_legendes(code, lg):
    """La legende d'un media ("Mathilde, soigneuse animaliere") occupait un
    ecran entier : le joueur devait appuyer sur Suivant pour lire une ligne,
    puis encore une fois pour continuer. Elle devient une signature sous la
    video, sur le meme ecran. Le texte est conserve, le clic disparait."""
    def est_le_media(x):
        if "egende" in x["ecran"]: return False
        if re.search(r"vid[ée]o|audio", x["ecran"], re.I): return True
        return code in APPEL_AUDIO and x["n"] == 1   # la borne de l'appel

    medias = [x for x in lg if est_le_media(x)]
    restant = []
    for x in lg:
        if "egende" in x["ecran"] and x["texte"] and medias:
            cible = next((m for m in medias if m["sens"] == x["sens"]), medias[0])
            cible["legende"] = x["texte"]
            continue                    # l'ecran disparait
        restant.append(x)
    return restant


def ecran_vide(code, etape, lg):
    """Un ecran qui n'aurait rien a montrer.

    Le cahier met "/" dans une case pour dire « rien ici ». Le generateur
    n'ecrivait alors pas de texte, mais fabriquait quand meme l'ecran : le
    joueur tombait sur une carte vide avec deux boutons, et devait appuyer
    sur Suivant pour rien. On ne le fabrique plus.

    Un ecran qui porte un media, une epreuve, une legende, un plan ou une
    note de chantier a du contenu, meme sans texte.
    """
    if lg["texte"] and lg["texte"] != "/":            return False
    if lg.get("legende"):                             return False
    if re.search(r"vid[ée]o|audio", lg["ecran"], re.I): return False
    if "aller ensuite" in lg["ecran"].lower():        return False
    if code in APPEL_AUDIO and lg["n"] == 1:          return False
    if code in EPREUVE_REPONSE and lg["n"] == 3:      return False
    if code in NON_CONSTRUIT and lg["n"] == 3:        return False
    if etape["lettre"] and etape["lettre"] not in ("-", "/") and lg["n"] == 1 \
       and code not in EPREUVE_REPONSE and code not in CONFIRMATION_INDICE \
       and code not in quiz:
        return False
    return True


def bloc_confirmation(lettre, donnee=False):
    """L'ecran qui demande au joueur s'il a trouve, avant de lui dire.

    donnee : la lettre n'est pas dans le decor, on la donne d'un bouton."""
    if donnee:
        choix = ['  <p>Vous avez bien observé la scène ? L\'indice est à vous.</p>',
                 '  <div data-indice-choix>',
                 '    <button data-indice-non>Donnez-moi l\'indice</button>',
                 '  </div>']
    else:
        choix = ['  <p>Avez-vous bien trouvé l\'indice caché ?</p>',
                 '  <div data-indice-choix>',
                 '    <button data-suivant>Oui</button>',
                 '    <button class="btn-secondary" data-indice-non>Non, montrez-le-moi</button>',
                 '  </div>']
    return "\n".join([
        '<section class="ecran card" data-confirmation hidden>'] + choix + [
        '  <div data-indice-revele hidden>',
        '    <div class="card indice">',
        '      <div class="eyebrow">Vous avez trouvé une lettre</div>',
        '      <p class="lettre">%s</p>' % e(lettre),
        '    </div>',
        '    <button data-suivant>Suivant</button>',
        '  </div>',
        '  <button class="btn-secondary" data-retour>Revenir en arrière</button>',
        '</section>',
    ])


def bloc_quiz(code, lettre):
    """Les questions affichees SOUS la video, pendant qu'elle tourne.

    Elles sont toutes dans la page des le depart, mais cachees : etape.js
    n'en montre qu'une a la fois, celle que la video vient d'atteindre. La
    suivante remplace la precedente.

    Chaque question a SECONDES_POUR_REPONDRE secondes. Passe ce delai elle
    se verrouille et montre la bonne reponse : un groupe qui n'a pas eu le
    temps perd le point, mais apprend quand meme quelque chose. C'est un
    quiz pedagogique, le silence serait une occasion perdue.

    Le verdict reste SECONDES_DE_VERDICT secondes, puis la question
    s'efface et l'ecran invite a ecouter la suivante.
    """
    h = ['<div class="quiz" data-quiz data-delai="%d" data-verdict-delai="%d" hidden>'
         % (SECONDES_POUR_REPONDRE, SECONDES_DE_VERDICT)]
    # Entre deux questions, l'ecran ne doit pas etre vide : un groupe qui ne
    # voit plus rien se demande si son telephone a laché, au lieu d'ecouter.
    h.append('  <p class="quiz-attente" data-attente hidden>'
             'Écoutez bien, une question va suivre.</p>')
    for i, q in enumerate(quiz[code]):
        h.append('  <div class="quiz-question" data-question data-t="%d" '
                 'data-bonne="%d" hidden>' % (q["t"], q["bonne"]))
        h.append('    <div class="quiz-numero">Question %d sur %d</div>'
                 % (i + 1, len(quiz[code])))
        h.append('    <p class="quiz-intitule">%s</p>' % e(q["question"]))
        # Le compte a rebours. La barre se vide, le nombre dit combien il
        # reste : la barre se lit sans lire, le nombre leve le doute sur un
        # ecran de telephone au soleil.
        h.append('    <div class="quiz-chrono" data-chrono>')
        h.append('      <div class="quiz-chrono-barre"><span></span></div>')
        h.append('      <div class="quiz-chrono-reste" data-reste>%d s</div>'
                 % SECONDES_POUR_REPONDRE)
        h.append('    </div>')
        for n, prop in enumerate(q["props"]):
            h.append('    <button class="quiz-prop" data-prop="%d">%s</button>'
                     % (n, e(prop)))
        h.append('    <p class="quiz-verdict" data-verdict hidden></p>')
        h.append('  </div>')

    # Le bilan ne donne plus que le score. La lettre a son propre ecran,
    # apres « Suivant » (voir bloc_lettre_du_quiz) : posee sous les
    # questions, elle se voyait des la fin de la video, et elle n'arrivait
    # jamais quand la video refusait de se charger.
    h.append('  <div class="quiz-bilan" data-bilan hidden>')
    h.append('    <p data-score></p>')
    h.append('  </div>')
    h.append('</div>')
    return "\n".join(h)


def bloc_reflexion(code):
    """La question de reflexion : Oui ou Non, puis l'explication de la
    reponse choisie. « Suivant » n'apparait qu'apres la reponse, comme pour
    les questions bonus : sinon on la sauterait sans la lire."""
    r = REFLEXION[code]
    h = ['<section class="ecran card popquiz" data-reflexion hidden>',
         '  <div class="ecran-titre">Votre avis d\'enquêteur</div>',
         '  <p class="popquiz-question">%s</p>' % e(r["question"]),
         '  <div data-reflexion-choix>',
         '    <button class="quiz-prop" data-reflexion-repondre="oui">Oui</button>',
         '    <button class="quiz-prop" data-reflexion-repondre="non">Non</button>',
         '  </div>']
    for cle in ("oui", "non"):
        titre, texte = r[cle]
        h += ['  <div class="card indice" data-reflexion-reponse="%s" hidden>' % cle,
              '    <div class="eyebrow">%s</div>' % e(titre),
              '    <p>%s</p>' % e(texte),
              '  </div>']
    h += ['  <button data-suivant data-reflexion-suivant hidden>Suivant</button>',
          '  <button class="btn-secondary" data-retour>Revenir en arrière</button>',
          '</section>']
    return "\n".join(h)


def bloc_lettre_du_quiz(lettre):
    """L'ecran qui suit le quiz : la lettre, quel que soit le score.

    Le quiz fait regarder la video et apprendre quelque chose ; il n'arrete
    pas l'enquete de ceux qui ont mal repondu, ni de ceux dont la video ne
    s'est pas chargee, ni de ceux qui l'ont passee."""
    return "\n".join([
        '<section class="ecran card" hidden>',
        '  <div class="card indice">',
        '    <div class="eyebrow">Vous avez trouvé une lettre</div>',
        '    <p class="lettre">%s</p>' % e(lettre),
        '  </div>',
        '  <button data-suivant>Suivant</button>',
        '  <button class="btn-secondary" data-retour>Revenir en arrière</button>',
        '</section>',
    ])


# L'invitation qui suit le denouement, sur la borne de la serre.
PHOTOCALL = {
    "titre": "Un dernier cliché pour le dossier",
    "textes": [
        "Avant de quitter la serre, prenez-vous en photo devant le photocall, "
        "et postez-la sur Instagram en identifiant @pomelolab.",
        "Chaque jour, la meilleure photo est sélectionnée et reçoit un cadeau surprise.",
    ],
    "bouton": "Ouvrir Instagram",
    "lien": "https://www.instagram.com/pomelolab/",
}

# Le titre « Question bonus » est deja ecrit en grand juste au-dessus.
CONSIGNE_BONUS = ("Répondez correctement à la question suivante pour "
                  "gagner un indice supplémentaire.")


def bloc_popquiz(code):
    """L'ecran d'une question bonus."""
    q = popquiz[code]
    h = ['<section class="ecran card popquiz" data-popquiz data-bonne="%d" hidden>'
         % q["bonne"],
         '  <div class="ecran-titre">Question bonus</div>',
         '  <p class="popquiz-consigne">%s</p>' % e(CONSIGNE_BONUS),
         '  <p class="popquiz-question">%s</p>' % e(q["question"])]
    h.append('  <div data-bonus-choix>')
    for n, prop in enumerate(q["props"]):
        h.append('    <button class="quiz-prop" data-bonus-prop="%d">%s</button>'
                 % (n, e(prop)))
    h.append('  </div>')
    # Les deux issues sont ecrites d'avance dans la page : le telephone n'a
    # rien a demander a personne au moment de repondre, et la borne reste
    # juste meme si le reseau du parc tombe entre-temps.
    h.append('  <div class="card indice" data-bonus-gagne hidden>')
    h.append('    <p>%s</p>' % e(q["indice"]))
    h.append('  </div>')
    h.append('  <p class="quiz-verdict quiz-faux" data-bonus-rate hidden>%s</p>'
             % e(q["rate"]))
    h.append('  <button data-suivant data-bonus-suivant hidden>Continuer</button>')
    h.append('  <button class="btn-secondary" data-retour>Revenir en arrière</button>')
    h.append('</section>')
    return "\n".join(h)


def bloc_ecran(etape, lg, dernier, sens_attr):
    """Un ecran = une carte. sens_attr vaut None, 'A' ou 'B'."""
    c, lib, txt = etape["code"], lg["ecran"], lg["texte"]
    est_media  = bool(re.search(r"vid[ée]o|audio", lib, re.I))
    est_sortie = "aller ensuite" in lib.lower()
    attr = ' data-sens="%s"' % sens_attr if sens_attr else ""
    h = ['<section class="ecran card"%s hidden>' % attr]
    titre = titre_joueur(lib)
    if titre:
        h.append('  <div class="ecran-titre">%s</div>' % e(titre))
    else:
        # L'etiquette du cahier reste en commentaire : elle sert a retrouver
        # la ligne du tableur quand on relit une page.
        h.append('  <!-- cahier : %s -->' % lib.replace("--", "—"))

    if est_media:
        fichier = MEDIAS.get(c)
        poster  = POSTERS.get(c, "")
        if fichier and MEDIA_BASE:
            # preload="none" : rien ne se telecharge tant que le joueur n'a pas
            # appuye sur lecture. Sur le reseau mobile d'un parc, c'est la
            # difference entre une page qui s'ouvre et une page qui rame.
            # Pas de "playsinline" : cet attribut demande justement a iOS de
            # rester dans la page. Sans lui, la video part d'elle-meme en
            # plein ecran sur iPhone, et etape.js s'en charge sur Android.
            # La video d'un quiz ne part PAS en plein ecran : elle cacherait
            # les questions, qui sont tout l'interet de l'ecran. Elle est
            # filmee en paysage, donc "playsinline" pour qu'iOS la laisse
            # dans la page, et un cadre 16/9 au lieu du 9/16 des temoignages.
            if c in quiz:
                # Le plein ecran cacherait les questions : on le dit, et
                # etape.js le refuse (controlsList le retire sur Android).
                h.append('  <p class="consigne-scan consigne-video">Ne mettez pas la vidéo en plein écran : '
                         'les questions apparaissent juste en dessous.</p>')
                h.append('  <video controls playsinline preload="none" '
                         'controlslist="nofullscreen" disablepictureinpicture '
                         'class="video-paysage" data-quiz-video poster="%s">'
                         % e(poster))
            else:
                h.append('  <video controls preload="none" poster="%s">'
                         % e(poster))
            h.append('    <source src="%s/%s" type="video/mp4">' % (MEDIA_BASE, e(fichier)))
            h.append('    <p>Votre navigateur ne lit pas cette vidéo. '
                     'Prévenez un membre de l\'équipe sur place.</p>')
            h.append('  </video>')
        else:
            h.append('  <!-- Vidéo pas encore intégrée : ajouter le fichier dans')
            h.append('       MEDIAS (contenu/fabriquer-les-pages.py) et renseigner')
            h.append('       MEDIA_BASE. Ne jamais mettre la vidéo dans le dépôt. -->')
            cls = ' class="video-paysage" data-quiz-video' if c in quiz else ''
            h.append('  <video controls playsinline%s poster="">'
                     '<source src="" type="video/mp4">' % cls)
            h.append('  Votre navigateur ne supporte pas la vidéo.</video>')
    if c in APPEL_AUDIO and lg["n"] == 1:
        h.append('  <button id="decrocher" class="btn-appel">Décrocher</button>')
        h.append('  <div id="blocAppel" hidden>')
        fichier = MEDIAS.get(c)
        if fichier and MEDIA_BASE:
            # preload="none" : le son ne se telecharge qu'au moment ou le
            # joueur decroche, comme les videos.
            h.append('    <audio id="audioAppel" controls preload="none">'
                     '<source src="%s/%s" type="audio/mpeg"></audio>' % (MEDIA_BASE, e(fichier)))
        else:
            h.append('    <!-- Audio pas encore integre : ajouter le fichier dans MEDIAS -->')
            h.append('    <audio id="audioAppel" controls><source src="" type="audio/mpeg"></audio>')
        h.append('  </div>')

    if c in PHOTO and lg["n"] == PHOTO[c][2]:
        fichier, texte, _ = PHOTO[c]
        h.append('  <img class="photo-borne" src="../assets/img/%s" alt="%s">'
                 % (e(fichier), e(texte)))

    if lg.get("legende"):
        h.append('  <p class="witness-name">%s</p>' % e(lg["legende"]))

    if c in quiz and est_media:
        h.append(bloc_quiz(c, etape["lettre"]))

    galerie = GALERIE.get(c) if c in GALERIE and lg["n"] == GALERIE[c]["ecran"] else None
    # Le texte de l'ecran AVANT le carrousel : il dit ce qu'on va voir. Pose
    # dessous, il arrivait apres le bouton qui l'annoncait.
    if galerie and txt and txt != "/":
        for p in [x.strip() for x in txt.split("\n") if x.strip()]:
            h.append('  <p>%s</p>' % e(p))
        txt = ""
    if galerie:
        # Les photos ne s'affichent qu'au clic sur « Voir » : l'ecran reste
        # lisible a l'arrivee, et rien ne se telecharge tant que le groupe
        # n'a pas decide de regarder.
        h.append('  <div class="galerie" data-galerie>')
        h.append('    <button data-galerie-ouvrir>%s</button>' % e(galerie["bouton"]))
        h.append('    <div data-galerie-vue hidden>')
        for i, (fichier, texte) in enumerate(galerie["photos"]):
            h.append('      <img class="photo-borne" loading="lazy" '
                     'data-galerie-photo src="../assets/img/%s" alt="%s"%s>'
                     % (e(fichier), e(texte), "" if i == 0 else " hidden"))
        h.append('      <div class="galerie-barre">')
        # « Précédente » et « Suivante », au feminin, avec leur fleche : un
        # bouton « Suivant » ici se confondait avec celui qui quitte l'ecran.
        h.append('        <button class="btn-secondary" data-galerie-prec aria-label="Image précédente">‹ Précédente</button>')
        h.append('        <span class="galerie-compte" data-galerie-compte></span>')
        h.append('        <button class="btn-secondary" data-galerie-suiv aria-label="Image suivante">Suivante ›</button>')
        h.append('      </div>')
        h.append('    </div>')
        h.append('  </div>')

    if txt and txt != "/":
        for p in [x.strip() for x in txt.split("\n") if x.strip()]:
            h.append('  <p>%s</p>' % e(p))

    if c in EPREUVE_REPONSE and lg["n"] == 3:
        rep, lettre = EPREUVE_REPONSE[c]
        h.append('  <input type="text" id="reponse" inputmode="numeric" placeholder="Votre réponse">')
        h.append('  <button id="valider">Valider</button>')
        h.append('  <p class="quiz-verdict quiz-faux" id="aCote" hidden></p>')
        h.append('  <div id="resultat" class="card indice" hidden>')
        h.append('    <div class="eyebrow" id="resultatTitre">Vous avez trouvé une lettre</div>')
        h.append('    <p class="lettre">%s</p>' % e(lettre))
        h.append('  </div>')
    elif (etape["lettre"] and etape["lettre"] not in ("-", "/") and lg["n"] == 1
          and c not in EPREUVE_REPONSE and c not in CONFIRMATION_INDICE
          and c not in quiz):
        h.append('  <div class="card indice">')
        h.append('    <div class="eyebrow">Vous avez trouvé une lettre</div>')
        h.append('    <p class="lettre">%s</p>' % e(etape["lettre"]))
        h.append('  </div>')

    if c in CODE_CACHE and lg["n"] == 3:
        h.append('  <input type="text" id="codeTrouve" inputmode="numeric" '
                 'maxlength="4" placeholder="4 chiffres">')
        h.append('  <button id="validerCode">Valider</button>')
        h.append('  <p class="quiz-verdict quiz-faux" id="codeACote" hidden></p>')
        h.append('  <div id="codeJuste" class="card indice" hidden>')
        h.append('    <div class="eyebrow">Notez ce nombre</div>')
        h.append('    <p class="lettre">%s</p>' % e(CODE_CACHE[c]))
        h.append('    <p>Vous ne savez pas encore à quoi il sert. Gardez-le.</p>')
        h.append('  </div>')

    if c in CODE_DEMANDE and lg["n"] == 3:
        h.append('  <input type="text" id="codeSerre" inputmode="numeric" '
                 'maxlength="4" placeholder="4 chiffres">')
        h.append('  <button id="validerSerre">Ouvrir</button>')
        h.append('  <p class="quiz-verdict quiz-faux" id="serreACote" hidden></p>')
        # Personne ne doit rester dehors parce qu'un papier s'est envole.
        h.append('  <button class="btn-lien" id="codePerdu">J\'ai perdu le code</button>')
        h.append('  <div id="serreOuverte" class="card indice" hidden>')
        h.append('    <div class="eyebrow">La porte s\'ouvre</div>')
        h.append('    <p>Entrez dans la serre.</p>')
        h.append('  </div>')

    if c == CONCLUSIONS and lg["n"] == 3 and denouements:
        h.append('  <textarea id="conclusions" rows="6" '
                 'placeholder="Racontez ce qui est arrivé à Isabelle."></textarea>')
        h.append('  <button id="validerConclusions">Rendre mon enquête</button>')
        h.append('  <p class="quiz-verdict quiz-faux" id="conclusionsVides" hidden>'
                 'Écrivez quelques mots avant de rendre votre enquête.</p>')
        for i, fin in enumerate(denouements):
            h.append('  <div class="card indice denouement" data-denouement="%s" hidden>'
                     % e(fin["nom"]))
            h.append('    <div class="eyebrow">%s</div>' % e(fin["titre"]))
            for par in [x.strip() for x in fin["texte"].split("\n") if x.strip()]:
                h.append('    <p>%s</p>' % e(par))
            h.append('  </div>')
        # Pour tous les groupes, quelle que soit leur fin : la photo devant
        # le photocall de la serre. Cachee jusqu'au verdict.
        h.append('  <div class="card photocall" data-photocall hidden>')
        h.append('    <div class="eyebrow">%s</div>' % e(PHOTOCALL["titre"]))
        for par in PHOTOCALL["textes"]:
            h.append('    <p>%s</p>' % e(par))
        h.append('    <a class="btn" href="%s" target="_blank" rel="noopener">%s</a>'
                 % (e(PHOTOCALL["lien"]), e(PHOTOCALL["bouton"])))
        h.append('  </div>')

    if c in NON_CONSTRUIT and lg["n"] == 3:
        h.append('  <!-- A CONSTRUIRE : %s -->' % NON_CONSTRUIT[c])
        h.append('  <p class="a-construire">%s</p>' % e(NON_CONSTRUIT[c]))

    if est_sortie:
        suite = etape.get("suite" + sens_attr) if sens_attr else None
        plan = CHEMINS.get((c, sens_attr)) or (nom_du_plan(c, suite) if suite else None)
        if plan:
            # loading="lazy" : le plan ne se telecharge qu'en arrivant a cet
            # ecran, pas au chargement de la borne. onerror : pas encore
            # depose, il se retire au lieu d'afficher une image cassee.
            h.append('  <img class="plan-chemin" loading="lazy" src="../assets/img/%s"'
                     % e(plan))
            h.append('       alt="Plan du parc : le chemin à suivre jusqu\'à la borne suivante"'
                     ' onerror="this.remove()">')

    if c in COUP_DE_POUCE and lg["n"] == 1:
        h.append('  <div data-coup-de-pouce>')
        h.append('    <button class="btn-secondary" data-coup-de-pouce-ouvrir>Demander un indice</button>')
        h.append('    <p class="card indice" data-coup-de-pouce-texte hidden>%s</p>' % e(COUP_DE_POUCE[c]))
        h.append('  </div>')

    mot_final = est_sortie and (c, sens_attr) in MOT_FINAL["ecrans"]
    if mot_final:
        h.append('  <div data-mot-final data-mot="%s">' % e(MOT_FINAL["mot"]))
        h.append('    <label for="motFinal">Le mot formé par vos 4 lettres</label>')
        h.append('    <input type="text" id="motFinal" autocomplete="off" autocapitalize="characters" spellcheck="false">')
        h.append('    <button id="validerMot">Valider</button>')
        h.append('    <p class="quiz-verdict quiz-faux" data-mot-faux hidden></p>')
        h.append('    <div class="card indice" data-mot-trouve hidden>')
        h.append('      <p data-mot-bravo data-donne="%s">%s</p>'
                 % (e(MOT_FINAL["donne"]), e(MOT_FINAL["trouve"])))
        h.append('      <div data-coup-de-pouce>')
        h.append('        <button class="btn-secondary" data-coup-de-pouce-ouvrir>Demander un indice</button>')
        h.append('        <p class="indice-lieu" data-coup-de-pouce-texte hidden>%s</p>' % e(MOT_FINAL["indice"]))
        h.append('      </div>')
        h.append('    </div>')
        h.append('  </div>')

    if lg["rem"]:
        h.append('  <!-- Note du cahier de contenu : %s -->' % lg["rem"].replace("--", "—"))

    if dernier:
        if mot_final:
            # Le scanner attend le mot : parti sans lui, le groupe ne saurait
            # pas ou aller.
            h.append('  <div data-apres-mot hidden>')
        if lg.get("lien"):
            # Le lien n'est PAS un bouton offert au joueur : l'enquete ne doit
            # pas se derouler au clic depuis un canape. Seul le scan du QR code
            # de la borne suivante ouvre la page. etape.js ne revele ce lien
            # qu'aux codes de test, pour que l'equipe puisse repeter le
            # parcours sans courir dans le parc.
            h.append('  <p class="consigne-scan">Rendez-vous sur place, puis scannez le QR code de la borne avec ce bouton.</p>')
            # Le scan se fait depuis la page, pas avec l'appareil photo : la
            # borne suivante s'ouvre ainsi dans le meme navigateur, celui qui
            # garde la partie en memoire. Voir assets/js/scanner.js.
            h.append('  <button data-scanner>Scanner le QR code</button>')
            h.append('  <a href="%s" class="btn btn-test" data-lien-test hidden>Raccourci de test</a>' % e(lg["lien"]))
            if mot_final:
                h.append('  </div>')
        else:
            # La derniere page du jeu : on remercie, et on remercie les
            # partenaires. Leurs logos ont leur plaque claire (style.css).
            h.append('  <p class="ecran-titre">Merci d\'avoir mené l\'enquête</p>')
            h.append('  <div class="partenaires">')
            h.append('    <div class="partenaires-titre">Merci à nos partenaires</div>')
            h.append('    <div class="partenaires-plaque"><img src="../assets/img/partenaires.webp" '
                     'loading="lazy" alt="%s"></div>' % e(PARTENAIRES))
            h.append('  </div>')
        # L'ecran de sortie n'avait aucun bouton de retour. C'est pourtant
        # celui ou le joueur reste le plus longtemps, puisqu'il y lit son
        # chemin : une fois arrive la, plus moyen de revoir le temoignage
        # sans passer par le bouton « precedent » du telephone.
        h.append('  <button class="btn-secondary" data-retour>Revenir en arrière</button>')
    else:
        # Sur l'ecran d'un quiz, "Suivant" est cache au depart. Pose sous la
        # premiere question, il invitait a sauter le quiz avant de l'avoir vu.
        # etape.js le rend des que le quiz est fini, et aussi des que la video
        # refuse de se charger : une video muette ne doit jamais enfermer un
        # groupe sur une borne.
        if c in quiz and est_media:
            h.append('  <button data-suivant data-quiz-suivant hidden>Suivant</button>')
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
<body data-borne="{borne}" data-etape="{code}" data-racine="../"
      data-prec-A="{precA}" data-prec-B="{precB}">

<div class="wrap">
  <div class="timer" id="timer">Chargement du chrono...</div>
  <!-- La progression du groupe. Les attributs portent le NUMERO de l'etape
       dans chaque sens ; etape.js remplit la barre selon le sens du groupe,
       et retire le bloc sur une borne qui n'appartient pas a ce parcours. -->
  <div class="progression" id="position" role="progressbar"
       data-A="{posA}" data-B="{posB}" data-total-A="{totA}" data-total-B="{totB}"
       aria-valuemin="0" aria-valuemax="100" hidden>
    <div class="progression-barre"><span></span></div>
    <div class="progression-compte"></div>
  </div>
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
      <!-- Ce champ libre finit dans le tableau de bord, qui n'a pas de
           vraie serrure : sa page verifie un mot de passe dans le
           navigateur du visiteur, ce qui ne protege rien. On ne peut pas
           y mettre une vraie authentification a quelques jours de
           l'ouverture ; on peut, en revanche, eviter qu'on y depose un
           nom et un numero de telephone. -->
      <p class="muted petite-note">Inutile d\'indiquer votre nom ou votre
        numéro : un membre de l\'équipe vient vers vous.</p>
      <button id="envoyerProbleme">Envoyer</button>
    </div>
    <p class="muted" id="retourProbleme" hidden></p>
  </div>
</div>

<footer>
  <img class="signature" src="../assets/img/logo-pomelo.webp" alt="Pomelo Événementiel">
  Le Sanctuaire des Brumes
</footer>

<script src="../assets/js/avant-ouverture.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.min.js"></script>
<script src="../assets/js/supabase-client.js"></script>
<script src="../assets/js/parcours.js"></script>
<script src="../assets/js/game.js"></script>
<script src="../assets/js/etape.js"></script>
<script src="../assets/js/scanner.js"></script>
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
    lg = fusionner_legendes(c, lg)
    lg = [x for x in lg if not ecran_vide(c, et, x)]
    communs = [x for x in lg if x["sens"] == "les deux"]
    sorties = {s: [x for x in lg if x["sens"] == "sens " + s.lower()] for s in ("A", "B")}

    blocs = []
    # « au scan » : la question tombe avant tout le reste, c'est la surprise.
    if c in popquiz and popquiz[c]["moment"] == "scan":
        blocs.append(bloc_popquiz(c))
    bonus_apres = (c in popquiz and popquiz[c]["moment"] == "sortie")
    for i, x in enumerate(communs):
        dernier = (i == len(communs) - 1) and not (sorties["A"] or sorties["B"]) \
                  and not bonus_apres
        blocs.append(bloc_ecran(et, x, dernier, None))
    if c in quiz and et["lettre"] and et["lettre"] not in ("-", "/"):
        blocs.append(bloc_lettre_du_quiz(et["lettre"]))
    if c in CONFIRMATION_INDICE and et["lettre"]:
        blocs.append(bloc_confirmation(et["lettre"], donnee=(c in LETTRE_DONNEE)))
    # La question de reflexion, juste avant le chemin.
    if c in REFLEXION:
        blocs.append(bloc_reflexion(c))
    # « avant la sortie » : la question vient apres le temoignage, juste avant
    # qu'on indique le chemin.
    if c in popquiz and popquiz[c]["moment"] == "sortie":
        blocs.append(bloc_popquiz(c))

    for s in ("A", "B"):
        # Seul le DERNIER ecran d'un sens porte le scanner. Une borne dont
        # tous les ecrans sont propres a un sens (Greg, version B) donnait le
        # scanner des la video : la consigne « allez voir Bill » qui suivait
        # ne s'affichait jamais.
        for j, x in enumerate(sorties[s]):
            suite = et["suite" + s]
            x = dict(x, lien=("../" + FICHIER[suite]) if suite else None)
            blocs.append(bloc_ecran(et, x, j == len(sorties[s]) - 1, s))

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
        extra += ('  epreuveReponse("reponse", "valider", "%s", "resultat", "aCote");\n'
                  % rep)
    if c in APPEL_AUDIO:
        extra += '  appelEntrant("decrocher", "audioAppel", "blocAppel");\n'
    if c in GALERIE:
        extra += '  galeriePhotos();\n'
    if c in CODE_CACHE:
        extra += '  codeATrouver("codeTrouve", "validerCode", "%s", "codeJuste", "codeACote");\n' % CODE_CACHE[c]
    if c == CONCLUSIONS and denouements:
        regles = [{"nom": f["nom"], "attendus": f["attendus"],
                   "interdits": f["interdits"]} for f in denouements]
        extra += ('  jugerLesConclusions("conclusions", "validerConclusions", '
                  '%s);\n' % json.dumps(regles, ensure_ascii=False))
    if c in CODE_DEMANDE:
        extra += '  porteACode("codeSerre", "validerSerre", "%s", "serreOuverte", "serreACote", "codePerdu");\n' % CODE_DEMANDE[c] 

    posA = str(ordre["A"][c]) if c in ordre["A"] else ""
    posB = str(ordre["B"][c]) if c in ordre["B"] else ""

    # La borne d'avant, dans chaque sens. Elle permet de revoir un temoignage
    # sans retraverser le parc : le verrouillage autorise deja toute borne
    # deja visitee, il ne manquait que le chemin pour y revenir.
    def precedente(sens):
        pos = ordre[sens].get(c)
        if not pos or pos <= 1: return ""
        for autre, p in ordre[sens].items():
            if p == pos - 1: return autre
        return ""
    precA, precB = precedente("A"), precedente("B")

    # titre : ce que lit le joueur. borne : l'identite en base, qui ne
    # change pas quand on rebaptise une etape.
    page = GABARIT.format(titre=e(TITRE_BORNE.get(c, et["nom"])),
                          borne=e(et["nom"]), code=c,
                          posA=e(posA), posB=e(posB),
                          totA=TOTAL["A"], totB=TOTAL["B"],
                          precA=e(precA), precB=e(precB),
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