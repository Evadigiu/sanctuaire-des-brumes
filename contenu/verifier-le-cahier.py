# -*- coding: utf-8 -*-
"""
Verifie le cahier de contenu avant de fabriquer les pages du jeu.

Ne modifie rien. Croise l'onglet Parcours et l'onglet Textes pour trouver
les endroits ou un joueur serait bloque, tournerait en rond, ou ou le
tableur se contredit lui-meme.

    python3 contenu/verifier-le-cahier.py
"""
import os, sys, unicodedata
from openpyxl import load_workbook

FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "sanctuaire-cahier-de-contenu.xlsx")

def propre(v):
    return "" if v is None else str(v).strip()

def sans_accent(t):
    """Minuscules sans accents : "Salle de seminaire" et "salle de seminaire"
    doivent se reconnaitre, sinon une faute d'accent masque une erreur reelle."""
    d = unicodedata.normalize("NFKD", t.lower())
    return "".join(c for c in d if not unicodedata.combining(c))

def code_dans(txt):
    """Extrait le code d'etape (E07, E11B...) d'une cellule 'Suite en sens X'."""
    t = propre(txt).upper().replace("-", " ")
    for mot in t.replace(":", " ").split():
        m = mot.strip(".,;")
        if m.startswith("E") and m[1:].rstrip("B").isdigit():
            return m
    return None

