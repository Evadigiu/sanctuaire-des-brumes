# -*- coding: utf-8 -*-
"""
Fabrique les codes remis a l'accueil du zoo.

    python3 contenu/fabriquer-les-vrais-codes.py [nombre] [dossier de sortie]

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
  Chaque code porte le sens du parcours. On alterne, pour que la pile
  distribue naturellement un groupe sur deux dans chaque sens et que les
  deux moities du parc se remplissent a la meme vitesse.

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

def fabriquer(nombre):
    codes, vus = [], set()
    while len(codes) < nombre:
        c = un_code()
        if c in vus: continue
        vus.add(c)
        sens = "horaire" if len(codes) % 2 == 0 else "antihoraire"
        codes.append((c, sens))
    return codes


def ecrire_excel(codes, chemin):
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
        ("Fabrique le %s. %d codes." % (
            datetime.date.today().strftime("%d/%m/%Y"), len(codes)), False),
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
        ("Une seule pile. L'agent prend le code du dessus, quel que soit le", False),
        ("nombre de personnes. La pile alterne les deux sens toute seule :", False),
        ("ne la triez pas, ne la melangez pas non plus.", False),
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
    lignes.append("on conflict (code) do nothing;")
    lignes.append("")
    lignes.append("-- Controle : doit renvoyer %d." % len(codes))
    lignes.append("select count(*) as codes_charges from codes where code not like 'TEST%';")

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
-- "on conflict do nothing" : relancer ce fichier deux fois ne cree pas
-- de doublons et n'efface rien.
-- ============================================================

""" % (len(codes), datetime.date.today().strftime("%d/%m/%Y"))
    open(chemin, "w", encoding="utf-8").write(entete + "\n".join(lignes) + "\n")


if __name__ == "__main__":
    nombre = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    sortie = sys.argv[2] if len(sys.argv) > 2 else "."
    os.makedirs(sortie, exist_ok=True)

    codes = fabriquer(nombre)

    # Controles avant de rien ecrire : une erreur ici coute une impression.
    assert len(set(c for c, _ in codes)) == nombre, "doublon dans les codes"
    assert all(len(c) == LONGUEUR for c, _ in codes), "longueur inattendue"
    assert all(set(c) <= set(ALPHABET) for c, _ in codes), "signe interdit"
    horaires = sum(1 for _, s in codes if s == "horaire")
    assert abs(horaires - nombre / 2) <= 1, "les deux sens ne s'equilibrent pas"

    ecrire_excel(codes, os.path.join(sortie, "codes-du-sanctuaire.xlsx"))
    ecrire_sql(codes, os.path.join(sortie, "codes-a-charger.sql"))

    print("%d codes fabriques dans %s" % (nombre, os.path.abspath(sortie)))
    print("  %d en sens horaire, %d en antihoraire" % (horaires, nombre - horaires))
    print("  exemple : %s" % codes[0][0])
