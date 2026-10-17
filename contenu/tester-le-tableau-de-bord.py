# -*- coding: utf-8 -*-
"""Teste le compteur de creneau du tableau de bord, sans toucher a Supabase.

    python3 contenu/tester-le-tableau-de-bord.py

Injecte de faux departs et verifie ce que l'accueil lira : le nombre de
personnes, le nombre de groupes, la taille moyenne, l'etat annonce par un
mot et pas seulement par une couleur, et le fait qu'un groupe sans nombre
declare soit signale au lieu d'etre compte en silence.
"""
import sys, os, json, threading, functools, http.server, socketserver
from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

class Muet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Muet, directory=RACINE))
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

def stub(codes, signalements=None, live=None, parties=None, connecte=False):
    return """
    window.__codes = %s;
    window.__sign = %s;
    window.__live = %s;
    window.__parties = %s;
    window.__lectures = [];
    // Supabase Auth : un seul compte, mot de passe « bon ».
    window.__session = %s;
    const auth = {
      getSession: async () => ({ data: { session: window.__session }, error: null }),
      signInWithPassword: async ({ email, password }) => {
        if (password !== "bon") return { data: { session: null },
          error: { message: "Invalid login credentials" } };
        window.__session = { user: { email } };
        return { data: { session: window.__session }, error: null }; },
      signOut: async () => { window.__session = null; return { error: null }; },
    };
    window.__rpc = [];
    window.supabase = { createClient: () => ({
      auth,
      rpc: async (nom, args) => { window.__rpc.push([nom, args]);
        const s = window.__sign.find(x => x.id === args.p_id);
        if (s) s.traite_le = new Date().toISOString();
        return { data: s ? s.traite_le : null, error: null }; },
      from: (t) => { window.__lectures.push(t);
      // "departs_recents" a remplace la lecture directe de "codes" au
      // correctif 6 : la table est fermee, le backoffice lit une vue.
      const donnees = t === "departs_recents" ? window.__codes
                    : t === "signalements_recents" ? window.__sign
                    : t === "live_dashboard" ? window.__live
                    : t === "historique_parties" ? window.__parties : [];
      const rep = { data: donnees, error: null };
      const q = {
        select: () => q, order: () => q, eq: () => q,
        not: () => q, limit: () => Promise.resolve(rep),
        gte: () => Promise.resolve(rep),
        maybeSingle: () => Promise.resolve({ data: null }),
        then: (f) => Promise.resolve(rep).then(f),
      };
      return q; } }) };
    """ % (json.dumps(codes), json.dumps(signalements or [], ensure_ascii=False),
           json.dumps(live or [], ensure_ascii=False), json.dumps(parties or [], ensure_ascii=False),
           '{ user: { email: "eva@exemple.fr" } }' if connecte else "null")

def entrer(page):
    """Se connecter avec le compte de l'equipe."""
    page.fill("#gateEmail", "eva@exemple.fr"); page.fill("#gateMdp", "bon")
    page.click("#enterBtn"); page.wait_for_timeout(400)

def codes(nb_groupes, par_groupe, minutes=5, declare=True):
    from datetime import datetime, timedelta, timezone
    t = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
    return [{"activated_at": t,
             "participants_reels": par_groupe if declare else None,
             "max_participants": par_groupe,
             "direction": "horaire" if i % 2 == 0 else "antihoraire"}
            for i in range(nb_groupes)]

def signalements(ouverts=0, clos=0):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    out = []
    for i in range(ouverts):
        out.append({"id": "o%d" % i, "signale_le": (now - timedelta(minutes=5 + i)).isoformat(),
                    "categorie": ["qr", "decor", "bug"][i % 3],
                    "borne": ["QUIZ ANIMALIER", "Bureau de Greg", "LA PASSANTE"][i % 3],
                    "message": "Constat numero %d" % i, "traite_le": None, "code": "TEST0%d" % (i % 3 + 1)})
    for i in range(clos):
        out.append({"id": "c%d" % i, "signale_le": (now - timedelta(hours=2)).isoformat(),
                    "categorie": "autre", "borne": "Bill", "message": "Regle",
                    "traite_le": (now - timedelta(hours=1)).isoformat(), "code": "TEST01"})
    return out

