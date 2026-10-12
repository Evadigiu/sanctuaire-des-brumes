# -*- coding: utf-8 -*-
"""
Fabrique les codes remis a l'accueil du zoo.

    python3 contenu/fabriquer-les-vrais-codes.py [nombre] [sortie] [options]

        --antihoraire N   combien de codes partent dans l'autre sens
                          (par defaut la moitie)
        --depuis F.xlsx   reprend les codes d'une serie deja imprimee au
                          lieu d'en tirer de nouveaux, et ne change que
                          leur sens

Produit deux fichiers :
    codes-du-sanctuaire.xlsx   la liste, pour l'impression et le suivi
    codes-a-charger.sql        a coller dans Supabase pour que le jeu les connaisse

>>> LES FICHIERS PRODUITS NE DOIVENT JAMAIS ENTRER DANS LE DEPOT. <<<
Le depot est public : un code publie est un code offert, et la billetterie
ne sert plus a rien. Ils sortent donc hors du depot par defaut, et
.gitignore les refuse s'ils y atterrissent par accident.

LE FORMAT
  Huit signes tires au hasard dans un alphabet de 32, ou l'on a retire tout
  ce qui se confond a la lecture : ni I ni 1, ni O ni 0. Cela fait mille
  milliards de combinaisons, et personne a l'accueil ne lit un zero pour
  un O.

  Ne JAMAIS numeroter les codes (SDB-001, SDB-002...). Un visiteur qui voit
  le billet de son voisin devinerait tous les autres, et le verrouillage de
  la base n'y pourrait rien : il empeche de LIRE la liste, pas de DEVINER
  un code.

LE SENS
  Chaque code porte le sens du parcours, et la pile est rangee pour que
  l'accueil n'ait rien a decider : les codes de l'autre sens sont semes a
  intervalle regulier dans la pile. A 500 contre 100, c'est un billet sur
  six ; a 300 contre 300, c'est un sur deux. L'agent prend toujours celui
  du dessus, et la repartition se fait toute seule.

  Le sens n'est pas imprime sur le billet. Changer la repartition d'une
  serie deja imprimee ne demande donc AUCUNE reimpression : il suffit de
  recharger le SQL, a condition que la pile reste rangee par numero.

LA DATE
  Les codes ne sont pas dates. Rien dans le jeu ne verifie la date d'un
  code : il s'ouvre le jour ou on l'active. Des codes dates auraient fait
  du gachis (ceux du mardi perdus le mardi soir) sans rien apporter.
"""
import os, sys, secrets, datetime

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # ni I, ni O, ni 0, ni 1
LONGUEUR = 8

# Un code est imprime sur un billet et lu a voix haute a l'accueil. Le hasard
# finit toujours par produire le mot qu'il ne fallait pas.
MALVENUS = ("CUL", "PUTE", "SEXE", "FUCK", "MERDE", "ANUS", "PEDE",
            "NAZE", "CACA", "SUCE", "PUTA", "CRAP", "DAMN", "TEST")

def un_code():
    while True:
        c = "".join(secrets.choice(ALPHABET) for _ in range(LONGUEUR))
        if not any(m in c for m in MALVENUS):
            return c

def semer_les_sens(nombre, nb_antihoraire):
    """Le sens de chaque place dans la pile.

    Les codes de l'autre sens sont repartis regulierement plutot que
    groupes a la fin : une pile dont les cent derniers billets partent
    tous dans le meme sens enverrait tout le monde du meme cote le
    dernier dimanche, et la moitie du parc serait vide pendant que
    l'autre bouchonne.
    """
    if nb_antihoraire <= 0:          return ["horaire"] * nombre
    if nb_antihoraire >= nombre:     return ["antihoraire"] * nombre
    sens, poses = [], 0
    for i in range(nombre):
        # On pose un antihoraire des que la part deja posee passe sous la
        # part visee. Pour 100 sur 600, cela donne un billet sur six.
        if poses * nombre < (i + 1) * nb_antihoraire:
            sens.append("antihoraire"); poses += 1
        else:
            sens.append("horaire")
    return sens


def fabriquer(nombre, nb_antihoraire=None):
    if nb_antihoraire is None: nb_antihoraire = nombre // 2
    repartition = semer_les_sens(nombre, nb_antihoraire)
    codes, vus = [], set()
    while len(codes) < nombre:
        c = un_code()
        if c in vus: continue
        vus.add(c)
        codes.append((c, repartition[len(codes)]))
    return codes


def relire_excel(chemin):
    """Les codes d'une serie deja imprimee, dans l'ordre de la pile.

    On ne retire pas de nouveaux codes : ceux-la sont deja sur du papier.
    Seul leur sens va changer, et le sens n'est pas imprime.
    """
    from openpyxl import load_workbook
    ws = load_workbook(chemin, data_only=True)["Codes"]
    codes = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        c = "" if r[1] is None else str(r[1]).strip().upper()
        if c: codes.append(c)
    if not codes:
        sys.exit("Aucun code lu dans %s (onglet \"Codes\", colonne B)." % chemin)
    if len(set(codes)) != len(codes):
        sys.exit("Le fichier contient des codes en double.")
    return codes


