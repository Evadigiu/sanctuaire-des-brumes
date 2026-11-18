# ============================================================
# TESTER LA DÉMO — Le Sanctuaire des Brumes
#
# Joue la démonstration de bout en bout dans un navigateur, comme un futur
# client qui a scanné le QR de la plaquette :
#   - les écrans s'enchaînent, la galerie et l'appel fonctionnent ;
#   - le code du sac ouvre la serre, un mauvais code non ;
#   - chaque réponse finale donne le bon dénouement, avec étincelles si juste ;
#   - la démo ne contacte jamais la base, ni Formspree ;
#   - elle n'est liée nulle part sur le site et n'est pas indexée.
# Lancer : python3 contenu/tester-la-demo.py
# ============================================================
import os, sys, glob, functools, threading, socketserver, http.server
from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = "demo-enquete-k7q3x"
CHROME = (sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")) or ["/usr/bin/google-chrome"])[-1]

class Muet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Muet, directory=RACINE))
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:%d/%s/" % (PORT, DEMO)

res = []
def note(nom, ok, detail=""):
    res.append((nom, ok)); print(("  OK    " if ok else "  ECHEC ") + nom + ("" if ok else "  -> " + str(detail)[:200]))

print("\nLa démo n'est liée nulle part et n'est pas indexée")
liens = []
for dossier, _, fichiers in os.walk(RACINE):
    if "/.git" in dossier or dossier.endswith("/contenu") or DEMO in dossier:
        continue
    for f in fichiers:
        if f.endswith((".html", ".js", ".md")):
            if DEMO in open(os.path.join(dossier, f), encoding="utf-8", errors="ignore").read():
                liens.append(os.path.join(dossier, f).replace(RACINE, ""))
liens = [l for l in liens if l != "/README.md"]
note("aucune page du jeu ne mène à la démo", not liens, liens)
page_html = open(os.path.join(RACINE, DEMO, "index.html"), encoding="utf-8").read()
note("balise noindex présente", 'name="robots" content="noindex, nofollow"' in page_html)
note("pas de Supabase dans la démo", "supabase" not in page_html.lower()
     and "supabase" not in open(os.path.join(RACINE, DEMO, "demo.js")).read().lower())

def nouvelle_page(nav):
    pg = nav.new_page(viewport={"width": 390, "height": 844})
    pg.__err = []; pg.__appels = []
    pg.on("pageerror", lambda e: pg.__err.append(str(e)))
    pg.on("request", lambda r: pg.__appels.append(r.url))
    pg.route("**/*.mp4", lambda r: r.abort())
    pg.route("**/*.mp3", lambda r: r.abort())
    return pg

visible = lambda pg: pg.locator(".ecran:not([hidden])")

