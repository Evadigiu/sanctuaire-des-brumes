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
    pg.route("**fonts.g**", lambda r: r.abort())
    return pg

visible = lambda pg: pg.locator(".ecran:not([hidden])")

def jouer(nav, choix, aide=False):
    pg = nouvelle_page(nav); pg.goto(URL); pg.wait_for_timeout(300)
    titres, comptes = [], []
    def suivant():
        titres.append(pg.inner_text("#titreEtape"))
        comptes.append(pg.inner_text(".progression-compte"))
        visible(pg).locator("[data-suivant]").click(); pg.wait_for_timeout(120)
    suivant()                                   # accueil
    suivant()                                   # commissaire
    visible(pg).locator("[data-passer]").click(); pg.wait_for_timeout(120)   # Greg, passé
    pg.wait_for_timeout(300)
    sonne = pg.evaluate("!document.getElementById('sonnerie').paused && document.getElementById('decrocher').classList.contains('sonne')")
    pg.click("#decrocher", force=True); pg.wait_for_timeout(100)
    appel_ok = pg.is_visible("#blocAppel")
    silence = pg.evaluate("document.getElementById('sonnerie').paused && !document.getElementById('decrocher').classList.contains('sonne')")
    suivant()                                   # appel
    visible(pg).locator("[data-galerie-ouvrir]").click(); pg.wait_for_timeout(100)
    compte = visible(pg).locator("[data-galerie-compte]").inner_text()
    for _ in range(3): visible(pg).locator("[data-galerie-suiv]").click()
    fin_galerie = visible(pg).locator("[data-galerie-compte]").inner_text()
    suivant()                                   # images
    suivant()                                   # sac
    botaniste = pg.inner_text("#titreEtape")
    video_bota = visible(pg).locator("video source").get_attribute("src")
    suivant()                                   # vidéo du botaniste
    bloque = not visible(pg).locator("[data-suivant]").is_visible()
    faux = None
    if aide:
        pg.click("#codeAide")
    else:
        pg.fill("#codeDemo", "1234"); pg.click("#validerCode"); pg.wait_for_timeout(80)
        faux = pg.is_visible("#codeFaux")
        pg.fill("#codeDemo", " 58 24 "); pg.press("#codeDemo", "Enter")
    pg.wait_for_timeout(100)
    ouvert = pg.is_visible("#codeBon") and visible(pg).locator("[data-suivant]").is_visible()
    suivant()                                   # porte de la serre
    visible(pg).locator(".quiz-prop", has_text=choix).click(); pg.wait_for_timeout(150)
    suivant()                                   # vidéo de la serre
    suivant()                                   # lettre
    verdict = visible(pg).locator("[data-denouement]:not([hidden])")
    out = {"sonne": sonne, "silence": silence, "titres": titres, "comptes": comptes, "appel": appel_ok, "galerie": (compte, fin_galerie),
           "bloque": bloque, "faux": faux, "ouvert": ouvert, "botaniste": botaniste, "video_bota": video_bota,
           "verdict": verdict.get_attribute("data-denouement") if verdict.count() == 1 else None,
           "etincelles": pg.locator(".etincelle").count()}
    suivant()                                   # verdict
    out["coulisses"] = pg.inner_text("#titreEtape")
    out["capture"] = pg.evaluate("[...document.querySelectorAll('.capture')].every(i => i.complete && i.naturalWidth > 0)")
    suivant()                                   # coulisses
    out["fin"] = pg.inner_text("#titreEtape")
    out["site"] = visible(pg).locator('a[href="https://www.pomelolab.fr"]').count() == 1
    out["externes"] = [u for u in pg.__appels if not u.startswith("http://127.0.0.1")
                       and "b-cdn.net" not in u and "fonts.g" not in u]
    out["erreurs"] = pg.__err
    pg.close()
    return out

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

    print("\nLe parcours complet, avec la bonne réponse")
    r = jouer(nav, "Elle s'est endormie.")
    note("14 écrans, de l'accueil au contact", r["fin"].lower() == "et chez vous ?", r)
    note("le grand titre suit l'étape", [t.lower() for t in r["titres"][:3]] ==
         ["le sanctuaire des brumes", "le commissaire jean", "appel du commissaire"], r["titres"])
    note("la barre compte de 1 / 6 à 6 / 6", r["comptes"][1] == "1 / 6" and "6 / 6" in r["comptes"], r["comptes"])
    note("le botaniste vient après le sac, avec sa vidéo", r["botaniste"].lower() == "louis, le botaniste"
         and r["video_bota"].endswith("le-botaniste-acanpa-2.mp4"), (r["botaniste"], r["video_bota"]))
    note("le téléphone sonne à l'arrivée sur l'appel", r["sonne"])
    note("l'appel se décroche", r["appel"])
    note("la sonnerie s'arrête quand on décroche", r["silence"])
    note("la galerie défile de 1/4 à 4/4", r["galerie"] == ("1 / 4", "4 / 4"), r["galerie"])
    note("la porte de la serre bloque la suite tant qu'elle est fermée", r["bloque"])
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
        note("« J'ai perdu le code » ouvre aussi la serre", r["ouvert"])

    print("\nQuitter l'appel sans décrocher")
    pg = nouvelle_page(nav); pg.goto(URL); pg.wait_for_timeout(300)
    for _ in range(3):
        visible(pg).locator("[data-suivant]").click(); pg.wait_for_timeout(150)
    sonne = pg.evaluate("!document.getElementById('sonnerie').paused")
    visible(pg).locator("[data-retour]").click(); pg.wait_for_timeout(150)
    coupe = pg.evaluate("document.getElementById('sonnerie').paused")
    note("revenir en arrière coupe la sonnerie", sonne and coupe, (sonne, coupe))
    pg.close()

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