def main():
    wb = load_workbook(FICHIER, data_only=True)
    par, tex = wb["Parcours"], wb["Textes"]

    # ---------- l'onglet Parcours ----------
    etapes, ordre = {}, {"A": {}, "B": {}}
    for r in par.iter_rows(min_row=3, values_only=True):
        c = propre(r[0])
        if not c: continue
        etapes[c] = {
            "nom": propre(r[1]), "type": propre(r[2]), "lieu": propre(r[3]),
            "qr": propre(r[4]), "lettre": propre(r[5]),
            "ordreA": propre(r[6]), "suiteA": code_dans(r[7]),
            "ordreB": propre(r[8]), "suiteB": code_dans(r[9]),
        }
        for s, i in (("A", 6), ("B", 8)):
            v = propre(r[i])
            if v.isdigit(): ordre[s][c] = int(v)

    # ---------- l'onglet Textes ----------
    textes = {}   # (code, sens, ecran) -> texte
    for r in tex.iter_rows(min_row=3, values_only=True):
        c = propre(r[0])
        if not c: continue
        textes.setdefault(c, []).append({
            "sens": propre(r[2]).lower(), "ecran": propre(r[3]), "texte": propre(r[5]),
        })

    pb, av = [], []

    # 1. chaque etape du parcours a-t-elle des textes ?
    for c in etapes:
        if c not in textes:
            pb.append("%s (%s) : aucune ligne dans l'onglet Textes." % (c, etapes[c]["nom"]))

    # 2. le joueur sait-il toujours ou aller ensuite ?
    for sens in ("A", "B"):
        cle_sens, cle_suite = "sens " + sens.lower(), "suite" + sens
        suite_ordonnee = sorted(ordre[sens].items(), key=lambda kv: kv[1])
        for c, pos in suite_ordonnee:
            e = etapes[c]
            if not e[cle_suite]:
                continue   # derniere etape
            lignes = [t for t in textes.get(c, [])
                      if t["ecran"].strip().startswith("4") or "aller ensuite" in t["ecran"].lower()]
            pour_ce_sens = [t for t in lignes if t["sens"] in (cle_sens, "les deux")]
            if not pour_ce_sens:
                autre = "sens " + ("b" if sens == "A" else "a")
                mal_etiquete = [t for t in lignes if t["sens"] == autre]
                if mal_etiquete:
                    pb.append("SENS %s, %s (%s) : l'orientation existe mais elle est etiquetee "
                              "\"%s\" au lieu de \"%s\". Le joueur serait bloque ici."
                              % (sens, c, e["nom"], autre, cle_sens))
                else:
                    pb.append("SENS %s, %s (%s) : aucune orientation. Le joueur ne sait pas ou aller."
                              % (sens, c, e["nom"]))
            elif not any(t["texte"] for t in pour_ce_sens):
                pb.append("SENS %s, %s (%s) : la case d'orientation est vide. Le joueur serait bloque."
                          % (sens, c, e["nom"]))

    # 3. l'orientation mentionne-t-elle un lieu deja visite ? (tourne en rond)
    for sens in ("A", "B"):
        cle_sens, cle_suite = "sens " + sens.lower(), "suite" + sens
        deja = []
        for c, pos in sorted(ordre[sens].items(), key=lambda kv: kv[1]):
            e = etapes[c]
            cible = e[cle_suite]
            for t in textes.get(c, []):
                if not (t["ecran"].strip().startswith("4") or "aller ensuite" in t["ecran"].lower()):
                    continue
                if t["sens"] not in (cle_sens, "les deux") or not t["texte"]:
                    continue
                txt = sans_accent(t["texte"])
                for vu in deja:
                    lieu = sans_accent(vu[1])
                    if len(lieu) > 8 and lieu in txt and vu[0] != cible:
                        pb.append("SENS %s, %s (%s) : le texte renvoie vers \"%s\", un lieu deja "
                                  "visite a l'etape %s. Or la suite declaree est %s. Le joueur tourne en rond."
                                  % (sens, c, e["nom"], vu[1], vu[0], cible))
            if e["lieu"]: deja.append((c, e["lieu"]))

    # 4. les lettres, dans l'ordre de ramassage
    for sens in ("A", "B"):
        lettres = [etapes[c]["lettre"] for c, _ in sorted(ordre[sens].items(), key=lambda kv: kv[1])
                   if etapes[c]["lettre"] and etapes[c]["lettre"] not in ("-", "/")]
        mot = "".join(lettres)
        note = "  <-- le mot est deja ecrit, l'enigme se resout sans reflechir" if mot == "IRIS" else ""
        av.append("SENS %s : lettres ramassees dans l'ordre %s%s" % (sens, ", ".join(lettres), note))

    # 5. bornes QR non tranchees
    sans = [c for c in etapes if not etapes[c]["qr"]]
    if sans:
        av.append("Colonne \"Borne QR ?\" vide pour %d etapes sur %d. Sans cette reponse, on ne sait "
                  "pas combien de QR codes fabriquer." % (len(sans), len(etapes)))

    # 6. lieux manquants ou flous
    for c, e in etapes.items():
        if not e["lieu"]:
            av.append("%s (%s) : pas de lieu indique dans le parc." % (c, e["nom"]))
        elif len(e["lieu"]) < 10:
            av.append("%s (%s) : lieu \"%s\", trop vague pour poser un QR code." % (c, e["nom"], e["lieu"]))

    # 7. textes vides hors video
    for c, lignes in textes.items():
        for t in lignes:
            if t["texte"]: continue
            ec = t["ecran"].lower()
            if "video" in ec or "vidéo" in ec or "finish" in ec: continue
            av.append("%s : ecran \"%s\" sans texte." % (c, t["ecran"]))

    # ---------- rapport ----------
    print("=" * 78)
    print("VERIFICATION DU CAHIER DE CONTENU")
    print("=" * 78)
    print("%d etapes, %d lignes de texte\n" % (len(etapes), sum(len(v) for v in textes.values())))
    print("BLOQUANT  (%d)  le jeu ne peut pas tourner en l'etat" % len(pb))
    print("-" * 78)
    for x in pb: print("  * " + x)
    if not pb: print("  aucun")
    print("\nA REGARDER  (%d)" % len(av))
    print("-" * 78)
    for x in av: print("  - " + x)
    return 1 if pb else 0

if __name__ == "__main__":
    sys.exit(main())
