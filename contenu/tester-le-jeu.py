# -*- coding: utf-8 -*-
"""Joue le parcours dans un vrai navigateur, sans toucher a Supabase.

    python3 contenu/tester-le-jeu.py

Sert le site sur un serveur local, pose une fausse partie en cours et
remplace la base par un bouchon, puis clique reellement dans les pages :
enchainement des ecrans, tri selon le sens du groupe, enregistrement du
passage, epreuve a reponse verifiee, et bornes de saisie du nombre de joueurs.

Necessite Chromium. Le chemin ci-dessous est celui de l'environnement de
developpement ; a adapter ailleurs.
"""
import sys, os, threading, functools, http.server, socketserver
from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8137
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

class Muet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

socketserver.TCPServer.allow_reuse_address = True   # relance immediate possible
srv = socketserver.TCPServer(("127.0.0.1", 0),
        functools.partial(Muet, directory=RACINE))
PORT = srv.server_address[1]                        # port libre choisi par l'OS
threading.Thread(target=srv.serve_forever, daemon=True).start()

# Remplace Supabase et pose une session valide, AVANT tout script de la page.
def init(sens):
    # Ce test ne porte pas sur le verrouillage du parcours (il a le sien) :
    # on declare donc toutes les bornes comme deja visitees, pour que chaque
    # page s'ouvre et qu'on puisse verifier ce qu'elle affiche.
    import json as _j
    txt = open(os.path.join(RACINE, "assets/js/parcours.js")).read()
    noms = _j.loads(txt.split("const PARCOURS =", 1)[1].rstrip().rstrip(";"))["noms"]
    tous = _j.dumps([{"qr_points": {"label": n}} for n in noms.values()], ensure_ascii=False)
    return """
    window.__scans = [];
    window.supabase = { createClient: () => ({
      // Depuis le correctif 6, le passage d'une borne s'enregistre par un
      // guichet (rpc) et non plus par une ecriture directe dans la table.
      rpc: async (nom, args) => { if (nom === "enregistrer_passage") window.__scans.push(args);
                                  return { data: { ok: true }, error: null }; },
      from: (t) => ({
      select: () => ({ eq: (...a) => (t === "scans"
                        ? Promise.resolve({ data: %s, error: null })
                        : ({ maybeSingle: async () => ({ data: { id: 'pt-1' } }) })) }),
      insert: async (row) => { window.__scans.push(row); return {}; } }) }) };""" % tous + """
    localStorage.setItem("sdb_session", JSON.stringify({
      codeId: "c1", code: "TEST", direction: "%s",
      expiresAt: "2099-01-01T00:00:00Z", participantName: "Test", nbJoueurs: 1 }));
    """ % sens

import json as _json
PARC = _json.loads(open(os.path.join(RACINE, "assets/js/parcours.js")).read()
                   .split("const PARCOURS =", 1)[1].rstrip().rstrip(";"))