echecs = []
def v(nom, cond, detail=""):
    print("   %-44s %s %s" % (nom, "OK " if cond else "ECHEC", "" if cond else detail))
    if not cond: echecs.append(nom)

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

    for libelle, jeu, attendu in [
        ("12 groupes de 6 = 72 personnes", codes(12, 6), {"pers":"72","grp":"12","taille":"6.0","etat":"Plafond atteint"}),
        ("36 groupes de 2 = 72 personnes", codes(36, 2), {"pers":"72","grp":"36","taille":"2.0","etat":"Plafond atteint"}),
        ("10 groupes de 4 = 40 personnes", codes(10, 4), {"pers":"40","grp":"10","taille":"4.0","etat":"Sous le plafond"}),
        ("20 groupes de 5 = 100 personnes", codes(20, 5), {"pers":"100","grp":"20","taille":"5.0","etat":"Plafond dépassé"}),
    ]:
        page = nav.new_page()
        page.add_init_script(stub(jeu))
        page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
        entrer(page)
        page.wait_for_timeout(400)
        print("\n%s" % libelle)
        v("personnes", page.text_content("#creneauPersonnes").strip() == attendu["pers"],
          page.text_content("#creneauPersonnes"))
        v("groupes", page.text_content("#creneauGroupes").strip() == attendu["grp"],
          page.text_content("#creneauGroupes"))
        v("taille moyenne", page.text_content("#creneauTaille").strip() == attendu["taille"],
          page.text_content("#creneauTaille"))
        v("etat annonce par un mot", attendu["etat"] in page.text_content("#creneauEtat"),
          page.text_content("#creneauEtat"))
        note = page.text_content("#creneauReserve")
        print("      note : " + note[:150])
        page.close()

    print("\nSignalements du terrain")
    for libelle, jeu, attendu in [
        ("aucun signalement", [], {"alerte": False, "titre": False}),
        ("trois problemes ouverts", signalements(3), {"alerte": True, "titre": True}),
        ("tout est regle", signalements(0, 2), {"alerte": False, "titre": False}),
    ]:
        page = nav.new_page()
        page.add_init_script(stub(codes(2, 3), jeu))
        page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
        entrer(page)
        a_alerte = page.eval_on_selector_all(".alerte", "e=>e.length") > 0
        titre = page.title().startswith("(")
        print("   %s" % libelle)
        v("   bandeau d'alerte %s" % ("present" if attendu["alerte"] else "absent"),
          a_alerte == attendu["alerte"])
        v("   compte dans l'onglet %s" % ("present" if attendu["titre"] else "absent"),
          titre == attendu["titre"], page.title())
        page.close()

    # Les diagnostics automatiques des bornes ne sont pas des problemes de
    # joueurs : ni alerte, ni compte dans l'onglet, mais une liste repliee.
    from datetime import datetime, timezone
    autos = [{"id": "a%d" % i, "signale_le": datetime.now(timezone.utc).isoformat(),
              "categorie": "bug", "borne": "VÉTÉRINAIRE", "traite_le": None, "code": None,
              "message": "Diagnostic automatique : partie introuvable a l'ouverture de la borne."}
             for i in range(30)]
    piege = dict(signalements(1)[0], message='<img src=x onerror="window.__xss=1">')
    for libelle, jeu, alerte, compte in [
        ("30 diagnostics automatiques seuls", autos, False, ""),
        ("30 diagnostics et 1 vrai probleme", autos + [piege], True, "(1)"),
    ]:
        page = nav.new_page()
        page.add_init_script(stub(codes(2, 3), jeu))
        page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
        entrer(page)
        print("   %s" % libelle)
        v("   alerte %s" % ("pour le vrai probleme seulement" if alerte else "absente"),
          (page.eval_on_selector_all(".alerte", "e=>e.length") > 0) == alerte
          and (not alerte or page.text_content(".alerte .compte").strip() == "1"))
        v("   onglet " + (compte or "sans compte"),
          page.title().startswith(compte) if compte else not page.title().startswith("("), page.title())
        v("   diagnostics ranges a part, replies",
          page.eval_on_selector_all("details.diagnostics:not([open]) [data-traiter]", "e=>e.length") == 30)
        v("   un message n'est jamais lu comme du HTML", not page.evaluate("window.__xss"))
        if not alerte:
            page.click("details.diagnostics summary"); page.click("#toutTraiter"); page.wait_for_timeout(600)
            appels = page.evaluate("window.__rpc")
            v("   « Tout marquer traite » passe par le guichet, 30 fois",
              len(appels) == 30 and all(x[0] == "marquer_signalement_traite" for x in appels), str(len(appels)))
        page.close()

    # Les codes derriere chaque chiffre : 4 caracteres, jamais le code entier.
    print("\nLes codes a cote des chiffres")
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    departs = [dict(c, code="AB%02d" % i) for i, c in enumerate(codes(3, 4))]
    departs[2]["participants_reels"] = None
    live = [{"code": "AB00", "max_participants": 4, "direction": "horaire",
             "last_point": "Bill", "last_scan_at": (now - timedelta(minutes=3)).isoformat()},
            {"code": "AB01", "max_participants": 4, "direction": "antihoraire",
             "last_point": "La passante", "last_scan_at": (now - timedelta(minutes=35)).isoformat()}]
    page = nav.new_page()
    page.add_init_script(stub(departs, [], live))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
    entrer(page)
    t = lambda sel: page.text_content(sel)
    v("personnes parties : codes et nombre de chacun",
      "···AB00 (4)" in t("#creneauCodesPersonnes") and "···AB02 (4 prévues)" in t("#creneauCodesPersonnes"),
      t("#creneauCodesPersonnes"))
    v("groupes partis : les trois codes", all("···AB0%d" % i in t("#creneauCodesGroupes") for i in range(3)),
      t("#creneauCodesGroupes"))
    v("sens : codes horaires et antihoraires a part",
      t("#creneauCodesSens").startswith("H : ") and "A : ···AB01" in t("#creneauCodesSens")
      and "···AB01" not in t("#creneauCodesSens").split("A :")[0]
      and all(x in t("#creneauCodesSens").split("A :")[0] for x in ("···AB00", "···AB02")),
      t("#creneauCodesSens"))
    cartes = page.eval_on_selector_all("#statRow .stat-card .codes", "e=>e.map(x=>x.textContent)")
    v("groupes en jeu : leurs codes", "···AB00" in cartes[0] and "···AB01" in cartes[0], str(cartes))
    v("sans scan depuis 20 min : le code et sa derniere borne",
      cartes[1].strip() == "···AB01 (La passante)", str(cartes))
    page.close()
    # Avant le correctif 11, la vue n'a pas de code : on compte quand meme.
    page = nav.new_page()
    page.add_init_script(stub(codes(2, 3), []))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
    entrer(page)
    v("sans le correctif 11 : le compte reste juste, codes en « ···? »",
      t("#creneauGroupes").strip() == "2" and "···?" in t("#creneauCodesGroupes"), t("#creneauCodesGroupes"))
    page.close()

    # ------------------------------------------------------------
    # LA PORTE : plus de mot de passe ecrit dans la page, un compte Supabase.
    # ------------------------------------------------------------
    print("\nLa connexion de l'equipe")
    for fichier, bloc in [("dashboard.html", "#dashboard"), ("statistiques.html", "#statsPage")]:
        source = open(os.path.join(RACINE, "backoffice", fichier)).read()
        v(fichier + " : plus aucun mot de passe dans la page", "brumes2026" not in source)
        page = nav.new_page()
        page.add_init_script(stub(codes(2, 3), []))
        page.goto("http://127.0.0.1:%d/backoffice/%s" % (PORT, fichier)); page.wait_for_timeout(300)
        v(fichier + " : fermee, et rien n'est lu avant connexion",
          not page.is_visible(bloc) and page.evaluate("window.__lectures.length") == 0,
          str(page.evaluate("window.__lectures")))
        page.fill("#gateEmail", "eva@exemple.fr"); page.fill("#gateMdp", "faux")
        page.click("#enterBtn"); page.wait_for_timeout(300)
        v(fichier + " : mauvais mot de passe refuse",
          not page.is_visible(bloc) and "incorrect" in page.text_content("#gateError"),
          page.text_content("#gateError"))
        page.fill("#gateMdp", "bon"); page.press("#gateMdp", "Enter"); page.wait_for_timeout(400)
        v(fichier + " : bon mot de passe, la page s'ouvre", page.is_visible(bloc))
        v(fichier + " : le compte connecte est affiche",
          "eva@exemple.fr" in page.text_content("#quiEstConnecte"))
        page.click("#seDeconnecter"); page.wait_for_timeout(400)
        v(fichier + " : « Se deconnecter » referme la page", not page.is_visible(bloc))
        page.close()
    page = nav.new_page()
    page.add_init_script(stub(codes(2, 3), [], connecte=True))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT); page.wait_for_timeout(400)
    v("deja connecte sur cet appareil : on entre directement", page.is_visible("#dashboard"))
    page.close()

    # ------------------------------------------------------------
    # TOUTES LES PARTIES
    # ------------------------------------------------------------
    print("\nToutes les parties")
    hier = (now - timedelta(days=1))
    parties = [
      {"activated_at": (now - timedelta(minutes=50)).isoformat(), "code": "K7NPX4RT",
       "nom_groupe": '<img src=x onerror="window.__xss=1">Les Limiers', "participants_reels": 4,
       "max_participants": 4, "direction": "horaire", "expires_at": (now + timedelta(hours=2)).isoformat(),
       "nb_bornes": 6, "nb_scans": 7, "dernier_scan": (now - timedelta(minutes=5)).isoformat(),
       "derniere_borne": "Bill", "a_atteint_la_serre": False, "parcours": "Le commissaire Jean 09:10 → Bill 09:55",
       "conclusion": None, "denouement": None, "nb_signalements": 1},
      {"activated_at": hier.isoformat(), "code": "QX2MAB12", "nom_groupe": "Les Hiboux",
       "participants_reels": None, "max_participants": 3, "direction": "antihoraire",
       "expires_at": (hier + timedelta(hours=3)).isoformat(), "nb_bornes": 15, "nb_scans": 15,
       "dernier_scan": (hier + timedelta(minutes=112)).isoformat(), "derniere_borne": "La serre",
       "a_atteint_la_serre": True, "parcours": "…", "conclusion": "Elle s'est endormie.",
       "denouement": "Bon", "nb_signalements": 0},
      {"activated_at": hier.isoformat(), "code": "TEST0001", "nom_groupe": "Equipe", "participants_reels": 2,
       "max_participants": 2, "direction": "horaire", "expires_at": hier.isoformat(), "nb_bornes": 1,
       "nb_scans": 1, "dernier_scan": hier.isoformat(), "derniere_borne": "Le commissaire Jean",
       "a_atteint_la_serre": False, "parcours": "", "conclusion": None, "denouement": None, "nb_signalements": 0},
    ]
    live_complet = [dict(live[0], code_complet="K7NPX4RT", nom_groupe="Les Limiers", participants_reels=4)]
    page = nav.new_page(accept_downloads=True)
    page.add_init_script(stub([dict(c, code="X4RT", code_complet="K7NPX4RT") for c in codes(1, 4)],
                              [], live_complet, parties))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
    entrer(page); page.wait_for_timeout(300)
    lignes = page.eval_on_selector_all("#partiesBody tr", "e=>e.map(x=>x.innerText)")
    v("une ligne par partie, codes de test masques", len(lignes) == 2, str(lignes))
    v("la plus recente en haut, code entier et nom du groupe",
      "K7NPX4RT" in lignes[0] and "Les Limiers" in lignes[0], lignes[0])
    v("un nom d'equipe n'est jamais lu comme du HTML", not page.evaluate("window.__xss"))
    v("partie finie : duree et denouement",
      "1 h 52" in lignes[1] and "Trouvé : Elle s'est endormie." in lignes[1], lignes[1])
    v("partie en cours dite en cours", "En cours" in lignes[0], lignes[0])
    v("joueurs non declares : la capacite prevue", "3 prévus" in lignes[1], lignes[1])
    v("le resume compte parties et trouvailles",
      "2 partie(s)" in page.text_content("#histoResume") and "dont 1 a trouvé" in page.text_content("#histoResume"),
      page.text_content("#histoResume"))
    page.uncheck("#histoSansTest"); page.wait_for_timeout(100)
    v("decocher : les codes de test reviennent",
      page.eval_on_selector_all("#partiesBody tr", "e=>e.length") == 3)
    page.check("#histoSansTest")
    jours = page.eval_on_selector_all("#histoJour option", "e=>e.map(x=>x.value)")
    page.select_option("#histoJour", jours[-1]); page.wait_for_timeout(100)
    v("filtre par jour", page.eval_on_selector_all("#partiesBody tr", "e=>e.length") == 1, str(jours))
    page.select_option("#histoJour", "")
    with page.expect_download() as dl:
        page.click("#histoExporter")
    contenu = open(dl.value.path(), encoding="utf-8-sig").read()
    v("l'export CSV contient chaque partie et son parcours",
      contenu.count("\n") == 2 and "K7NPX4RT" in contenu and "Le commissaire Jean 09:10" in contenu
      and contenu.startswith("Départ;Code;Groupe"), contenu[:200])
    v("groupes actifs : code entier et nom",
      "K7NPX4RT" in page.text_content("#liveBody") and "Les Limiers" in page.text_content("#liveBody"),
      page.text_content("#liveBody"))
    v("creneau : code entier", "K7NPX4RT" in page.text_content("#creneauCodesGroupes"),
      page.text_content("#creneauCodesGroupes"))
    page.close()
    # Avant le correctif 12, la vue n'existe pas : on le dit, sans casser le reste.
    page = nav.new_page()
    page.add_init_script(stub(codes(2, 3), []).replace(
        ': t === "historique_parties" ? window.__parties : [];',
        ': [];').replace('const rep = { data: donnees, error: null };',
        'const rep = t === "historique_parties" ? { data: null, error: { message: "relation absente" } } : { data: donnees, error: null };'))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
    entrer(page); page.wait_for_timeout(300)
    v("sans le correctif 12 : message clair, le reste s'affiche",
      "correctif 12" in page.text_content("#partiesBody") and page.text_content("#creneauGroupes").strip() == "2",
      page.text_content("#partiesBody"))
    page.close()

    print("\nClore un signalement")
    page = nav.new_page()
    page.add_init_script(stub(codes(2, 3), signalements(2)))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
    entrer(page)
    v("deux boutons Traite", page.eval_on_selector_all("[data-traiter]", "e=>e.length") == 2)
    page.query_selector("[data-traiter]").click(); page.wait_for_timeout(400)
    appels = page.evaluate("window.__rpc")
    v("passe par le guichet, pas par la table",
      len(appels) == 1 and appels[0][0] == "marquer_signalement_traite", str(appels))
    v("il n'en reste qu'un ouvert",
      page.eval_on_selector_all("[data-traiter]", "e=>e.length") == 1)
    page.close()

    # Groupes sans declaration : le total ne doit pas mentir en silence
    page = nav.new_page()
    page.add_init_script(stub(codes(5, 4, declare=False)))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
    entrer(page)
    print("\n5 groupes sans nombre declare")
    note = page.text_content("#creneauReserve")
    v("l'approximation est signalee", "approximatif" in note and "5 groupe" in note, note[:120])
    page.screenshot(path=os.path.join(RACINE, "dashboard-apercu.png"), full_page=True)
    page.close()

    # Aucun depart
    page = nav.new_page(); page.add_init_script(stub([]))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
    entrer(page)
    print("\nAucun depart")
    v("pas de division par zero", page.text_content("#creneauTaille").strip() == "—",
      page.text_content("#creneauTaille"))
    v("message clair", "Aucun départ" in page.text_content("#creneauReserve"))
    page.close()
    nav.close()

srv.shutdown()
print("\n" + "="*64)
print("ECHECS : %d %s" % (len(echecs), echecs if echecs else ""))
sys.exit(1 if echecs else 0)