def ecrire_excel(codes, chemin):
    nb_h = sum(1 for _, x in codes if x == "horaire")
    nb_a = len(codes) - nb_h
    if nb_a == 0:   melange = "aucun billet en sens antihoraire"
    elif nb_a == len(codes): melange = "tous en sens antihoraire"
    else:           melange = "environ un billet sur %d part dans l'autre sens" \
                              % round(len(codes) / nb_a)
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()

    # --- Mode d'emploi, en premier : c'est la page qu'on ouvre en premier ---
    ke = wb.active
    ke.title = "Mode d'emploi"
    lignes = [
        ("LES CODES DU SANCTUAIRE DES BRUMES", True),
        ("", False),
        ("Fabrique le %s. %d codes : %d en sens horaire, %d en antihoraire."
         % (datetime.date.today().strftime("%d/%m/%Y"), len(codes),
            nb_h, len(codes) - nb_h), False),
        ("", False),
        ("CE DOCUMENT EST CONFIDENTIEL", True),
        ("Un code lu par quelqu'un qui n'a pas paye, c'est une partie offerte.", False),
        ("Ne le mettez pas sur GitHub, ni sur un Drive partage avec le public.", False),
        ("", False),
        ("A QUOI SERVENT LES COLONNES", True),
        ("Code          ce qui est imprime sur le billet", False),
        ("Sens          le cote du parc par lequel le groupe commence.", False),
        ("              A ne PAS imprimer : ca ne dit rien au joueur et ca", False),
        ("              revele une mecanique du jeu.", False),
        ("Personnes     6 pour tous : c'est un plafond, pas une obligation.", False),
        ("              Le joueur declare lui-meme combien ils sont, et le", False),
        ("              jeu refuse au-dela de 6.", False),
        ("Distribue le  a remplir a la main si vous voulez suivre.", False),
        ("Remis a       idem. Ces deux colonnes sont pour vous, le jeu les", False),
        ("              ignore.", False),
        ("", False),
        ("COMMENT L'ACCUEIL DISTRIBUE", True),
        ("Une seule pile, rangee par numero. L'agent prend le code du dessus,", False),
        ("quel que soit le nombre de personnes.", False),
        ("", False),
        ("NE TRIEZ PAS LA PILE, NE LA MELANGEZ PAS.", True),
        ("Les deux sens y sont semes a intervalle regulier : %s." % melange, False),
        ("C'est ce rangement, et lui seul, qui repartit les groupes dans le", False),
        ("parc. Une pile melangee enverrait tout le monde du meme cote.", False),
        ("", False),
        ("AVANT L'OUVERTURE", True),
        ("1. Charger les codes dans Supabase avec codes-a-charger.sql,", False),
        ("   sinon le jeu ne les connait pas et refuse tout le monde.", False),
        ("2. Effacer les codes de test :", False),
        ("      delete from scans where code_id in", False),
        ("        (select id from codes where code like 'TEST%');", False),
        ("      delete from codes where code like 'TEST%';", False),
        ("", False),
        ("SI VOUS TOMBEZ A COURT", True),
        ("Relancez le script pour une seconde serie. Les nouveaux codes ne", False),
        ("peuvent pas tomber sur les anciens : la base les refuserait.", False),
    ]
    for i, (texte, gras) in enumerate(lignes, start=1):
        c = ke.cell(row=i, column=1, value=texte)
        if gras: c.font = Font(bold=True, size=12)
    ke.column_dimensions["A"].width = 76

    # --- La liste ---
    ws = wb.create_sheet("Codes")
    entetes = ["N°", "Code", "Sens", "Personnes max", "Distribué le", "Remis à"]
    fond = PatternFill("solid", fgColor="1F2430")
    for j, t in enumerate(entetes, start=1):
        c = ws.cell(row=1, column=j, value=t)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = fond
        c.alignment = Alignment(horizontal="center")

    for i, (code, sens) in enumerate(codes, start=1):
        ws.cell(row=i + 1, column=1, value=i)
        c = ws.cell(row=i + 1, column=2, value=code)
        c.font = Font(name="Consolas", size=12, bold=True)   # chiffres alignes
        ws.cell(row=i + 1, column=3, value=sens)
        ws.cell(row=i + 1, column=4, value=6)

    for j, largeur in enumerate((6, 16, 14, 15, 16, 24), start=1):
        ws.column_dimensions[get_column_letter(j)].width = largeur
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:F%d" % (len(codes) + 1)

    wb.save(chemin)


