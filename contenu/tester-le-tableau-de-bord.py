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

def stub(codes, signalements=None):
    return """
    window.__codes = %s;
    window.__sign = %s;
    window.__rpc = [];
    window.supabase = { createClient: () => ({
      rpc: async (nom, args) => { window.__rpc.push([nom, args]);
        const s = window.__sign.find(x => x.id === args.p_id);
        if (s) s.traite_le = new Date().toISOString();
        return { data: s ? s.traite_le : null, error: null }; },
      from: (t) => {
      const donnees = t === "codes" ? window.__codes
                    : t === "signalements_recents" ? window.__sign : [];
      const rep = { data: donnees, error: null };
      const q = {
        select: () => q, order: () => Promise.resolve(rep), eq: () => q,
        not: () => q, limit: () => Promise.resolve(rep),
        gte: () => Promise.resolve(rep),
        maybeSingle: () => Promise.resolve({ data: null }),
        then: (f) => Promise.resolve(rep).then(f),
      };
      return q; } }) };
    """ % (json.dumps(codes), json.dumps(signalements or [], ensure_ascii=False))

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
        page.fill("#pwd", "brumes2026"); page.click("#enterBtn")
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
        page.fill("#pwd", "brumes2026"); page.click("#enterBtn"); page.wait_for_timeout(400)
        a_alerte = page.eval_on_selector_all(".alerte", "e=>e.length") > 0
        titre = page.title().startswith("(")
        print("   %s" % libelle)
        v("   bandeau d'alerte %s" % ("present" if attendu["alerte"] else "absent"),
          a_alerte == attendu["alerte"])
        v("   compte dans l'onglet %s" % ("present" if attendu["titre"] else "absent"),
          titre == attendu["titre"], page.title())
        page.close()

    print("\nClore un signalement")
    page = nav.new_page()
    page.add_init_script(stub(codes(2, 3), signalements(2)))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
    page.fill("#pwd", "brumes2026"); page.click("#enterBtn"); page.wait_for_timeout(400)
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
    page.fill("#pwd", "brumes2026"); page.click("#enterBtn"); page.wait_for_timeout(400)
    print("\n5 groupes sans nombre declare")
    note = page.text_content("#creneauReserve")
    v("l'approximation est signalee", "approximatif" in note and "5 groupe" in note, note[:120])
    page.screenshot(path=os.path.join(RACINE, "dashboard-apercu.png"), full_page=True)
    page.close()

    # Aucun depart
    page = nav.new_page(); page.add_init_script(stub([]))
    page.goto("http://127.0.0.1:%d/backoffice/dashboard.html" % PORT)
    page.fill("#pwd", "brumes2026"); page.click("#enterBtn"); page.wait_for_timeout(400)
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
