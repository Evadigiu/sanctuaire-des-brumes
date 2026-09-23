# -*- coding: utf-8 -*-
"""Ajoute a DCC Ash les lettres accentuees francaises qui lui manquent.

    python3 contenu/completer-la-police.py

La police fournie vise l'Europe centrale : elle a les carons et les accents
aigus, mais ni l'accent grave, ni le circonflexe sur le E, ni la cedille.
Or « LA COLLEGUE SOIGNEUSE » s'ecrit avec un E accent grave, et le navigateur
dessinait alors cette seule lettre dans une autre police, au milieu du titre.

On ne redessine rien : on compose. Les accents existent deja dans la police,
isoles ou portes par d'autres lettres ; il suffit de les poser au bon endroit
sur les lettres de base. La position vient de la police elle-meme, mesuree sur
les lettres accentuees qu'elle possede deja, pour que les nouvelles soient
indiscernables des anciennes.

Produit assets/fonts/dcc-ash-fr.otf, puis le WOFF2 allege servi aux joueurs.
"""
import os, sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Offset

ICI    = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
SOURCE = os.path.join(RACINE, "assets", "fonts", "dcc-ash.otf")
CIBLE  = os.path.join(RACINE, "assets", "fonts", "dcc-ash-fr.otf")
WEB    = os.path.join(RACINE, "assets", "fonts", "dcc-ash.woff2")

# lettre de base, accent, nom du nouveau glyphe, caractere
A_CREER = [
    ("E", "grave",      "Egrave",      "È"),
    ("E", "circumflex", "Ecircumflex", "Ê"),
    ("A", "grave",      "Agrave",      "À"),
    ("U", "grave",      "Ugrave",      "Ù"),
    ("U", "circumflex", "Ucircumflex", "Û"),
    ("I", "dieresis",   "Idieresis",   "Ï"),
    ("Y", "dieresis",   "Ydieresis",   "Ÿ"),
    ("C", "cedilla",    "Ccedilla",    "Ç"),
]

f  = TTFont(SOURCE)
gs = f.getGlyphSet()
cff = f["CFF "].cff
top = cff[cff.fontNames[0]]
charstrings = top.CharStrings

def contours(nom):
    p = RecordingPen(); gs[nom].draw(p); return p.value

def bornes(valeurs):
    p = BoundsPen(None)
    for op, args in valeurs: getattr(p, op)(*args)
    return p.bounds

def largeur(nom):
    return top.CharStrings[nom].width if hasattr(top.CharStrings[nom], "width") else gs[nom].width

# --- Le circonflexe n'existe pas isole : on le preleve sur le A ---
base_A, avec_A = contours("A"), contours("Acircumflex")
circonflexe = [c for c in avec_A if c not in base_A]
if not circonflexe:
    sys.exit("Impossible de prelever le circonflexe sur Acircumflex.")

# --- Ou poser un accent ? La police le dit elle-meme, via E et Eacute ---
hE   = bornes(contours("E"))[3]          # sommet du E
hEac = bornes(contours("Eacute"))[3]     # sommet du E accent aigu
haut_accent = bornes(contours("acute"))[3] - bornes(contours("acute"))[1]
BASE_ACCENT = hEac - haut_accent - hE     # de combien l'accent depasse la lettre
print("Mesure prise sur la police : un accent se pose %d unites au-dessus de la lettre."
      % BASE_ACCENT)

def accent_de(nom):
    return circonflexe if nom == "circumflex" else contours(nom)

ajoutes = []
for lettre, accent, nouveau, caractere in A_CREER:
    if nouveau in charstrings:
        continue
    if lettre not in charstrings:
        print("  %s : lettre de base %s absente, ignore" % (caractere, lettre)); continue

    trace_lettre = contours(lettre)
    trace_accent = accent_de(accent)
    bl, ba = bornes(trace_lettre), bornes(trace_accent)

    # Centre l'accent sur la lettre
    dx = ((bl[0] + bl[2]) / 2) - ((ba[0] + ba[2]) / 2)
    # Le pose au-dessus, sauf la cedille qui pend sous la lettre
    dy = 0 if accent == "cedilla" else (bl[3] + BASE_ACCENT) - ba[1]

    stylo = T2CharStringPen(largeur(lettre), None)
    for op, args in trace_lettre: getattr(stylo, op)(*args)
    decale = TransformPen(stylo, Offset(dx, dy))
    for op, args in trace_accent: getattr(decale, op)(*args)

    cs = stylo.getCharString()
    cs.private = charstrings[lettre].private
    # Un glyphe neuf s'inscrit a trois endroits : la liste des dessins, la
    # table des noms, et la liste des glyphes de la police.
    charstrings.charStringsIndex.append(cs)
    charstrings.charStrings[nouveau] = len(charstrings.charStringsIndex) - 1
    top.charset.append(nouveau)          # le catalogue interne du CFF
    f.setGlyphOrder(f.getGlyphOrder() + [nouveau])
    f["hmtx"].metrics[nouveau] = f["hmtx"].metrics[lettre]
    # Seules les tables Unicode : la police embarque aussi une vieille table
    # limitee a 256 caracteres, qui refuse tout ce qui depasse.
    for table in f["cmap"].tables:
        if table.isUnicode():
            table.cmap[ord(caractere)] = nouveau
    ajoutes.append(caractere)

if not ajoutes:
    print("Rien a ajouter, la police est deja complete.")
else:
    print("Lettres composees : " + " ".join(ajoutes))

# La police compte desormais huit glyphes de plus. Le decompte se prend sur
# le catalogue du CFF, seule liste qui fasse foi a la relecture : celle que
# l'on manipule en memoire derive d'ailleurs et se decale d'une unite.
f.setGlyphOrder(top.charset)
f["maxp"].numGlyphs = len(top.charset)
f.save(CIBLE)

# --- Le fichier servi aux joueurs : capitales seules, format web ---
from fontTools import subset
maj = ("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
       " .,;:!?'’«»\"()-–—·&/…"
       "ÀÂÄÇÉÈÊËÎÏ"
       "ÔÖÙÛÜŸ")
opt = subset.Options(); opt.layout_features = ["*"]; opt.notdef_outline = True
sub = subset.load_font(CIBLE, opt)
s = subset.Subsetter(options=opt); s.populate(text=maj); s.subset(sub)
opt.flavor = "woff2"
subset.save_font(sub, WEB, opt)
print("WOFF2 servi aux joueurs : %d Ko" % (os.path.getsize(WEB)//1024))

# --- Controle : la police sait-elle ecrire les titres du jeu ? ---
import json, io
plan = json.loads(io.open(os.path.join(RACINE, "assets", "js", "parcours.js"),
                          encoding="utf-8").read()
                  .split("const PARCOURS =", 1)[1].rstrip().rstrip(";"))
cmap = TTFont(WEB).getBestCmap()
manque = set()
for t in list(plan["noms"].values()) + ["Vous êtes l'enquêteur·rice",
                                        "Votre enquête commence",
                                        "Le Sanctuaire des Brumes"]:
    for ch in t.upper():
        if not ch.isspace() and ord(ch) not in cmap:
            manque.add(ch)
print("Caracteres encore absents des titres :", " ".join(sorted(manque)) or "aucun")
sys.exit(1 if manque else 0)