def ecrire_sql(codes, chemin):
    # slot_time est obligatoire dans la table mais n'est verifie nulle part :
    # on y met la date d'ouverture, a titre indicatif.
    lignes = ["insert into codes (code, max_participants, direction, slot_time) values"]
    tuples = ["  ('%s', 6, '%s', timestamptz '2026-10-17 09:00+02')" % (c, s)
              for c, s in codes]
    lignes.append(",\n".join(tuples))
    # Les codes peuvent etre DEJA dans la base avec un autre sens : c'est le
    # cas quand on change la repartition d'une serie imprimee. "do nothing"
    # les aurait laisses tels quels, en silence, et la moitie de la pile
    # aurait envoye les groupes du mauvais cote.
    #
    # Le "where" est le garde-fou : un code deja active garde son sens. Un
    # groupe en train de jouer ne doit pas voir son parcours s'inverser
    # entre deux bornes.
    lignes.append("on conflict (code) do update")
    lignes.append("  set direction = excluded.direction")
    lignes.append("  where codes.status = 'unused';")
    lignes.append("")
    lignes.append("-- Controle : %d codes, dont %d en sens horaire."
                  % (len(codes), sum(1 for _, x in codes if x == "horaire")))
    lignes.append("select direction, status, count(*)")
    lignes.append("  from codes where code not like 'TEST%'")
    lignes.append(" group by direction, status")
    lignes.append(" order by direction, status;")

    entete = """-- ============================================================
-- LES %d CODES DU SANCTUAIRE DES BRUMES
-- Fabrique le %s.
--
-- A coller dans Supabase : SQL Editor > New query > Run.
-- Message attendu : "Success. No rows returned", puis le compte.
--
-- >>> CE FICHIER EST CONFIDENTIEL. Il ne doit jamais entrer dans le
-- >>> depot GitHub, qui est public. Un code publie est un code offert.
--
-- Relancer ce fichier deux fois ne cree pas de doublons. Un code deja
-- present voit seulement son SENS mis a jour, et seulement s'il n'a pas
-- encore ete active : une partie en cours ne change jamais de sens.
-- ============================================================

""" % (len(codes), datetime.date.today().strftime("%d/%m/%Y"))
    open(chemin, "w", encoding="utf-8").write(entete + "\n".join(lignes) + "\n")


def lire_options(args):
    """Les options de la ligne de commande, sans dependance exterieure."""
    nombre, sortie, antihoraire, depuis = None, ".", None, None
    reste = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--antihoraire":
            i += 1
            if i >= len(args): sys.exit("--antihoraire attend un nombre.")
            try: antihoraire = int(args[i])
            except ValueError: sys.exit("--antihoraire attend un nombre.")
        elif a == "--depuis":
            i += 1
            if i >= len(args): sys.exit("--depuis attend un fichier .xlsx.")
            depuis = args[i]
        elif a.startswith("--"):
            sys.exit("Option inconnue : %s" % a)
        else:
            reste.append(a)
        i += 1
    # Un argument qui s'ecrit avec des chiffres est le nombre de codes, les
    # autres sont le dossier de sortie. Avec --depuis le nombre n'a plus de
    # raison d'etre, et l'ordre des arguments cesse d'avoir de l'importance.
    for a in reste:
        if a.isdigit() and nombre is None: nombre = int(a)
        else: sortie = a
    return nombre, sortie, antihoraire, depuis


if __name__ == "__main__":
    nombre, sortie, antihoraire, depuis = lire_options(sys.argv[1:])

    if depuis:
        # Serie deja imprimee : on garde les codes, on ne change que le sens.
        anciens = relire_excel(depuis)
        if nombre and nombre != len(anciens):
            sys.exit("Le fichier contient %d codes, pas %d. Retirez le nombre "
                     "de la ligne de commande ou corrigez-le."
                     % (len(anciens), nombre))
        nombre = len(anciens)
        if antihoraire is None: antihoraire = nombre // 2
        codes = list(zip(anciens, semer_les_sens(nombre, antihoraire)))
    else:
        if nombre is None: nombre = 600
        if antihoraire is None: antihoraire = nombre // 2
        codes = fabriquer(nombre, antihoraire)

    if not 0 <= antihoraire <= nombre:
        sys.exit("--antihoraire doit etre compris entre 0 et %d." % nombre)

    os.makedirs(sortie, exist_ok=True)

    # Controles avant de rien ecrire : une erreur ici coute une impression.
    assert len(set(c for c, _ in codes)) == nombre, "doublon dans les codes"
    assert all(len(c) == LONGUEUR for c, _ in codes), "longueur inattendue"
    assert all(set(c) <= set(ALPHABET) for c, _ in codes), "signe interdit"
    horaires = sum(1 for _, s in codes if s == "horaire")
    assert nombre - horaires == antihoraire, \
        "repartition demandee %d, obtenue %d" % (antihoraire, nombre - horaires)
    if depuis:
        assert [c for c, _ in codes] == anciens, "les codes ont bouge"

    ecrire_excel(codes, os.path.join(sortie, "codes-du-sanctuaire.xlsx"))
    ecrire_sql(codes, os.path.join(sortie, "codes-a-charger.sql"))

    print("%d codes %s dans %s"
          % (nombre, "repartis" if depuis else "fabriques", os.path.abspath(sortie)))
    print("  %d en sens horaire, %d en antihoraire" % (horaires, nombre - horaires))
    if depuis:
        print("  les codes sont inchanges : AUCUNE reimpression de billet")
