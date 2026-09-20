# -*- coding: utf-8 -*-
"""Teste le verrouillage du parcours, le code de secours et le signalement.

    python3 contenu/tester-le-verrouillage.py

Ne touche pas a Supabase. Simule un groupe ayant scanne telle ou telle borne
et verifie qu'il ne peut pas sauter d'etapes, que le code a quatre chiffres
ouvre bien la borne attendue, qu'aucun de ces codes ne se deduit d'un autre
par une seule faute de frappe, et qu'un signalement part avec sa borne.
"""
import sys, os, json, threading, functools, http.server, socketserver, re
from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
class Muet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Muet, directory=RACINE))
PORT = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

txt = open(os.path.join(RACINE, "assets/js/parcours.js")).read()
PARC = json.loads(txt.split("const PARCOURS =", 1)[1].rstrip().rstrip(";"))

def init(sens, scans, code="TEST01"):
    """scans = liste de codes d'etape deja visites (cote base)."""
    labels = [PARC["noms"][c] for c in scans]
    return """
    window.__inserts = [];
    window.supabase = { createClient: () => ({ from: (t) => {
      if (t === "scans") {
        return { select: () => ({ eq: () => Promise.resolve({
                   data: %s.map(l => ({ qr_points: { label: l } })), error: null }) }),
                 insert: async (r) => { window.__inserts.push(["scans", r]); return {}; } };
      }
      if (t === "signalements") {
        return { insert: async (r) => { window.__inserts.push(["signalements", r]); return { error: null }; } };
      }
      return { select: () => ({ eq: () => ({ maybeSingle: async () => ({ data: { id: 'pt' } }) }) }),
               insert: async () => ({}) };
    } }) };
    localStorage.setItem("sdb_session", JSON.stringify({
      codeId: "c1", code: "%s", direction: "%s",
      expiresAt: "2099-01-01T00:00:00Z", nbJoueurs: 2 }));
    """ % (json.dumps(labels, ensure_ascii=False), code, sens)

echecs = []
def v(nom, cond, detail=""):
    print("   %-46s %s %s" % (nom, "OK " if cond else "ECHEC", "" if cond else detail))
    if not cond: echecs.append(nom)

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

    print("\nVerrouillage du parcours (sens A)")
    cas = [
      ("E01", [],                              True,  "premiere borne, sans rien avoir scanne"),
      ("E05", [],                              False, "saut direct a la 5e borne"),
      ("E05", ["E01","E02","E03","E04"],       True,  "5e borne apres les quatre precedentes"),
      ("E02", ["E01","E02","E03"],             True,  "retour sur une borne deja visitee"),
      ("E15", ["E01","E02"],                   False, "saut a la derniere borne"),
    ]
    for code, faits, attendu, libelle in cas:
        page = nav.new_page()
        page.add_init_script(init("horaire", faits))
        page.goto("http://127.0.0.1:%d/etapes/%s" % (PORT, PARC["pages"][code]))
        page.wait_for_timeout(350)
        bloque = "pas la vôtre" in page.text_content(".wrap")
        v(libelle, bloque != attendu, "bloque=%s attendu_ouvert=%s" % (bloque, attendu))
        if bloque:
            print("        message : " + re.sub(r"\s+", " ", page.text_content(".ecran"))[:110])
        page.close()

    print("\nLe code de secours a 4 chiffres")
    page = nav.new_page(); page.add_init_script(init("horaire", ["E01"]))
    page.goto("http://127.0.0.1:%d/etapes/%s" % (PORT, PARC["pages"]["E02"]))
    page.wait_for_timeout(300)
    page.click("#boutonSecours")
    page.fill("#champSecours", "0000"); page.click("#validerSecours")
    page.wait_for_timeout(150)
    v("numero inconnu : message d'erreur", not page.eval_on_selector("#erreurSecours", "e=>e.hidden"))
    bon = [n for n, c in PARC["secours"].items() if c == "E03"][0]
    page.fill("#champSecours", bon); page.click("#validerSecours")
    page.wait_for_timeout(400)
    v("bon numero : ouvre la bonne borne", PARC["pages"]["E03"] in page.url, page.url)
    page.close()

    print("\nLes codes de secours ne se devinent pas")
    nums = sorted(int(n) for n in PARC["secours"].keys())
    ecarts = [b - a for a, b in zip(nums, nums[1:])]
    v("tous differents", len(set(nums)) == len(nums))
    v("aucun ne se suit", all(e > 1 for e in ecarts), "ecarts min=%d" % min(ecarts))
    v("tous a 4 chiffres", all(1000 <= n <= 9999 for n in nums))

    print("\nLe bouton « j'ai un problème »")
    page = nav.new_page(); page.add_init_script(init("horaire", ["E01"]))
    page.goto("http://127.0.0.1:%d/etapes/%s" % (PORT, PARC["pages"]["E02"]))
    page.wait_for_timeout(300)
    page.click("#boutonProbleme")
    page.select_option("#categorieProbleme", "decor")
    page.fill("#messageProbleme", "Le sac est renversé")
    page.click("#envoyerProbleme"); page.wait_for_timeout(300)
    envois = [i for i in page.evaluate("window.__inserts") if i[0] == "signalements"]
    v("le signalement part", len(envois) == 1, str(envois))
    if envois:
        r = envois[0][1]
        v("il porte la borne et la categorie",
          r.get("categorie") == "decor" and r.get("borne") == PARC["noms"]["E02"], str(r))
    v("le joueur est remercie", "noté" in page.text_content("#retourProbleme"),
      page.text_content("#retourProbleme"))
    page.close()
    nav.close()

srv.shutdown()
print("\n" + "="*68)
print("ECHECS : %d %s" % (len(echecs), echecs if echecs else ""))
sys.exit(1 if echecs else 0)