def jouer(nav, choix, code="5824", aide=False):
    pg = nouvelle_page(nav); pg.goto(URL); pg.wait_for_timeout(300)
    titres = []
    def suivant():
        titres.append(visible(pg).locator(".ecran-titre").first.inner_text())
        visible(pg).locator("[data-suivant]").click(); pg.wait_for_timeout(120)
    suivant()                                   # accueil
    suivant()                                   # commissaire
    visible(pg).locator("[data-passer]").click(); pg.wait_for_timeout(120)   # Greg, passé
    pg.click("#decrocher"); pg.wait_for_timeout(100)
    appel_ok = pg.is_visible("#blocAppel")
    suivant()                                   # appel
    visible(pg).locator("[data-galerie-ouvrir]").click(); pg.wait_for_timeout(100)
    compte = visible(pg).locator("[data-galerie-compte]").inner_text()
    for _ in range(3): visible(pg).locator("[data-galerie-suiv]").click()
    fin_galerie = visible(pg).locator("[data-galerie-compte]").inner_text()
    suivant()                                   # images
    bloque = not visible(pg).locator("[data-suivant]").is_visible()
    if aide:
        pg.click("#codeAide")
    else:
        pg.fill("#codeDemo", "1234"); pg.click("#validerCode"); pg.wait_for_timeout(80)
        faux = pg.is_visible("#codeFaux")
        pg.fill("#codeDemo", " 58 24 "); pg.press("#codeDemo", "Enter")
    pg.wait_for_timeout(100)
    ouvert = pg.is_visible("#codeBon") and visible(pg).locator("[data-suivant]").is_visible()
    suivant()                                   # sac
    visible(pg).locator(".quiz-prop", has_text=choix).click(); pg.wait_for_timeout(150)
    suivant()                                   # vidéo de la serre
    suivant()                                   # lettre
    verdict = visible(pg).locator("[data-denouement]:not([hidden])")
    out = {"titres": titres, "appel": appel_ok, "galerie": (compte, fin_galerie), "bloque": bloque,
           "ouvert": ouvert, "verdict": verdict.get_attribute("data-denouement") if verdict.count() == 1 else None,
           "etincelles": pg.locator(".etincelle").count()}
    if not aide: out["faux"] = faux
    suivant()                                   # verdict
    out["coulisses"] = visible(pg).locator(".ecran-titre").first.inner_text()
    out["capture"] = pg.evaluate("[...document.querySelectorAll('.capture')].every(i => i.complete && i.naturalWidth > 0)")
    suivant()                                   # coulisses
    out["fin"] = visible(pg).locator(".ecran-titre").first.inner_text()
    out["site"] = visible(pg).locator('a[href="https://www.pomelolab.fr"]').count() == 1
    externes = [u for u in pg.__appels if not u.startswith("http://127.0.0.1")
                and "b-cdn.net" not in u]
    out["externes"] = externes; out["erreurs"] = pg.__err
    pg.close()
    return out

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

    print("\nLe parcours complet, avec la bonne réponse")
    r = jouer(nav, "Elle s'est endormie.")
    note("12 écrans, de l'accueil au contact", r["fin"].lower() == "et chez vous ?", r)
    note("l'appel se décroche", r["appel"])
    note("la galerie défile de 1/4 à 4/4", r["galerie"] == ("1 / 4", "4 / 4"), r["galerie"])
    note("le sac bloque la suite tant que la serre est fermée", r["bloque"])
    note("un mauvais code est refusé", r["faux"])
    note("« 58 24 » validé par Entrée ouvre la serre", r["ouvert"])
    note("bonne réponse : dénouement « Bon »", r["verdict"] == "Bon", r["verdict"])
    note("bonne réponse : des étincelles", r["etincelles"] > 0)
    note("l'écran coulisses montre la capture fictive", r["coulisses"].lower() == "côté organisateur" and r["capture"], r)
    note("le lien vers pomelolab.fr est là", r["site"])
    note("aucun appel réseau hors site et vidéos", not r["externes"], r["externes"])
    note("aucune erreur JavaScript", not r["erreurs"], r["erreurs"])

    print("\nLes autres réponses")
    for choix, attendu in [("Louis l'a empoisonnée avec sa tisane.", "Moyen"), ("Greg l'a kidnappée.", "Mauvais")]:
        r = jouer(nav, choix, aide=True)
        note("« %s » : dénouement %s, sans étincelles" % (choix[:22], attendu),
             r["verdict"] == attendu and r["etincelles"] == 0, r["verdict"])
        note("« Je n'y arrive pas » ouvre aussi la serre", r["ouvert"])

    print("\nSur un écran d'ordinateur")
    pg = nav.new_page(viewport={"width": 1280, "height": 800})
    pg.goto(URL); pg.wait_for_timeout(300)
    deborde = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    note("pas de débordement horizontal", not deborde)
    pg.close()
    nav.close()

ko = [n for n, ok in res if not ok]
print("\n%d contrôles\nECHECS : %d %s" % (len(res), len(ko), ko if ko else ""))
sys.exit(1 if ko else 0)
