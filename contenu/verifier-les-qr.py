# -*- coding: utf-8 -*-
"""Relit chaque QR code avec un lecteur et verifie son adresse.

    python3 contenu/verifier-les-qr.py

Generer un QR et le relire sont deux choses differentes : on imprime seize
affichettes qu'on ira coller dans un parc, et une erreur ne se verrait qu'une
fois sur place. Ce controle decode reellement chaque image.
"""
import os, sys, json, glob
try:
    import cv2
except ImportError:
    sys.exit("Il manque opencv : pip install opencv-python-headless")

ICI    = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)

plan = json.loads(open(os.path.join(RACINE, "assets", "js", "parcours.js"),
                       encoding="utf-8").read()
                  .split("const PARCOURS =", 1)[1].rstrip().rstrip(";"))
src = open(os.path.join(ICI, "fabriquer-les-pages.py"), encoding="utf-8").read()
DOMAINE = src.split('DOMAINE = "', 1)[1].split('"', 1)[0]
secours = {c: n for n, c in plan["secours"].items()}

attendu = {secours[c]: "%s/%s" % (DOMAINE, plan["pages"][c]) for c in plan["pages"]}
fichiers = sorted(glob.glob(os.path.join(RACINE, "qr-codes", "*.png")))

if not fichiers:
    sys.exit("Aucun QR code. Lancer d'abord fabriquer-les-qr.py.")

det = cv2.QRCodeDetector()
pb = []
for f in fichiers:
    num = os.path.basename(f).split("-")[1]
    lu, _, _ = det.detectAndDecode(cv2.imread(f))
    if not lu:
        pb.append("%s : illisible." % os.path.basename(f))
    elif lu != attendu.get(num):
        pb.append("%s : mene vers %s au lieu de %s"
                  % (os.path.basename(f), lu, attendu.get(num)))

manquants = set(attendu) - {os.path.basename(f).split("-")[1] for f in fichiers}
for m in manquants:
    pb.append("Aucun QR pour la borne %s." % m)

print("=" * 70)
print("RELECTURE DES QR CODES")
print("=" * 70)
print("%d images, domaine %s\n" % (len(fichiers), DOMAINE))
if pb:
    for x in pb: print("  * " + x)
else:
    print("  Les %d QR sont lisibles et menent tous a la bonne borne." % len(fichiers))
sys.exit(1 if pb else 0)
