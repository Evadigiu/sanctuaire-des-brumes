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
      rpc: async (nom, args) => {
        if (nom === "enregistrer_passage") { window.__scans.push(args);
          return { data: { ok: true }, error: null }; }
        if (nom === "activer_code") return { data: { ok: true, code_id: "c1",
          code: (args.p_code || "").toUpperCase(), direction: "horaire",
          expires_at: "2099-01-01T00:00:00Z" }, error: null };
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
        (PARC["pages"]["E02"], "horaire",     (2, 15), "sens A"),
        (PARC["pages"]["E02"], "antihoraire", (8, 15), "sens B"),
        (PARC["pages"]["E09"], "antihoraire", None,    "borne de l'autre sens"),
    ]:
        page = nav.new_page()
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
        page = nav.new_page(); page.add_init_script(init("horaire"))
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
        page = nav.new_page(); page.add_init_script(init("horaire"))
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
    page = nav.new_page(); page.add_init_script(init("horaire"))
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
    page = nav.new_page(); page.add_init_script(init("horaire"))

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

    # Sur la borne de depart il n'y a rien avant : le bouton disparait plutot
    # que de rester la sans rien faire.
    page = nav.new_page(); page.add_init_script(init("horaire"))
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
    page = nav.new_page(); page.add_init_script(init("horaire"))
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
    page = nav.new_page(); page.add_init_script(init("horaire"))
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
    page = nav.new_page(); page.add_init_script(init("horaire"))
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
        page = nav.new_page(); page.add_init_script(init("horaire"))
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
    page = nav.new_page(); page.add_init_script(init("horaire"))
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

    nav.close()

srv.shutdown()
print("\n" + "=" * 62)
print("ECHECS : %d %s" % (len(echecs), echecs if echecs else ""))
sys.exit(1 if echecs else 0)