echecs = []
def verifier(nom, condition, detail=""):
    print("   %-38s %s %s" % (nom, "OK " if condition else "ECHEC", "" if condition else detail))
    if not condition: echecs.append(nom)

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

    for fichier, sens, pos_attendue, libelle in [
        (PARC["pages"]["E02"], "horaire",     "Étape 2 sur 15", "sens A"),
        (PARC["pages"]["E02"], "antihoraire", "Étape 8 sur 15", "sens B"),
        (PARC["pages"]["E09"], "antihoraire", "",               "borne de l'autre sens"),
    ]:
        page = nav.new_page()
        page.add_init_script(init(sens))
        page.goto("http://127.0.0.1:%d/%s" % (PORT, fichier))
        page.wait_for_timeout(300)
        print("\n%s  [%s]" % (fichier, libelle))

        verifier("pas de redirection", "/index.html" not in page.url, page.url)
        verifier("position affichee", page.text_content("#position").strip() == pos_attendue,
                 repr(page.text_content("#position")))
        scans = page.evaluate("window.__scans")
        verifier("passage enregistre une fois", len(scans) == 1, str(scans))
        verifier("un seul ecran visible",
                 page.eval_on_selector_all(".ecran", "e=>e.filter(x=>!x.hidden).length") == 1)
        # aucun ecran de l'autre sens ne doit subsister
        autre = "B" if sens == "horaire" else "A"
        verifier("ecrans de l'autre sens retires",
                 page.eval_on_selector_all('[data-sens="%s"]' % autre, "e=>e.length") == 0)

        total = page.eval_on_selector_all(".ecran", "e=>e.length")
        vus = 1
        while vus < 15:
            b = page.query_selector(".ecran:not([hidden]) [data-suivant]")
            if not b: break
            b.click(); page.wait_for_timeout(60); vus += 1
        verifier("tous les ecrans parcourus", vus == total, "%d sur %d" % (vus, total))
        sortie = page.query_selector(".ecran:not([hidden]) a.btn")
        if libelle == "borne de l'autre sens":
            verifier("message au lieu d'un cul-de-sac",
                     "pas votre borne" in page.text_content(".ecran:not([hidden])").lower())
        else:
            verifier("le dernier ecran mene ailleurs", sortie is not None)
        page.close()

    # Le raccourci ne doit exister que pour les codes de test
    print("\nLe raccourci vers l'etape suivante")
    for code, attendu, libelle in [("TEST01", True, "code de test"), ("AB12CD", False, "vrai code")]:
        page = nav.new_page()
        page.add_init_script(init("horaire").replace('code: "TEST"', 'code: "%s"' % code))
        page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E02"]))
        page.wait_for_timeout(250)
        present = page.eval_on_selector_all("[data-lien-test]", "e=>e.length") > 0
        verifier("%s : raccourci %s" % (libelle, "present" if attendu else "absent"),
                 present == attendu)
        # la consigne d'aller scanner est la dans les deux cas
        page.eval_on_selector_all(".ecran", "e=>e.forEach(x=>x.hidden=false)")
        verifier("%s : consigne de scan affichee" % libelle,
                 "scannez le QR code" in page.text_content(".wrap"))
        page.close()

    # L'epreuve a reponse verifiee
    print("\ne08 : l'epreuve du panneau d'empreintes")
    page = nav.new_page(); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E08"]))
    page.wait_for_timeout(300)
    page.query_selector(".ecran:not([hidden]) [data-suivant]").click(); page.wait_for_timeout(60)
    page.fill("#reponse", "7"); page.click("#valider")
    verifier("mauvaise reponse : pas de lettre", page.eval_on_selector("#resultat", "e=>e.hidden"))
    page.fill("#reponse", "11"); page.click("#valider")
    verifier("bonne reponse : la lettre S",
             not page.eval_on_selector("#resultat", "e=>e.hidden")
             and page.text_content(".lettre").strip() == "S")
    page.close()

    # L'accueil : saisie a 1 joueur
    print("\nindex.html : demarrage en solo")
    page = nav.new_page(); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/index.html" % PORT)
    page.wait_for_timeout(200)
    page.click("#versSaisie")
    page.fill("#participantName", "Solo"); page.fill("#nbJoueurs", "1")
    page.fill("#codeInput", "TEST01"); page.check("#acceptRules")
    verifier("1 joueur accepte", not page.eval_on_selector("#startBtn", "e=>e.disabled"))
    page.fill("#nbJoueurs", "7")
    verifier("7 joueurs refuses", page.eval_on_selector("#startBtn", "e=>e.disabled"))
    page.fill("#nbJoueurs", "6")
    verifier("6 joueurs acceptes", not page.eval_on_selector("#startBtn", "e=>e.disabled"))
    page.close()
    nav.close()

srv.shutdown()
print("\n" + "=" * 62)
print("ECHECS : %d %s" % (len(echecs), echecs if echecs else ""))
sys.exit(1 if echecs else 0)
