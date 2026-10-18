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
import sys, os, re, threading, functools, http.server, socketserver
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
    const SENS = "%s";
    window.__scans = []; window.__signalements = [];
    window.supabase = { createClient: () => ({
      // Depuis le correctif 6, le passage d'une borne s'enregistre par un
      // guichet (rpc) et non plus par une ecriture directe dans la table.
      rpc: async (nom, args) => {
        // Le journal des guichets appeles survit au rechargement de la page.
        try { const l = JSON.parse(sessionStorage.getItem("__rpcs") || "[]");
              l.push([nom, args]); sessionStorage.setItem("__rpcs", JSON.stringify(l)); } catch (e) { }
        if (nom === "enregistrer_passage") { window.__scans.push(args);
          return { data: { ok: true }, error: null }; }
        if (nom === "donner_avis") { (window.__avis = window.__avis || []).push(args);
          return { data: { ok: !window.__avisEnPanne }, error: null }; }
        if (nom === "enregistrer_conclusions") { window.__scans.push(args);
          return { data: { ok: true }, error: null }; }
        if (nom === "reprendre_partie") {
          const c = (args.p_code || "").trim().toUpperCase();
          if (c === "FINI0000") return { data: { ok: false,
            message: "Ce code a déjà servi et sa partie est terminée. Adressez-vous à l'accueil du zoo." }, error: null };
          if (c === "NEUF0000") return { data: { ok: false, pas_commencee: true,
            message: "Cette enquête n'a pas encore commencé." }, error: null };
          if (c !== "K7NPX4RT") return { data: { ok: false,
            message: "Ce code n'existe pas." }, error: null };
          return { data: { ok: true, code_id: "c1", code: c, direction: SENS,
            expires_at: "2099-01-01T00:00:00Z" }, error: null }; }
        // Le guichet rend le sens inscrit sur le code, pas un sens fixe :
        // sans cela, impossible de tester ce que voit un billet antihoraire.
        if (nom === "activer_code") return { data: { ok: true, code_id: "c1",
          code: (args.p_code || "").toUpperCase(), direction: SENS,
          expires_at: "2099-01-01T00:00:00Z" }, error: null };
        return { data: { ok: true }, error: null }; },
      from: (t) => ({
      select: () => ({ eq: (...a) => (t === "scans"
                        ? Promise.resolve({ data: %s, error: null })
                        : ({ maybeSingle: async () => ({ data: { id: 'pt-1' } }) })) }),
      insert: async (row) => { (t === "signalements" ? window.__signalements
                                 : window.__scans).push(row); return {}; } }) }) };""" % (sens, tous) + """
    localStorage.setItem("sdb_session", JSON.stringify({
      codeId: "c1", code: "TEST", direction: "%s",
      expiresAt: "2099-01-01T00:00:00Z", participantName: "Test", nbJoueurs: 1 }));
    """ % sens

import json as _json
PARC = _json.loads(open(os.path.join(RACINE, "assets/js/parcours.js")).read()
                   .split("const PARCOURS =", 1)[1].rstrip().rstrip(";"))

echecs = []
def nouvelle_page(nav):
    """Une page de test qui ne va pas chercher les videos chez l'hebergeur.

    Les pages portent l'adresse reelle des medias. Les telecharger n'apprend
    rien sur le jeu : ca ralentit chaque chargement, ca depend du reseau, et
    un jour ou l'hebergeur repond lentement des controles qui n'ont rien a
    voir avec la video se mettent a echouer. C'est arrive.

    On coupe donc court, explicitement. Les bornes sont ainsi testees dans
    le pire cas, celui ou la video ne descend pas : c'est exactement la
    situation du reseau d'un parc un dimanche de novembre.
    """
    page = nav.new_page()
    page.route("**/*.mp4", lambda r: r.abort())
    page.route("**/*.mp3", lambda r: r.abort())
    # Jamais de vrai mail depuis les tests : l'alerte Formspree est coupee
    # (les tests qui la verifient la remplacent par une reponse d'avance).
    page.route("**/formspree.io/**", lambda r: r.abort())
    return page


def verifier(nom, condition, detail=""):
    print("   %-38s %s %s" % (nom, "OK " if condition else "ECHEC", "" if condition else detail))
    if not condition: echecs.append(nom)

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

    for fichier, sens, pos_attendue, libelle in [
        (PARC["pages"]["E02"], "horaire",     (2, 15), "sens A"),
        (PARC["pages"]["E02"], "antihoraire", (8, 15), "sens B"),
        (PARC["pages"]["E09"], "antihoraire", None,    "borne de l'autre sens"),
    ]:
        page = nouvelle_page(nav)
        page.add_init_script(init(sens))
        page.goto("http://127.0.0.1:%d/%s" % (PORT, fichier))
        page.wait_for_timeout(300)
        print("\n%s  [%s]" % (fichier, libelle))

        verifier("pas de redirection", "/index.html" not in page.url, page.url)
        # La ligne « Étape 2 sur 15 » est devenue une barre. Sur une borne de
        # l'autre sens, elle est retiree plutot que remplie a zero, ce qui
        # ferait croire au groupe qu'il est revenu au debut.
        etat = page.evaluate("""() => {
          const z = document.getElementById("position");
          if (!z) return { absente: true };
          return { absente: false, hidden: z.hidden,
                   texte: z.getAttribute("aria-valuetext"),
                   compte: z.querySelector(".progression-compte").textContent,
                   part: getComputedStyle(z).getPropertyValue("--part").trim() };
        }""")
        if pos_attendue:
            n, total = pos_attendue
            verifier("barre de progression affichee",
                     not etat["absente"] and not etat["hidden"], str(etat))
            verifier("elle annonce la bonne etape",
                     etat.get("texte") == "Étape %d sur %d" % (n, total), str(etat))
            verifier("le compte est juste",
                     etat.get("compte") == "%d / %d" % (n, total), str(etat))
            verifier("le remplissage est proportionnel",
                     etat.get("part") == "%d%%" % round(n / total * 100), str(etat))
        else:
            verifier("barre retiree sur la borne de l'autre sens",
                     etat["absente"], str(etat))
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
            # Une question bonus n'offre « Continuer » qu'une fois repondu :
            # c'est le principe, on ne passe pas devant sans la voir. Le
            # promeneur repond donc, n'importe quoi fera l'affaire.
            bonus = page.query_selector(
                ".ecran:not([hidden])[data-popquiz] [data-bonus-prop]")
            if bonus: bonus.click(); page.wait_for_timeout(60)
            b = page.query_selector(".ecran:not([hidden]) [data-suivant]")
            if not b or not b.is_visible(): break
            b.click(); page.wait_for_timeout(60); vus += 1
        verifier("tous les ecrans parcourus", vus == total, "%d sur %d" % (vus, total))
        sortie = page.query_selector(".ecran:not([hidden]) a.btn")
        if libelle == "borne de l'autre sens":
            verifier("message au lieu d'un cul-de-sac",
                     "pas votre borne" in page.text_content(".ecran:not([hidden])").lower())
        else:
            verifier("le dernier ecran mene ailleurs", sortie is not None)
        page.close()

    # Le cas qui a bloque les essais sur le terrain : le QR s'ouvre dans un
    # navigateur qui n'a pas la partie en memoire (lecteur de codes de
    # l'iPhone, Google Lens, onglet prive). Chaque new_page() ouvre un
    # contexte vierge, exactement comme ces lecteurs. Tous les autres tests
    # posent la session d'avance, et c'est pour cela qu'aucun ne l'a vu.
    print("\nUne borne ouverte dans un navigateur sans la partie")
    sans_partie = init("horaire").split('localStorage.setItem("sdb_session"')[0]
    page = nouvelle_page(nav); page.add_init_script(sans_partie)
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E02"]))
    page.wait_for_timeout(300)
    verifier("on reste sur la borne", "/index.html" not in page.url, page.url)
    verifier("le code est demande", page.is_visible("#codeReprise"))
    verifier("aucun ecran de jeu avant le code",
             page.eval_on_selector_all(".ecran:not(#retrouverPartie)", "e=>e.length") == 0)
    verifier("aucun passage enregistre sans partie",
             len(page.evaluate("window.__scans")) == 0)
    diag = page.evaluate("window.__signalements")
    verifier("un diagnostic part au tableau de bord",
             len(diag) == 1 and diag[0]["categorie"] == "bug"
             and "Bornes visitées en mémoire : non" in diag[0]["message"]
             and len(diag[0]["message"]) <= 500, str(diag))
    verifier("demarrer est propose", page.is_visible("#versAccueil"))
    page.fill("#codeReprise", "zzzz"); page.click("#validerReprise")
    page.wait_for_timeout(200)
    verifier("code inconnu : message, on reste",
             page.is_visible("#erreurReprise") and "/index.html" not in page.url)
    page.fill("#codeReprise", " k7npx4rt ")
    # On attend le CHANGEMENT DE PAGE, pas un delai au juge. Une attente
    # fixe apres un clic qui recharge la borne est une course : la machine
    # est parfois lente, et deux controles sans rapport avec la reprise se
    # mettaient a echouer une fois sur dix.
    with page.expect_navigation():
        page.click("#validerReprise")
    page.wait_for_timeout(400)
    verifier("partie retrouvee, toujours sur la borne",
             page.url.endswith(PARC["pages"]["E02"]), page.url)
    verifier("la borne s'affiche",
             page.eval_on_selector_all(".ecran", "e=>e.filter(x=>!x.hidden).length") == 1
             and not page.is_visible("#codeReprise"))
    verifier("le passage est enregistre", len(page.evaluate("window.__scans")) == 1)
    page.close()

    # Code jamais active, saisi sur une borne : ce groupe n'a pas demarre.
    # On l'envoie a l'accueil avec son code, sans rien activer en route.
    page = nouvelle_page(nav); page.add_init_script(sans_partie)
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E02"]))
    page.wait_for_timeout(300)
    page.fill("#codeReprise", "NEUF0000")
    with page.expect_navigation():
        page.click("#validerReprise")
    page.wait_for_timeout(400)
    verifier("code neuf : renvoye a l'accueil", "/index.html?code=NEUF0000" in page.url, page.url)
    verifier("code neuf : deja saisi a l'accueil",
             page.input_value("#codeInput") == "NEUF0000")
    verifier("code neuf : rien d'active en route",
             page.evaluate("localStorage.getItem('sdb_session')") is None)
    page.close()

    # ------------------------------------------------------------
    # LE DOUBLE SCAN AU DEPART
    #
    # Le chemin le plus frequent sur place : on prend son billet, on avance,
    # on voit le panneau du commissaire et on le scanne AVANT d'avoir
    # demarre. Le jeu envoyait alors a l'accueil, puis annoncait « rendez-
    # vous dans le jardin des Pivoines » a un groupe qui s'y trouvait deja,
    # et lui demandait de rescanner le QR code qu'il avait sous les yeux.
    #
    # On verifie les quatre cas, y compris les deux ou le renvoi doit etre
    # REFUSE : c'est la qu'une porte derobee se glisserait.
    # ------------------------------------------------------------
    print("\nLe QR de la premiere borne scanne avant d'avoir demarre")

    def demarrer_depuis(url_borne, code="K7NPX4RT", sens="horaire"):
        """Scanne une borne sans partie, puis demarre. Rend l'etat final."""
        pg = nouvelle_page(nav)
        pg.add_init_script(init(sens).split('localStorage.setItem("sdb_session"')[0])
        pg.goto(url_borne)
        pg.wait_for_timeout(400)
        with pg.expect_navigation():
            pg.click("#versAccueil")
        pg.wait_for_timeout(300)
        depuis = pg.url
        pg.click("#versSaisie")
        pg.fill("#participantName", "Eva"); pg.fill("#nbJoueurs", "4")
        pg.fill("#codeInput", code); pg.check("#acceptRules")
        pg.click("#startBtn"); pg.wait_for_timeout(600)
        etat = {
            "accueil": depuis,
            "propose": pg.is_visible("#dejaSurPlace"),
            "consigne_de_marche": pg.is_visible("#allerALaBorne"),
            "lien": pg.eval_on_selector("#versBorneScannee",
                                        "e => e.getAttribute('href')"),
        }
        return pg, etat

    url_e01 = "http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E01"])

    # Depuis l'inauguration, la borne du commissaire EST le depart : elle
    # accueille le groupe et ouvre la partie sur place, sans detour par la
    # page d'accueil ni second scan.
    def demarrer_au_commissaire(sens, code="K7NPX4RT"):
        pg = nouvelle_page(nav)
        pg.add_init_script(init(sens).split('localStorage.setItem("sdb_session"')[0])
        pg.goto(url_e01); pg.wait_for_timeout(400)
        etat = {"bienvenue": pg.is_visible("#accueilDepart"),
                "renvoi_accueil": pg.locator("#versAccueil").count() > 0,
                "diagnostic": len(pg.evaluate("window.__signalements"))}
        pg.click("#versSaisieDepart")
        etat["bouton_grise"] = pg.is_disabled("#startBtn")
        pg.fill("#participantName", "Eva"); pg.fill("#nbJoueurs", "4")
        pg.fill("#codeInput", code); pg.check("#acceptRules")
        with pg.expect_navigation():
            pg.click("#startBtn")
        pg.wait_for_timeout(600)
        etat.update({
            "url": pg.url,
            "ecrans": pg.eval_on_selector_all(".ecran", "e=>e.filter(x=>!x.hidden).length"),
            "formulaire": pg.locator("#saisieDepart").count(),
            "scans": len(pg.evaluate("window.__scans")),
            "conseil": pg.is_visible("#conseilScanner"),
            "session": pg.evaluate("localStorage.getItem('sdb_session') !== null"),
        })
        return pg, etat

    # Le nom d'equipe part en base, par son propre guichet, apres l'activation.
    pg, e = demarrer_au_commissaire("horaire")
    appels = pg.evaluate("JSON.parse(sessionStorage.getItem('__rpcs') || '[]')")
    noms = [a for a in appels if a[0] == "nommer_groupe"]
    verifier("le nom d'equipe est garde en base, apres l'activation",
             len(noms) == 1 and noms[0][1] == {"p_code_id": "c1", "p_nom": "Eva"}
             and [a[0] for a in appels].index("activer_code") < [a[0] for a in appels].index("nommer_groupe"),
             str(appels))
    pg.close()
    # Guichet absent (correctif 12 pas lance) : la partie demarre quand meme.
    _init = init
    def init(sens, _i=_init):
        return _i(sens).replace('rpc: async (nom, args) => {',
            'rpc: async (nom, args) => { if (nom === "nommer_groupe") '
            'return { data: null, error: { message: "Could not find the function" } };', 1)
    pg, e = demarrer_au_commissaire("horaire")
    verifier("sans le guichet du nom, la partie demarre quand meme",
             e["session"] and e["formulaire"] == 0 and e["ecrans"] == 1, str(e))
    pg.close()
    init = _init

    for sens in ("horaire", "antihoraire"):
        pg, e = demarrer_au_commissaire(sens)
        verifier("%s : bienvenue sur la borne" % sens, e["bienvenue"] and not e["renvoi_accueil"], str(e))
        verifier("%s : pas de diagnostic au depart" % sens, e["diagnostic"] == 0, str(e))
        verifier("%s : demarrer grise tant qu'il manque" % sens, e["bouton_grise"], str(e))
        verifier("%s : on reste sur la borne" % sens,
                 e["url"].split("?")[0].endswith(PARC["pages"]["E01"]), e["url"])
        verifier("%s : la borne s'ouvre, sans formulaire" % sens,
                 e["ecrans"] == 1 and e["formulaire"] == 0 and e["session"], str(e))
        verifier("%s : passage enregistre une fois" % sens, e["scans"] == 1, str(e))
        verifier("%s : le conseil du scanner s'affiche" % sens, e["conseil"], str(e))
        pg.close()

    # Un code refuse : le message de la base, et on reste sur le formulaire.
    pg = nouvelle_page(nav)
    pg.add_init_script(init("horaire").split('localStorage.setItem("sdb_session"')[0]
                       + 'window.supabase.createClient = ((f) => () => { const c = f(); '
                         'const r = c.rpc; c.rpc = async (n, a) => n === "activer_code" '
                         '? { data: { ok: false, message: "Ce code n\'existe pas." }, error: null } '
                         ': r(n, a); return c; })(window.supabase.createClient);')
    pg.goto(url_e01); pg.wait_for_timeout(300)
    pg.click("#versSaisieDepart")
    pg.fill("#participantName", "Eva"); pg.fill("#nbJoueurs", "4")
    pg.fill("#codeInput", "ZZZZ"); pg.check("#acceptRules")
    pg.click("#startBtn"); pg.wait_for_timeout(400)
    verifier("code refuse : message affiche", "existe pas" in pg.inner_text("#errorBox"))
    verifier("code refuse : on peut corriger", pg.is_enabled("#startBtn")
             and pg.evaluate("localStorage.getItem('sdb_session')") is None)
    pg.close()

    # REFUS 2 : une borne du milieu du parcours. Scanner le veterinaire en
    # arrivant ne doit pas ouvrir la septieme etape.
    pg, e = demarrer_depuis("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E07"]))
    verifier("borne du milieu : pas de raccourci", not e["propose"], str(e))
    pg.close()

    # REFUS 3 : une adresse bricolee a la main. Le parametre ne doit ouvrir
    # que ce que le plan du parcours connait.
    pg = nouvelle_page(nav)
    pg.add_init_script(init("horaire").split('localStorage.setItem("sdb_session"')[0])
    pg.goto("http://127.0.0.1:%d/index.html?borne=E99" % PORT)
    pg.wait_for_timeout(300)
    pg.click("#versSaisie")
    pg.fill("#participantName", "Eva"); pg.fill("#nbJoueurs", "4")
    pg.fill("#codeInput", "K7NPX4RT"); pg.check("#acceptRules")
    pg.click("#startBtn"); pg.wait_for_timeout(600)
    verifier("borne inventee : pas de raccourci", not pg.is_visible("#dejaSurPlace"))
    pg.close()

    # Le cas signale sur le terrain : un essai precedent a laisse une partie
    # au chrono ecoule, puis on scanne directement le QR du commissaire. La
    # borne renvoyait a l'accueil avec « session terminee » : impossible de
    # demarrer depuis le QR.
    print("\nUne ancienne partie expiree, puis le QR de la premiere borne")
    page = nouvelle_page(nav); page.add_init_script(sans_partie)
    page.add_init_script("""
      if (!sessionStorage.getItem("pose")) { sessionStorage.setItem("pose", "1");
        localStorage.setItem("sdb_session", JSON.stringify({ codeId:"vieux", code:"TEST01",
          direction:"horaire", expiresAt:"2020-01-01T00:00:00Z" }));
        localStorage.setItem("sdb_visites", JSON.stringify(["E01","E02","E03","E04"])); }
    """)
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E01"]))
    page.wait_for_timeout(300)
    verifier("on reste sur la borne", "/index.html" not in page.url, page.url)
    verifier("la bienvenue est proposee", page.is_visible("#accueilDepart"))
    verifier("l'ancienne partie est oubliee",
             page.evaluate("localStorage.getItem('sdb_session') === null"
                           " && localStorage.getItem('sdb_visites') === null"))
    verifier("pas de diagnostic pour un depart normal",
             len(page.evaluate("window.__signalements")) == 0)
    page.close()

    # Un vrai billet dont la partie est close (la base le confirme) : on ne
    # l'invite pas a redemarrer.
    page = nouvelle_page(nav); page.add_init_script(sans_partie)
    page.add_init_script("""
      localStorage.setItem("sdb_session", JSON.stringify({ codeId:"c9", code:"FINI0000",
        direction:"horaire", expiresAt:"2020-01-01T00:00:00Z" }));
    """)
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E01"]))
    page.wait_for_timeout(300)
    verifier("vrai billet expire : enquete terminee",
             page.is_visible("#partieTerminee") and not page.is_visible("#versAccueil"))
    verifier("vrai billet expire : aucun ecran de jeu",
             page.eval_on_selector_all(".ecran:not(#partieTerminee)", "e=>e.length") == 0)
    verifier("vrai billet expire : aucun passage enregistre",
             len(page.evaluate("window.__scans")) == 0)
    page.close()

    # Une nouvelle partie efface les bornes visitees par la precedente.
    page = nouvelle_page(nav); page.add_init_script(sans_partie)
    page.add_init_script("""
      if (!sessionStorage.getItem("pose")) { sessionStorage.setItem("pose", "1");
        localStorage.setItem("sdb_session", JSON.stringify({ codeId:"vieux", code:"X",
          direction:"horaire", expiresAt:"2020-01-01T00:00:00Z" }));
        localStorage.setItem("sdb_visites", JSON.stringify(["E01","E02","E03"])); }
    """)
    page.goto("http://127.0.0.1:%d/index.html" % PORT)
    page.wait_for_timeout(200)
    page.click("#versSaisie")
    page.fill("#participantName", "Eva"); page.fill("#nbJoueurs", "2")
    page.fill("#codeInput", "K7NPX4RT"); page.check("#acceptRules")
    page.click("#startBtn"); page.wait_for_timeout(300)
    verifier("nouvelle partie : anciennes visites effacees",
             page.evaluate("localStorage.getItem('sdb_visites')") is None)
    page.close()

    # Le raccourci ne doit exister que pour les codes de test
    print("\nLe raccourci vers l'etape suivante")
    for code, attendu, libelle in [("TEST01", True, "code de test"), ("AB12CD", False, "vrai code")]:
        page = nouvelle_page(nav)
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

    # ------------------------------------------------------------
    # L'EPREUVE DU PANNEAU D'EMPREINTES
    #
    # Tout tient sur un seul ecran : la photo, la consigne et la reponse.
    # Et surtout, on ne bloque personne. Au deuxieme essai manque, le jeu
    # donne le numero ET la lettre : quatre personnes debout devant un
    # panneau un dimanche de novembre abandonnent avant de chercher
    # longtemps, et cette lettre leur est necessaire pour finir.
    # ------------------------------------------------------------
    print("\ne08 : l'epreuve du panneau d'empreintes")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E08"]))
    page.wait_for_timeout(300)
    verifier("tout est sur le premier ecran",
             page.is_visible("#reponse") and page.is_visible(".photo-borne"))
    verifier("la photo est bien l'empreinte",
             "empreinte-renard" in page.eval_on_selector(".photo-borne",
                                                         "e=>e.getAttribute('src')"))
    page.fill("#reponse", "7"); page.click("#valider")
    page.wait_for_timeout(100)
    verifier("premier essai manque : pas de lettre, mais on reessaie",
             page.eval_on_selector("#resultat", "e=>e.hidden")
             and not page.eval_on_selector("#aCote", "e=>e.hidden")
             and not page.eval_on_selector("#reponse", "e=>e.disabled"))
    page.fill("#reponse", "11"); page.click("#valider")
    page.wait_for_timeout(100)
    verifier("bonne reponse : la lettre S",
             not page.eval_on_selector("#resultat", "e=>e.hidden")
             and page.text_content(".lettre").strip() == "S")
    verifier("et plus de message d'erreur",
             page.eval_on_selector("#aCote", "e=>e.hidden"))
    page.close()

    # Deux essais manques : on donne le numero et la lettre quand meme.
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E08"]))
    page.wait_for_timeout(300)
    for essai in ("7", "3"):
        page.fill("#reponse", essai); page.click("#valider")
        page.wait_for_timeout(100)
    bloque = page.evaluate("""() => ({
        lettre: !document.getElementById("resultat").hidden,
        titre: document.getElementById("resultatTitre").textContent,
        message: document.getElementById("aCote").textContent })""")
    verifier("deux essais manques : la lettre est donnee quand meme",
             bloque["lettre"], str(bloque))
    verifier("et le bon numero est annonce", "11" in bloque["titre"], str(bloque))
    page.close()

    # ------------------------------------------------------------
    # LE SAC PERDU : les photos, puis le nombre qu'elles cachent
    # ------------------------------------------------------------
    print("\ne11 : le sac perdu")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E11"]))
    page.wait_for_timeout(300)
    verifier("rien ne s'affiche avant d'avoir clique sur Voir",
             page.eval_on_selector("[data-galerie-vue]", "e=>e.hidden"))
    page.click("[data-galerie-ouvrir]"); page.wait_for_timeout(150)
    vue = lambda: page.evaluate("""() => {
        const p = Array.from(document.querySelectorAll("[data-galerie-photo]"));
        return { total: p.length,
                 visible: p.findIndex(x => !x.hidden),
                 compte: document.querySelector("[data-galerie-compte]").textContent,
                 prec: document.querySelector("[data-galerie-prec]").disabled,
                 suiv: document.querySelector("[data-galerie-suiv]").disabled }; }""")
    v = vue()
    # Le nombre de photos vient du sac reel (les fichiers sac-N.webp du
    # depot), pas d'un chiffre ecrit ici : ajouter une photo au sac ne doit
    # pas casser le test.
    import glob as _glob
    N = len(_glob.glob(os.path.join(RACINE, "assets/img/sac-*.webp")))
    verifier("%d photos, la premiere a l'ecran" % N,
             v["total"] == N and v["visible"] == 0 and v["compte"] == "1 / %d" % N, str(v))
    verifier("on ne peut pas remonter avant la premiere", v["prec"], str(v))
    for _ in range(N - 1):
        page.click("[data-galerie-suiv]"); page.wait_for_timeout(80)
    v = vue()
    verifier("on fait defiler jusqu'a la derniere",
             v["visible"] == N - 1 and v["compte"] == "%d / %d" % (N, N) and v["suiv"], str(v))

    # Le nombre cache. Deux essais manques et on le donne : il est
    # indispensable pour entrer dans la serre.
    page.query_selector(".ecran:not([hidden]) [data-suivant]").click()
    page.wait_for_timeout(120)
    page.fill("#codeTrouve", "1234"); page.click("#validerCode")
    page.wait_for_timeout(100)
    verifier("un mauvais nombre ne donne rien, mais on reessaie",
             page.eval_on_selector("#codeJuste", "e=>e.hidden")
             and not page.eval_on_selector("#codeTrouve", "e=>e.disabled"))
    page.fill("#codeTrouve", "5824"); page.click("#validerCode")
    page.wait_for_timeout(100)
    verifier("5824 est le nombre cache dans le sac",
             not page.eval_on_selector("#codeJuste", "e=>e.hidden"))
    verifier("et on ne dit pas encore a quoi il sert",
             "serre" not in page.text_content(".ecran:not([hidden])").lower())
    page.close()

    # ------------------------------------------------------------
    # LA PORTE DE LA SERRE
    # ------------------------------------------------------------
    print("\ne14 : la porte de la serre")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E14"]))
    page.wait_for_timeout(300)
    while not page.is_visible("#codeSerre"):
        b = page.query_selector(".ecran:not([hidden]) [data-suivant]")
        if not b or not b.is_visible(): break
        b.click(); page.wait_for_timeout(100)
    verifier("la porte demande un code", page.is_visible("#codeSerre"))
    page.fill("#codeSerre", "0000"); page.click("#validerSerre")
    page.wait_for_timeout(100)
    verifier("un mauvais code n'ouvre pas",
             page.eval_on_selector("#serreOuverte", "e=>e.hidden"))
    page.fill("#codeSerre", "5824"); page.click("#validerSerre")
    page.wait_for_timeout(100)
    verifier("5824 ouvre la serre",
             not page.eval_on_selector("#serreOuverte", "e=>e.hidden"))
    page.close()

    # Personne ne reste dehors a la derniere etape de trois heures d'enquete.
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E14"]))
    page.wait_for_timeout(300)
    while not page.is_visible("#codePerdu"):
        b = page.query_selector(".ecran:not([hidden]) [data-suivant]")
        if not b or not b.is_visible(): break
        b.click(); page.wait_for_timeout(100)
    page.click("#codePerdu"); page.wait_for_timeout(150)
    verifier("« j'ai perdu le code » ouvre quand meme",
             not page.eval_on_selector("#serreOuverte", "e=>e.hidden"))
    verifier("et annonce le code", "5824" in page.text_content("#serreACote"))
    page.close()

    # L'accueil : saisie a 1 joueur
    print("\nindex.html : demarrage en solo")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
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

    # L'ecran de depart etait la seule porte qui laissait commencer l'enquete
    # sans scanner un QR code : un joueur pouvait la franchir assis a la
    # caisse. On verifie que le raccourci reste reserve aux codes de test.
    # Le bouton « Revenir en arriere » du premier ecran ne faisait rien : il
    # n'y a pas d'ecran avant. Il ramene maintenant a la borne precedente,
    # pour revoir un temoignage.
    # L'ecran de sortie, celui qui indique le chemin, n'avait aucun bouton de
    # retour. C'est pourtant celui ou le joueur reste le plus longtemps : une
    # fois arrive la, il ne pouvait plus revoir la video sans le bouton
    # « precedent » de son telephone.
    # La lettre s'affichait des le scan : le joueur recevait la reponse avant
    # d'avoir leve les yeux. Elle passe derriere une question.
    # Le cahier met "/" dans une case pour dire « rien ici ». Le generateur
    # fabriquait quand meme l'ecran : une carte vide, deux boutons, et un
    # Suivant a appuyer pour rien.
    print("\nAucune borne n'affiche d'ecran vide")
    vides = []
    for code, page_borne in PARC["pages"].items():
        page = nouvelle_page(nav); page.add_init_script(init("horaire"))
        page.goto("http://127.0.0.1:%d/%s" % (PORT, page_borne))
        page.wait_for_timeout(250)
        n = page.evaluate("""() => [...document.querySelectorAll('.ecran')].filter(
              e => !e.querySelector('video, audio, img, input, p')).length""")
        if n: vides.append("%s (%d)" % (code, n))
        page.close()
    verifier("toutes les bornes ont du contenu partout",
             not vides, ", ".join(vides))

    print("\nL'enclos des loups ne donne plus la lettre d'emblee")
    for reponse, doit_voir in (("[data-indice-non]", True), ("[data-suivant]", False)):
        page = nouvelle_page(nav); page.add_init_script(init("horaire"))
        page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E04"]))
        page.wait_for_timeout(400)
        libelle = "Non" if doit_voir else "Oui"
        verifier("%s : pas de lettre au premier ecran" % libelle,
                 page.query_selector(".ecran:not([hidden]) .lettre") is None)
        page.click(".ecran:not([hidden]) [data-suivant]"); page.wait_for_timeout(200)
        verifier("%s : la question est posee" % libelle,
                 "trouvé l'indice" in (page.text_content(".ecran:not([hidden])") or ""))
        verifier("%s : la lettre est encore cachee" % libelle,
                 not page.is_visible(".ecran:not([hidden]) .lettre"))
        page.click(".ecran:not([hidden]) " + reponse); page.wait_for_timeout(250)
        if doit_voir:
            verifier("Non : la lettre R apparait",
                     page.is_visible(".ecran:not([hidden]) .lettre")
                     and (page.text_content(".ecran:not([hidden]) .lettre") or "").strip() == "R")
        else:
            verifier("Oui : on passe a la suite sans la lettre",
                     page.query_selector(".ecran:not([hidden]) .plan-chemin") is not None
                     or "Où aller" in (page.text_content(".ecran:not([hidden])") or ""))
        page.close()

    print("\nDepuis l'ecran de sortie, on peut remonter jusqu'a la video")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E01"]))
    page.wait_for_timeout(400)
    for _ in range(6):
        b = page.query_selector(".ecran:not([hidden]) [data-suivant]")
        if not b: break
        b.click(); page.wait_for_timeout(120)
    verifier("on est bien sur l'ecran du chemin",
             page.query_selector(".ecran:not([hidden]) .plan-chemin") is not None)
    verifier("un bouton de retour y figure",
             page.is_visible(".ecran:not([hidden]) [data-retour]"))
    for _ in range(6):
        i = page.evaluate("""() => [...document.querySelectorAll('.ecran')]
                                    .findIndex(e => !e.hidden)""")
        if i == 0: break
        page.click(".ecran:not([hidden]) [data-retour]"); page.wait_for_timeout(150)
    verifier("on remonte jusqu'a la video",
             page.query_selector(".ecran:not([hidden]) video") is not None)
    page.close()

    print("\nRevoir le temoignage precedent")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))

    # On commence par PARCOURIR la borne du commissaire jusqu'a son dernier
    # ecran. C'est indispensable : chaque borne se souvient de l'ecran ou on
    # l'a quittee, et c'est ce souvenir qui ramenait le joueur sur « ou aller
    # ensuite » au lieu de la video. Sans ce passage, le test s'ouvrirait sur
    # un souvenir vide et passerait sans rien prouver.
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E01"]))
    page.wait_for_timeout(400)
    for _ in range(6):
        suivant = page.query_selector(".ecran:not([hidden]) [data-suivant]")
        if not suivant: break
        suivant.click(); page.wait_for_timeout(120)
    dernier = page.evaluate("""() => [...document.querySelectorAll('.ecran')]
                                      .findIndex(e => !e.hidden)""")
    verifier("le commissaire se quitte sur son dernier ecran", dernier > 0, str(dernier))

    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E02"]))
    page.wait_for_timeout(400)
    b1 = page.query_selector(".ecran:not([hidden]) [data-retour]")
    verifier("premier ecran : le bouton propose de revoir",
             b1 is not None and not b1.is_hidden()
             and "témoignage" in (b1.text_content() or ""),
             repr(b1 and b1.text_content()))
    b1.click(); page.wait_for_timeout(500)
    verifier("il mene bien a la borne d'avant",
             page.url.endswith(PARC["pages"]["E01"] + "?revoir=E02"), page.url)
    # On vient revoir une video : la borne doit s'ouvrir sur son PREMIER ecran,
    # pas sur celui ou on l'avait quittee. Elle s'en souvient pourtant, et
    # c'est utile quand un telephone se verrouille : les deux besoins se
    # contredisent, celui-ci gagne.
    verifier("elle s'ouvre sur son premier ecran",
             page.evaluate("""() => [...document.querySelectorAll('.ecran')]
                                    .findIndex(e => !e.hidden)""") == 0)
    verifier("la video est bien la",
             page.query_selector(".ecran:not([hidden]) video") is not None)
    retour = page.query_selector(".retour-borne")
    verifier("un retour vers sa propre borne est propose",
             retour is not None and PARC["noms"]["E02"] in (retour.text_content() or ""),
             repr(retour and retour.text_content()))
    retour.click(); page.wait_for_timeout(500)
    verifier("ce retour ramene a la bonne borne",
             page.url.endswith(PARC["pages"]["E02"]), page.url)
    page.close()

    # Le groupe remonte DEUX bornes pour revoir des temoignages : le bouton
    # doit le ramener a la borne la plus avancee qu'il avait atteinte, pas a
    # l'avant-derniere (cas signale le 18/10, coince a la passante).
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E04"])); page.wait_for_timeout(500)
    page.goto("http://127.0.0.1:%d/%s?revoir=E04" % (PORT, PARC["pages"]["E03"])); page.wait_for_timeout(400)
    page.goto("http://127.0.0.1:%d/%s?revoir=E03" % (PORT, PARC["pages"]["E02"])); page.wait_for_timeout(400)
    retour = page.query_selector(".retour-borne")
    verifier("deux bornes en arriere : retour propose vers la plus avancee",
             retour is not None and PARC["noms"]["E04"] in (retour.text_content() or ""),
             repr(retour and retour.text_content()))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E02"])); page.wait_for_timeout(400)
    retour = page.query_selector(".retour-borne")
    verifier("meme sans ?revoir, une borne deja depassee propose le retour",
             retour is not None and PARC["noms"]["E04"] in (retour.text_content() or ""),
             repr(retour and retour.text_content()))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E04"])); page.wait_for_timeout(400)
    verifier("sur sa borne la plus avancee : pas de bouton de retour",
             page.query_selector(".retour-borne") is None)
    page.close()

    # Sur la borne de depart il n'y a rien avant : le bouton disparait plutot
    # que de rester la sans rien faire.
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E01"]))
    page.wait_for_timeout(700)
    b0 = page.query_selector(".ecran:not([hidden]) [data-retour]")
    verifier("borne de depart : le bouton est retire",
             b0 is None or b0.is_hidden())
    # Une adresse ?revoir= fantaisiste ne doit rien ouvrir.
    page.goto("http://127.0.0.1:%d/%s?revoir=ZZZ" % (PORT, PARC["pages"]["E01"]))
    page.wait_for_timeout(400)
    verifier("un code de retour inconnu est ignore",
             page.query_selector(".retour-borne") is None)
    page.close()

    # Reculer trop loin fait sortir du parcours et ramene a l'accueil. Le
    # joueur doit pouvoir reprendre sans retaper son code, que le groupe a
    # peut-etre garde.
    print("\nindex.html : reprendre une enquete en cours")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.add_init_script("""
      localStorage.setItem("sdb_session", JSON.stringify({ codeId:"c1", code:"TEST01",
        direction:"horaire", expiresAt: new Date(Date.now()+3600000).toISOString(),
        participantName:"Eva", nbJoueurs:2 }));
      localStorage.setItem("sdb_visites", JSON.stringify(["E01","E02","E03"]));
    """)
    page.goto("http://127.0.0.1:%d/index.html" % PORT)
    page.wait_for_timeout(400)
    verifier("le bouton est propose", page.is_visible("#reprendre"))
    verifier("il vise la borne la plus avancee",
             (page.get_attribute("#reprendre", "href") or "").endswith(PARC["pages"]["E03"]),
             repr(page.get_attribute("#reprendre", "href")))
    page.close()

    # Une partie finie ne se reprend pas : le bouton n'a rien a faire la.
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.add_init_script("""
      localStorage.setItem("sdb_session", JSON.stringify({ codeId:"c1", code:"TEST01",
        direction:"horaire", expiresAt: "2020-01-01T00:00:00Z",
        participantName:"Eva", nbJoueurs:2 }));
    """)
    page.goto("http://127.0.0.1:%d/index.html" % PORT)
    page.wait_for_timeout(400)
    verifier("partie expiree : pas de bouton", not page.is_visible("#reprendre"))
    page.close()

    print("\nindex.html : les quatre champs sont obligatoires")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/index.html" % PORT)
    page.wait_for_timeout(200)
    page.click("#versSaisie")
    manquants = [
        ("nom d'equipe", "#participantName", "Les Limiers", "le nom de votre équipe"),
        ("nombre de joueurs", "#nbJoueurs", "3",            "le nombre de joueurs"),
        ("code",              "#codeInput", "TEST01",       "votre code"),
    ]
    for libelle, champ, valeur, attendu in manquants:
        verifier("%s : signale comme manquant" % libelle,
                 attendu in page.text_content("#ceQuiManque"),
                 repr(page.text_content("#ceQuiManque")))
        verifier("%s : bouton bloque" % libelle,
                 page.eval_on_selector("#startBtn", "e=>e.disabled"))
        page.fill(champ, valeur)
    verifier("consignes : signalees comme manquantes",
             "consignes" in page.text_content("#ceQuiManque"),
             repr(page.text_content("#ceQuiManque")))
    verifier("consignes : bouton encore bloque",
             page.eval_on_selector("#startBtn", "e=>e.disabled"))
    page.check("#acceptRules")
    verifier("tout rempli : bouton ouvert",
             not page.eval_on_selector("#startBtn", "e=>e.disabled"))
    verifier("tout rempli : plus rien a signaler",
             page.text_content("#ceQuiManque").strip() == "",
             repr(page.text_content("#ceQuiManque")))
    page.fill("#participantName", "   ")
    verifier("un nom fait d'espaces ne compte pas",
             page.eval_on_selector("#startBtn", "e=>e.disabled"))
    page.close()

    print("\nindex.html : l'ecran de depart n'ouvre plus la premiere borne")
    for code, attendu, libelle in [("TEST01", True, "code de test"),
                                   ("K7NPX4RT", False, "vrai code")]:
        page = nouvelle_page(nav); page.add_init_script(init("horaire"))
        page.goto("http://127.0.0.1:%d/index.html" % PORT)
        page.wait_for_timeout(200)
        page.click("#versSaisie")
        page.fill("#participantName", "Eva"); page.fill("#nbJoueurs", "2")
        page.fill("#codeInput", code); page.check("#acceptRules")
        page.click("#startBtn"); page.wait_for_timeout(300)
        visible = page.eval_on_selector_all(
            "#versPremiereBorne", "e => e.length === 1 && !e[0].hidden")
        verifier("%s : raccourci %s" % (libelle, "propose" if attendu else "retire"),
                 visible == attendu)
        verifier("%s : secours propose" % libelle,
                 page.is_visible("#boutonSecours"))
        page.close()

    # Le nombre a quatre chiffres de l'affichette doit ouvrir la borne, et
    # sans empiler les dossiers : /8055/ et non /index.html/8055/.
    print("\nindex.html : le secours a quatre chiffres")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/index.html" % PORT)
    page.wait_for_timeout(200)
    page.click("#versSaisie")
    page.fill("#participantName", "Eva"); page.fill("#nbJoueurs", "2")
    page.fill("#codeInput", "K7NPX4RT"); page.check("#acceptRules")
    page.click("#startBtn"); page.wait_for_timeout(300)
    page.click("#boutonSecours")
    page.fill("#champSecours", "8055")
    page.click("#validerSecours"); page.wait_for_timeout(400)
    attendue = "http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E01"])
    verifier("ouvre bien la borne du commissaire", page.url == attendue, page.url)
    page.close()

    # ------------------------------------------------------------
    # L'HEURE DE FIN VIENT DE LA BASE (correctif 13 : plus de chrono de 3 h)
    # ------------------------------------------------------------
    print("\nL'heure de fin redemandee a la base")
    # Fin depassee d'apres le telephone, mais la base a prolonge : on joue.
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.add_init_script("""
      localStorage.setItem("sdb_session", JSON.stringify({ codeId:"c1", code:"K7NPX4RT",
        direction:"horaire", expiresAt:"2020-01-01T00:00:00Z", participantName:"Eva" }));
    """)
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E02"])); page.wait_for_timeout(500)
    s_ = page.evaluate("JSON.parse(localStorage.getItem('sdb_session'))")
    verifier("prolongee par la base : la partie continue",
             not page.query_selector("#partieTerminee")
             and page.eval_on_selector_all(".ecran", "e=>e.filter(x=>!x.hidden).length") == 1, str(s_))
    verifier("le telephone garde la nouvelle heure de fin, et son nom d'equipe",
             s_["expiresAt"].startswith("2099") and s_.get("participantName") == "Eva", str(s_))
    verifier("plus de compte a rebours a l'ecran", not page.query_selector("#timer"))
    page.close()
    # Fin lointaine d'apres le telephone, mais la base a clos (reponse finale
    # rendue il y a plus de 30 minutes) : la borne le dit.
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.add_init_script("""
      localStorage.setItem("sdb_session", JSON.stringify({ codeId:"c1", code:"FINI0000",
        direction:"horaire", expiresAt:"2099-01-01T00:00:00Z" }));
    """)
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E02"])); page.wait_for_timeout(500)
    verifier("close par la base : enquete terminee", page.is_visible("#partieTerminee"))
    page.close()
    # Fin depassee d'apres le telephone (ancien chrono de 3 h) et base muette :
    # on ne ferme pas l'enquete sur la seule foi du telephone.
    page = nouvelle_page(nav)
    page.add_init_script(init("horaire").replace('rpc: async (nom, args) => {',
        'rpc: async (nom, args) => { if (nom === "reprendre_partie") throw new Error("reseau");', 1))
    page.add_init_script("""
      localStorage.setItem("sdb_session", JSON.stringify({ codeId:"c1", code:"K7NPX4RT",
        direction:"horaire", expiresAt:"2020-01-01T00:00:00Z" }));
    """)
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E02"])); page.wait_for_timeout(600)
    verifier("fin depassee sur le telephone, base muette : la partie continue",
             not page.query_selector("#partieTerminee")
             and page.eval_on_selector_all(".ecran", "e=>e.filter(x=>!x.hidden).length") == 1
             and "/index.html" not in page.url, page.url)
    page.close()

    # La base ne repond pas : on ne coupe personne.
    page = nouvelle_page(nav)
    page.add_init_script(init("horaire").replace('rpc: async (nom, args) => {',
        'rpc: async (nom, args) => { if (nom === "reprendre_partie") throw new Error("reseau");', 1))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E02"])); page.wait_for_timeout(500)
    verifier("base muette : la partie continue",
             not page.query_selector("#partieTerminee")
             and page.eval_on_selector_all(".ecran", "e=>e.filter(x=>!x.hidden).length") == 1)
    page.close()

    # ------------------------------------------------------------
    # LE MOT DES QUATRE LETTRES (IRIS), au bureau de Greg en sens A.
    # Juste : felicitations, et le lieu reste a chercher, avec un indice
    # a la demande. Faux deux fois : le mot est donne, sans felicitations.
    # ------------------------------------------------------------
    print("\ne13 : le mot des quatre lettres")

    def jouer_mot(essais, indice=False):
        pg = nouvelle_page(nav); pg.add_init_script(init("horaire"))
        borne = PARC["pages"]["E13"]
        # Droit a l'ecran « Ou aller ensuite » : les precedents ont leurs tests.
        pg.add_init_script("sessionStorage.setItem('sdb_ecran_/%s', '2')" % borne)
        pg.goto("http://127.0.0.1:%d/%s" % (PORT, borne))
        pg.wait_for_timeout(300)
        for m in essais:
            pg.fill("#motFinal", m); pg.click("#validerMot"); pg.wait_for_timeout(100)
        if indice:
            pg.click("[data-mot-trouve] [data-coup-de-pouce-ouvrir]"); pg.wait_for_timeout(100)
        r = pg.evaluate("""() => {
          const t = document.querySelector("[data-mot-trouve]");
          const i = t.querySelector("[data-coup-de-pouce-texte]");
          const a = document.querySelector("[data-apres-mot]");
          return { trouve: !t.hidden, bravo: t.querySelector("[data-mot-bravo]").textContent,
                   indice: !i.hidden, lieu: i.textContent,
                   bouton: !t.querySelector("[data-coup-de-pouce-ouvrir]").hidden,
                   scanner: !!a && !a.hidden,
                   faux: document.querySelector("[data-mot-faux]").textContent }; }""")
        pg.close()
        return r

    r = jouer_mot(["iris"])
    verifier("le bon mot : felicitations", r["trouve"] and r["bravo"].startswith("Félicitations"), str(r))
    verifier("le lieu n'est pas donne d'office", r["bouton"] and not r["indice"], str(r))
    verifier("le scanner apparait", r["scanner"], str(r))
    r = jouer_mot(["iris"], indice=True)
    verifier("« Demander un indice » donne le Jardin des Iris",
             r["indice"] and "Jardin des Iris" in r["lieu"] and not r["bouton"], str(r))
    r = jouer_mot(["sire", "riss"])
    verifier("deux essais manques : le mot est donne, sans felicitations",
             r["trouve"] and "IRIS" in r["faux"] and "Félicitations" not in r["bravo"]
             and r["bouton"] and r["scanner"], str(r))

    # ------------------------------------------------------------
    # LA FIN DE L'ENQUETE, a la serre.
    #
    # Quatre propositions. Le choix mene droit a la video, SANS verdict ;
    # puis la lettre de Greg ; puis le verdict, avec les etincelles si le
    # groupe avait vu juste ; puis le photocall, sur son ecran ; puis les
    # remerciements. Le choix est verrouille : revenir en arriere apres la
    # video ne permet pas de le changer.
    # ------------------------------------------------------------
    print("\ne15 : les conclusions a choix")

    ETAT_FIN = """() => {
      const vis = Array.from(document.querySelectorAll(".ecran")).find(x => !x.hidden);
      const d = Array.from(document.querySelectorAll("[data-denouement]")).filter(x => !x.hidden);
      return { video: !!(vis && vis.querySelector("video")),
               lettre: !!(vis && vis.querySelector("img.photo-borne")),
               verdictEcran: !!(vis && vis.hasAttribute("data-verdict-final")),
               photocall: !!(vis && vis.classList.contains("photocall")),
               fin: !!(vis && vis.querySelector(".partenaires")),
               choix: !!(vis && vis.querySelector("[data-conclusions]")),
               denouement: d.length === 1 ? d[0].getAttribute("data-denouement") : (d.length ? "plusieurs" : null),
               fete: !!document.querySelector(".celebration"),
               verrou: Array.from(document.querySelectorAll("[data-conclusion]")).every(b => b.disabled),
               rangements: (window.__scans || []).filter(x => x && x.p_denouement)
                             .map(x => x.p_denouement) }; }"""

    def suivant(pg):
        pg.locator(".ecran:not([hidden]) [data-suivant]:visible").first.click()
        pg.wait_for_timeout(150)

    def conclure(choix, base_muette=False):
        pg = nouvelle_page(nav)
        i = init("horaire")
        if base_muette:
            i = i.replace('rpc: async (nom, args) => {',
                          'rpc: async (nom, args) => { if (nom === "enregistrer_conclusions") '
                          'throw new Error("base injoignable");')
        pg.add_init_script(i)
        pg.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E15"]))
        pg.wait_for_timeout(300)
        etapes = {}
        for _ in range(4):
            if pg.is_visible("[data-conclusions]"): break
            suivant(pg)
        etapes["avant"] = pg.evaluate(ETAT_FIN)
        pg.locator("[data-conclusion]").nth(choix).click(); pg.wait_for_timeout(200)
        etapes["video"] = pg.evaluate(ETAT_FIN)
        suivant(pg); etapes["lettre"] = pg.evaluate(ETAT_FIN)
        suivant(pg); pg.wait_for_timeout(200); etapes["verdict"] = pg.evaluate(ETAT_FIN)
        if etapes["verdict"]["fete"]:
            pg.click("#celebrationFermer"); pg.wait_for_timeout(600)
            etapes["verdict"]["fete_fermee"] = not pg.query_selector(".celebration")
        suivant(pg); etapes["photocall"] = pg.evaluate(ETAT_FIN)
        suivant(pg); etapes["avis"] = pg.is_visible("[data-avis]")
        suivant(pg); etapes["fin"] = pg.evaluate(ETAT_FIN)
        # Retour jusqu'au choix : il est verrouille.
        for _ in range(8):
            if pg.is_visible("[data-conclusions]"): break
            pg.locator(".ecran:not([hidden]) [data-retour]").first.click(); pg.wait_for_timeout(100)
        etapes["retour"] = pg.evaluate(ETAT_FIN)
        pg.close()
        return etapes

    # Les fins des propositions, lues dans la page : le cahier peut changer.
    FINS = re.findall(r'data-conclusion="\d+" data-fin="([^"]+)"',
                      open(os.path.join(RACINE, PARC["pages"]["E15"], "index.html")).read())
    verifier("cinq propositions, une seule juste",
             len(FINS) == 5 and FINS.count("Bon") == 1, str(FINS))
    verifier("la bonne reponse n'est pas la derniere", FINS and FINS[-1] != "Bon", str(FINS))
    verifier("l'empoisonnement mene a la fin intermediaire", "Moyen" in FINS, str(FINS))
    BONNE = FINS.index("Bon")
    for choix, attendue in enumerate(FINS):
        juste = (attendue == "Bon")
        f = conclure(choix)
        nom = "reponse %d (%s)" % (choix + 1, attendue)
        verifier(nom + " : le choix est propose apres l'accueil", f["avant"]["choix"], str(f["avant"]))
        verifier(nom + " : droit a la video, sans verdict",
                 f["video"]["video"] and f["video"]["denouement"] is None and not f["video"]["fete"],
                 str(f["video"]))
        verifier(nom + " : puis la lettre de Greg, toujours sans verdict",
                 f["lettre"]["lettre"] and f["lettre"]["denouement"] is None, str(f["lettre"]))
        verifier(nom + " : puis son verdict",
                 f["verdict"]["verdictEcran"] and f["verdict"]["denouement"] == attendue,
                 str(f["verdict"]))
        verifier(nom + " : etincelles " + ("oui" if juste else "non"),
                 f["verdict"]["fete"] == juste and f["verdict"].get("fete_fermee", True), str(f["verdict"]))
        verifier(nom + " : le photocall, l'avis, puis les remerciements",
                 f["photocall"]["photocall"] and f["avis"] and f["fin"]["fin"],
                 str(f["photocall"]) + str(f["avis"]) + str(f["fin"]))
        verifier(nom + " : la reponse est rangee une fois",
                 f["verdict"]["rangements"] == [attendue],
                 str(f["verdict"]["rangements"]))
        verifier(nom + " : de retour au choix, il est verrouille",
                 f["retour"]["choix"] and f["retour"]["verrou"], str(f["retour"]))

    # « Alors, cette enquete vous a plu ? »
    def ouvrir_avis(en_panne=False):
        pg = nouvelle_page(nav)
        pg.add_init_script(init("horaire") + ("window.__avisEnPanne = true;" if en_panne else ""))
        n = open(os.path.join(RACINE, PARC["pages"]["E15"], "index.html")).read()
        rang = n.count('<section class="ecran', 0, n.index('<section class="ecran card avis"'))
        pg.add_init_script("sessionStorage.setItem('sdb_ecran_/%s', '%d')" % (PARC["pages"]["E15"], rang))
        pg.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E15"])); pg.wait_for_timeout(300)
        return pg
    pg = ouvrir_avis()
    verifier("l'avis : envoyer est grise sans note",
             pg.is_visible("[data-avis]") and pg.is_disabled("#envoyerAvis"))
    pg.locator(".etoile").nth(3).click()
    allumees = pg.eval_on_selector_all(".etoile.allumee", "e=>e.length")
    pg.fill("#avisTexte", "  Super enquête !  ")
    pg.click("#envoyerAvis"); pg.wait_for_timeout(300)
    envoi = pg.evaluate("window.__avis || []")
    verifier("quatre etoiles touchees, quatre allumees", allumees == 4, str(allumees))
    verifier("l'avis part avec la note et le mot",
             len(envoi) == 1 and envoi[0]["p_note"] == 4 and envoi[0]["p_texte"] == "Super enquête !"
             and envoi[0]["p_code_id"] == "c1", str(envoi))
    verifier("merci affiche, formulaire replie, « Passer » devient « Suivant »",
             pg.is_visible("#avisMerci") and not pg.is_visible("#envoyerAvis")
             and pg.text_content("[data-avis-suivant]").strip() == "Suivant")
    g = pg.query_selector("#avisGoogle")
    verifier("le bouton « Laisser un avis Google » est propose apres l'envoi",
             g is not None and g.is_visible() and "share.google" in (g.get_attribute("href") or "")
             and g.get_attribute("target") == "_blank")
    pg.reload(); pg.wait_for_timeout(300)
    verifier("deja donne : on ne redemande pas", pg.is_visible("#avisMerci") and not pg.is_visible(".etoile"))
    pg.close()
    pg = ouvrir_avis(en_panne=True)
    pg.locator(".etoile").nth(4).click(); pg.click("#envoyerAvis"); pg.wait_for_timeout(300)
    verifier("envoi rate : message poli, on peut reessayer ou passer",
             pg.is_visible("#avisRate") and pg.is_enabled("#envoyerAvis")
             and pg.is_visible("[data-avis] [data-suivant]"))
    pg.close()

    # Et surtout : la fin s'affiche meme si la base ne repond pas.
    f = conclure(BONNE, base_muette=True)
    verifier("la base muette n'empeche pas la fin",
             f["video"]["video"] and f["verdict"]["denouement"] == "Bon" and f["fin"]["fin"],
             str(f["verdict"]))

    # ------------------------------------------------------------
    # « J'AI UN PROBLEME » : la base ET un mail (Formspree). L'un des deux
    # suffit pour dire au joueur que l'equipe est prevenue.
    # ------------------------------------------------------------
    print("\nLe signalement d'un joueur, par mail aussi")

    def signaler(mail_ok=True, base_ok=True):
        pg = nouvelle_page(nav)
        i = init("horaire")
        if not base_ok:
            i = i.replace('insert: async (row) => {',
                          'insert: async (row) => { if (t === "signalements") '
                          'return { error: { message: "base injoignable" } };')
        pg.add_init_script(i)
        mails = []
        pg.unroute("**/formspree.io/**")
        def formspree(r):
            mails.append(_json.loads(r.request.post_data))
            if mail_ok: r.fulfill(status=200, content_type="application/json", body='{"ok":true}')
            else: r.abort()
        pg.route("**/formspree.io/**", formspree)
        pg.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E10"]))
        pg.wait_for_timeout(300)
        pg.click("#boutonProbleme")
        pg.select_option("#categorieProbleme", "qr")
        pg.fill("#messageProbleme", "Le QR est décollé")
        pg.fill("#telProbleme", "06 12 34 56 78")
        pg.click("#envoyerProbleme"); pg.wait_for_timeout(600)
        r = {"mails": mails, "base": len(pg.evaluate("window.__signalements")),
             "retour": pg.text_content("#retourProbleme")}
        pg.close()
        return r

    r = signaler()
    m = r["mails"][0] if r["mails"] else {}
    verifier("un mail part, avec la borne, le type et le message",
             len(r["mails"]) == 1 and m.get("_subject", "").startswith("⚠ Problème signalé : QR code, ")
             and "Le QR est décollé" in m.get("message", "") and m.get("borne")
             and m.get("telephone") == "06 12 34 56 78" and "06 12 34 56 78" in m.get("_subject", "")
             and "TEST" in m.get("groupe", ""), str(r["mails"]))
    verifier("et le signalement arrive en base, comme avant", r["base"] == 1, str(r))
    verifier("le joueur est rassure", "nous allons vous appeler" in r["retour"], r["retour"])
    r = signaler(base_ok=False)
    verifier("base muette, mail parti : le joueur est rassure quand meme",
             "nous allons vous appeler" in r["retour"], r["retour"])
    r = signaler(mail_ok=False)
    verifier("mail en panne, base a jour : le joueur est rassure", "nous allons vous appeler" in r["retour"], r["retour"])
    # Sans numero, rien ne part : c'est par lui qu'on debloque le groupe.
    pg = nouvelle_page(nav); pg.add_init_script(init("horaire"))
    envois = []
    pg.unroute("**/formspree.io/**"); pg.route("**/formspree.io/**", lambda r: (envois.append(1), r.abort()))
    pg.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E10"])); pg.wait_for_timeout(300)
    pg.click("#boutonProbleme"); pg.click("#envoyerProbleme"); pg.wait_for_timeout(300)
    verifier("sans numero : on le demande, rien ne part",
             pg.is_visible("#telManquant") and not envois
             and len(pg.evaluate("window.__signalements")) == 0)
    pg.close()
    r = signaler(mail_ok=False, base_ok=False)
    verifier("les deux en panne : on lui dit de prevenir l'equipe", "pas parti" in r["retour"], r["retour"])

    # Les diagnostics automatiques ne font jamais partir de mail.
    pg = nouvelle_page(nav)
    pg.add_init_script(init("horaire").split('localStorage.setItem("sdb_session"')[0])
    mails = []
    pg.unroute("**/formspree.io/**")
    pg.route("**/formspree.io/**", lambda r: (mails.append(1), r.abort()))
    pg.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E10"])); pg.wait_for_timeout(500)
    verifier("un diagnostic automatique n'envoie pas de mail",
             len(pg.evaluate("window.__signalements")) == 1 and not mails,
             str(pg.evaluate("window.__signalements")))
    pg.close()

    # ------------------------------------------------------------
    # LES QUESTIONS BONUS
    #
    # Elles surgissent sans QR code. Une seule tentative : qui repond juste
    # du premier coup gagne un indice que les autres n'auront pas. On ne
    # bloque jamais — une mauvaise reponse coute l'indice, pas la suite.
    #
    # Rien n'est ecrit en dur : on lit la bonne reponse dans la page, donc
    # le cahier peut changer de question sans rendre ce test faux.
    # ------------------------------------------------------------
    print("\nLes questions bonus")

    def ouvrir_bonus(code):
        pg = nouvelle_page(nav); pg.add_init_script(init("horaire"))
        pg.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"][code]))
        pg.wait_for_timeout(400)
        return pg

    def etat_bonus(pg):
        return pg.evaluate("""() => {
          const z = document.querySelector("[data-popquiz]");
          if (!z) return null;
          const p = Array.from(z.querySelectorAll("[data-bonus-prop]"));
          const s = z.querySelector("[data-bonus-suivant]");
          return { bonne: parseInt(z.getAttribute("data-bonne"), 10),
                   nbProps: p.length,
                   bloquees: p.every(b => b.disabled),
                   gagne: !z.querySelector("[data-bonus-gagne]").hidden,
                   rate: !z.querySelector("[data-bonus-rate]").hidden,
                   suivant: !!s && !s.hidden,
                   visible: !z.hidden,
                   consigne: z.querySelector(".popquiz-consigne").textContent };
        }""")

    # La question de Sophie arrive AU SCAN : c'est le premier ecran.
    page = ouvrir_bonus("E03")
    e = etat_bonus(page)
    verifier("la question bonus s'affiche des le scan",
             e and e["visible"] and e["nbProps"] == 4, str(e))
    verifier("la consigne est celle d'Eva",
             "indice supplémentaire" in e["consigne"], e["consigne"])
    verifier("rien n'est revele avant de repondre",
             not e["gagne"] and not e["rate"], str(e))
    verifier("et on ne peut pas passer outre", not e["suivant"], str(e))

    # Bonne reponse : l'indice tombe.
    page.locator("[data-bonus-prop]").nth(e["bonne"]).click()
    page.wait_for_timeout(200)
    juste = etat_bonus(page)
    verifier("bonne reponse : l'indice est donne",
             juste["gagne"] and not juste["rate"], str(juste))
    verifier("les propositions se verrouillent", juste["bloquees"], str(juste))
    verifier("et la suite s'ouvre", juste["suivant"], str(juste))

    # Un second clic ne doit rien changer : une seule tentative.
    faux_n = 0 if e["bonne"] != 0 else 1
    page.locator("[data-bonus-prop]").nth(faux_n).dispatch_event("click")
    page.wait_for_timeout(150)
    apres = etat_bonus(page)
    verifier("un second clic ne retire pas l'indice",
             apres["gagne"] and not apres["rate"], str(apres))
    page.close()

    # Mauvaise reponse : pas d'indice, mais la borne continue.
    page = ouvrir_bonus("E03")
    e = etat_bonus(page)
    page.locator("[data-bonus-prop]").nth(0 if e["bonne"] != 0 else 1).click()
    page.wait_for_timeout(200)
    rate = etat_bonus(page)
    verifier("mauvaise reponse : pas d'indice",
             rate["rate"] and not rate["gagne"], str(rate))
    verifier("mais la borne reste jouable", rate["suivant"], str(rate))
    page.click("[data-bonus-suivant]"); page.wait_for_timeout(200)
    verifier("et on passe bien a la suite",
             page.eval_on_selector_all(
                 ".ecran:not([hidden])[data-popquiz]", "e=>e.length") == 0)
    page.close()

    # Chez Greg, la question vient APRES le temoignage, avant le chemin.
    page = ouvrir_bonus("E09")
    verifier("chez Greg, la question n'arrive pas au scan",
             page.eval_on_selector_all(
                 ".ecran:not([hidden])[data-popquiz]", "e=>e.length") == 0)
    for _ in range(6):
        b = page.query_selector(".ecran:not([hidden]) [data-suivant]")
        if not b or not b.is_visible(): break
        b.click(); page.wait_for_timeout(120)
        if page.eval_on_selector_all(
               ".ecran:not([hidden])[data-popquiz]", "e=>e.length"): break
    verifier("mais elle arrive avant l'ecran du chemin",
             page.eval_on_selector_all(
                 ".ecran:not([hidden])[data-popquiz]", "e=>e.length") == 1)
    page.close()

    # ------------------------------------------------------------
    # LE QUIZ QUI SUIT LA VIDEO (borne Sabri & Arez)
    #
    # On ne lit pas de vraie video ici : le code du quiz ne connait de la
    # video que son currentTime et ses evenements. On remplace donc la
    # lecture par une horloge qu'on avance a la main. Le test devient
    # instantane et reproductible, et il verifie exactement le contrat.
    #
    # Aucune minute n'est ecrite en dur : elles sont lues dans la page.
    # Le cahier peut changer de questions, d'horaires ou de nombre de
    # propositions sans que ce test devienne faux sans prevenir.
    #
    # La balise <source> est retiree de la page avant chargement, sinon le
    # navigateur signale un fichier introuvable (la video n'est pas encore
    # chez l'hebergeur) et le filet de securite ouvrirait le quiz d'un coup.
    # ------------------------------------------------------------
    print("\nE06 : le quiz se deroule au rythme de la video")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    def sans_source(route):
        page_e06 = open(os.path.join(RACINE, PARC["pages"]["E06"], "index.html"),
                        encoding="utf-8").read()
        route.fulfill(status=200, content_type="text/html; charset=utf-8",
                      body=re.sub(r"<source[^>]*>", "", page_e06))
    page.route("**/%s/**" % PARC["pages"]["E06"].rstrip("/"), sans_source)
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E06"]))
    page.wait_for_timeout(300)

    plan = page.evaluate("""() => {
      const z = document.querySelector("[data-quiz]");
      return { delai: parseFloat(z.getAttribute("data-delai")),
               verdict: parseFloat(z.getAttribute("data-verdict-delai")),
               t: Array.from(z.querySelectorAll("[data-question]"))
                       .map(q => parseFloat(q.getAttribute("data-t"))),
               bonnes: Array.from(z.querySelectorAll("[data-question]"))
                       .map(q => parseInt(q.getAttribute("data-bonne"), 10)) };
    }""")
    N, DELAI, T, VERDICT = len(plan["t"]), plan["delai"], plan["t"], plan["verdict"]
    verifier("le cahier fournit au moins trois questions", N >= 3, str(N))

    etat = lambda: page.evaluate("""(n) => {
      const z = document.querySelector("[data-quiz]");
      const qs = Array.from(z.querySelectorAll("[data-question]"));
      const b  = z.querySelector("[data-bilan]");
      const s  = document.querySelector("[data-quiz-suivant]");
      const ouverte = qs.findIndex(q => !q.hidden);
      return { zone: !z.hidden, nbOuvertes: qs.filter(q => !q.hidden).length,
               ouverte: ouverte,
               bilan: !b.hidden, score: b.querySelector("[data-score]").textContent,
               lettre: (b.querySelector(".lettre") || {}).textContent || "",
               suivant: !!s && !s.hidden, pleinEcran: !!document.fullscreenElement,
               bouton: s ? s.textContent.trim() : "",
               // La lettre ne doit pas etre lisible a l'arrivee : sur cette
               // borne elle se merite au bout du quiz, pas au scan.
               lettreVue: Array.from(document.querySelectorAll(".lettre"))
                               .some(x => x.offsetParent !== null),
               attente: !z.querySelector("[data-attente]").hidden,
               reste: ouverte < 0 ? "" :
                      qs[ouverte].querySelector("[data-reste]").textContent,
               chrono: ouverte >= 0 &&
                       !qs[ouverte].querySelector("[data-chrono]").hidden };
    }""", N)

    e0 = etat()
    verifier("rien avant la lecture",
             not e0["zone"] and e0["nbOuvertes"] == 0 and not e0["bilan"]
             and not e0["lettreVue"], str(e0))
    # Demande du terrain : un groupe presse peut passer la video. Il perd les
    # points, pas la lettre, qui est sur l'ecran d'apres.
    verifier("« Passer la vidéo » n'est pas propose au depart",
             not e0["suivant"], str(e0))

    # Une horloge a la place de la lecture.
    page.evaluate("""() => {
      const v = document.querySelector("[data-quiz-video]");
      window.__t = 0;
      Object.defineProperty(v, "currentTime", { get: () => window.__t });
      window.__avancer = (t, ev) => { window.__t = t;
        v.dispatchEvent(new Event(ev || "timeupdate")); };
      v.dispatchEvent(new Event("play"));
    }""")
    e1 = etat()
    verifier("la lecture ouvre le quiz, sans question",
             e1["zone"] and e1["nbOuvertes"] == 0, str(e1))
    verifier("et l'ecran invite a ecouter", e1["attente"], str(e1))
    verifier("la video du quiz ne part pas en plein ecran", not e1["pleinEcran"])

    avancer = lambda t, ev="timeupdate": page.evaluate(
        "([t, e]) => window.__avancer(t, e)", [t, ev])
    question = lambda i: page.locator("[data-question]").nth(i)

    # --- La premiere question, et une mauvaise reponse ------------------
    avancer(T[0] + 5)
    e2 = etat()
    verifier("la premiere question apparait a son heure",
             e2["ouverte"] == 0 and e2["nbOuvertes"] == 1, str(e2))
    verifier("son compte a rebours decompte le delai du cahier",
             e2["chrono"] and e2["reste"] == "%d s" % (DELAI - 5), str(e2))

    faux = 0 if plan["bonnes"][0] != 0 else 1
    question(0).locator(".quiz-prop").nth(faux).click()
    # Deuxieme clic, sur la bonne cette fois : il doit rester sans effet. Le
    # bouton est desactive, donc on force l'evenement a la main — c'est bien
    # le verrou du code qu'on teste, pas celui du navigateur.
    question(0).locator(".quiz-prop").nth(plan["bonnes"][0]).dispatch_event("click")
    detail = page.evaluate("""(bonne) => {
      const q = document.querySelectorAll("[data-question]")[0];
      const p = q.querySelectorAll(".quiz-prop");
      return { verdict: q.querySelector("[data-verdict]").textContent,
               cachee: q.querySelector("[data-verdict]").hidden,
               bloquees: Array.from(p).every(b => b.disabled),
               bonneMontree: p[bonne].classList.contains("est-bonne"),
               chrono: q.querySelector("[data-chrono]").hidden };
    }""", plan["bonnes"][0])
    verifier("mauvaise reponse : le verdict s'affiche",
             not detail["cachee"] and "pas la bonne" in detail["verdict"], str(detail))
    verifier("la bonne reponse est montree, les boutons bloques",
             detail["bloquees"] and detail["bonneMontree"], str(detail))
    verifier("le compte a rebours disparait une fois repondu", detail["chrono"])

    # La question garde sa place pendant TOUT son compte a rebours, meme
    # repondue des la cinquieme seconde. La video affiche son propre chrono :
    # une question qui s'effacerait avant lui passerait pour un bug.
    avancer(T[0] + DELAI - 1)
    verifier("repondue tot, la question reste jusqu'au bout du chrono",
             etat()["ouverte"] == 0, str(etat()))
    # Puis le verdict s'attarde le temps d'etre lu.
    if VERDICT >= 2:
        avancer(T[0] + DELAI + VERDICT - 1)
        verifier("le verdict reste le temps d'etre lu",
                 etat()["ouverte"] == 0, str(etat()))
    else:
        print("   %-38s (SECONDES_DE_VERDICT = %g)"
              % ("le verdict ne s'attarde pas", VERDICT))
    avancer(T[0] + DELAI + VERDICT + 1)
    e2b = etat()
    verifier("puis la question s'efface",
             e2b["nbOuvertes"] == 0 and not e2b["bilan"], str(e2b))
    verifier("et l'ecran invite a ecouter la suivante", e2b["attente"], str(e2b))

    # --- LE CHOIX D'EVA : une question a la fois ------------------------
    avancer(T[1] + 1)
    e3 = etat()
    verifier("la question suivante REMPLACE la precedente",
             e3["ouverte"] == 1 and e3["nbOuvertes"] == 1, str(e3))

    # Dix secondes et personne n'a repondu : la question se verrouille et
    # nomme la bonne reponse. On perd le point, pas la lecon.
    avancer(T[1] + DELAI + 1)
    expiree = page.evaluate("""(bonne) => {
      const q = document.querySelectorAll("[data-question]")[1];
      const p = q.querySelectorAll(".quiz-prop");
      return { verdict: q.querySelector("[data-verdict]").textContent,
               bloquees: Array.from(p).every(b => b.disabled),
               bonneMontree: p[bonne].classList.contains("est-bonne"),
               nommee: q.querySelector("[data-verdict]").textContent
                        .includes(p[bonne].textContent),
               chrono: q.querySelector("[data-chrono]").hidden };
    }""", plan["bonnes"][1])
    verifier("passe le delai, la question expire",
             "Temps écoulé" in expiree["verdict"] and expiree["bloquees"]
             and expiree["bonneMontree"] and expiree["chrono"], str(expiree))
    verifier("et elle nomme la bonne reponse plutot que la designer",
             expiree["nommee"], expiree["verdict"])

    # Repondre apres l'heure ne rapporte rien.
    question(1).locator(".quiz-prop").nth(plan["bonnes"][1]).dispatch_event("click")

    # La question expiree s'efface elle aussi, une fois sa reponse lue.
    avancer(T[1] + DELAI + VERDICT + 1.5)
    e4b = etat()
    verifier("la question expiree s'efface a son tour",
             e4b["nbOuvertes"] == 0 and e4b["attente"], str(e4b))

    # Un joueur qui revient en arriere dans la video retrouve la question
    # de ce moment-la, dans l'etat ou il l'a laissee.
    avancer(T[0] + 1, "seeked")
    e4 = etat()
    verifier("retour en arriere : on retrouve la question de ce moment",
             e4["ouverte"] == 0 and e4["nbOuvertes"] == 1, str(e4))

    # « Passer la vidéo » n'arrive qu'a deux minutes, et reste ensuite.
    avancer(119)
    verifier("a 1:59, toujours pas de « Passer la vidéo »", not etat()["suivant"], str(etat()))
    avancer(120)
    e_p = etat()
    verifier("a 2:00, « Passer la vidéo » apparait",
             e_p["suivant"] and e_p["bouton"] == "Passer la vidéo", str(e_p))
    avancer(30, "seeked")
    verifier("et reste meme apres un retour en arriere", etat()["suivant"], str(etat()))

    # --- La derniere question, bien repondue ----------------------------
    avancer(T[N - 1] + 1)
    e5 = etat()
    verifier("la derniere question est seule a l'ecran",
             e5["ouverte"] == N - 1 and e5["nbOuvertes"] == 1, str(e5))
    question(N - 1).locator(".quiz-prop").nth(plan["bonnes"][N - 1]).click()

    # Le delai de la derniere question est ecoule, mais la video continue de
    # tourner : la lettre ne doit PAS tomber par-dessus le temoignage qui
    # suit. Le groupe n'a pas repondu a tout, rien ne doit se declencher.
    avancer(T[N - 1] + DELAI + VERDICT + 2)
    pas_encore = etat()
    verifier("la lettre n'arrive pas avant la fin de la video",
             not pas_encore["bilan"] and not pas_encore["lettreVue"],
             str(pas_encore))

    # C'est la fin de la video qui la declenche.
    avancer(T[N - 1] + DELAI + 60, "ended")
    fin = etat()
    verifier("le quiz fini, le bilan s'affiche",
             fin["bilan"] and fin["nbOuvertes"] == 0, str(fin))
    verifier("l'invitation a ecouter disparait avec le bilan",
             not fin["attente"], str(fin))
    verifier("une seule bonne reponse comptee sur %d" % N,
             ("1 bonne réponse sur %d" % N) in fin["score"], fin["score"])
    # La lettre n'est plus sous les questions : elle a son ecran, apres
    # « Suivant ». Elle arrive ainsi meme si la video n'a pas charge, ou si
    # le groupe l'a passee.
    verifier("la lettre n'est pas sur l'ecran du quiz",
             not fin["lettre"] and not fin["lettreVue"], str(fin))
    verifier("le bouton devient « Suivant »",
             fin["suivant"] and fin["bouton"] == "Suivant", str(fin))
    page.click("[data-quiz-suivant]")
    page.wait_for_timeout(200)
    lettre = page.evaluate("""() => { const l = Array.from(document.querySelectorAll('.lettre'))
                                   .find(x => x.offsetParent !== null);
                                 return l ? l.textContent.trim() : ""; }""")
    verifier("apres Suivant, l'ecran de la lettre", lettre == "I", lettre)
    page.close()

    # La video ne descend pas : fichier absent chez l'hebergeur, ou reseau
    # du parc qui lache en pleine partie. La borne doit rester jouable et la
    # sortie accessible, sinon le groupe est enferme. Sans video il n'y a
    # plus d'horloge, donc pas de compte a rebours : on montre la premiere
    # question, sans minuteur.
    #
    # La coupure est provoquee ici (nouvelle_page bloque les .mp4), et non
    # subie : ce controle passait jusqu'ici parce que le reseau de la
    # machine de developpement refuse l'hebergeur. Ailleurs il aurait
    # echoue sans rien reveler du jeu.
    print("\nE06 : si la video ne se charge pas, la borne reste jouable")
    page = nouvelle_page(nav); page.add_init_script(init("horaire"))
    page.goto("http://127.0.0.1:%d/%s" % (PORT, PARC["pages"]["E06"]))
    page.wait_for_timeout(500)
    sans = etat()
    verifier("le quiz s'ouvre malgre tout",
             sans["zone"] and sans["ouverte"] == 0 and sans["nbOuvertes"] == 1,
             str(sans))
    verifier("sans compte a rebours, faute d'horloge", not sans["chrono"], str(sans))
    verifier("et sans invitation a ecouter, la question reste",
             not sans["attente"], str(sans))
    verifier("la sortie reste accessible", sans["suivant"], str(sans))
    page.close()

    nav.close()

srv.shutdown()
print("\n" + "=" * 62)
print("ECHECS : %d %s" % (len(echecs), echecs if echecs else ""))
sys.exit(1 if echecs else 0)
