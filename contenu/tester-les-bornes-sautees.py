# ============================================================
# TESTER LES BORNES SAUTEES — Le Sanctuaire des Brumes
#
# Rejoue les deux groupes du 20/10 :
#   - l'un saute l'enclos (Sophie, puis la passante, puis le quiz), revient
#     a l'enclos, et se faisait renvoyer vers des bornes deja faites ;
#   - l'autre saute l'appel du commissaire et bute sur le bureau de Greg.
# Verifie que :
#   1. une borne refusee n'est plus enregistree (le verrou ne fuit plus) ;
#   2. « Ou aller ensuite » indique la prochaine borne PAS ENCORE FAITE ;
#   3. l'ecran de blocage parle avec des noms lisibles, montre le chemin, et
#      laisse continuer sans une borne introuvable, en prevenant l'equipe.
#
# Base simulee, aucun vrai code. Reprend le decor de tester-le-jeu.py.
# Lancer : python3 contenu/tester-les-bornes-sautees.py
# ============================================================
import sys, os, json
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(R, "contenu", "tester-le-jeu.py")).read()
__file__ = os.path.join(R, "contenu", "tester-le-jeu.py")
exec(src[:src.index("with sync_playwright() as pw:")])
from playwright.sync_api import sync_playwright
U = lambda c: "http://127.0.0.1:%d/%s" % (PORT, PARC["pages"][c])
NOMS = PARC["noms"]
res = []
def note(nom, ok, detail=""):
    res.append((nom, ok, detail))
    print(("  OK    " if ok else "  ECHEC ") + nom + ("" if ok else "  -> " + str(detail)[:300]))


def stub(sens, faites, reseau_en_panne=False):
    """Une base qui se souvient : les passages survivent au rechargement."""
    depart = json.dumps([NOMS[c] for c in faites], ensure_ascii=False)
    return """
    const SENS = %s;
    if (sessionStorage.getItem("__base") === null)
      sessionStorage.setItem("__base", JSON.stringify(%s));
    const base = () => JSON.parse(sessionStorage.getItem("__base"));
    const journal = (cle, x) => { const l = JSON.parse(sessionStorage.getItem(cle) || "[]");
      l.push(x); sessionStorage.setItem(cle, JSON.stringify(l)); };
    window.__mails = [];
    const vraiFetch = window.fetch;
    window.fetch = async (url, o) => {
      if (String(url).indexOf("formspree") !== -1) { journal("__mails", JSON.parse(o.body));
        return new Response("{}", { status: 200 }); }
      return vraiFetch(url, o); };
    window.supabase = { createClient: () => ({
      rpc: async (nom, args) => {
        if (nom === "enregistrer_passage") {
          if (%s) return { data: null, error: { message: "Failed to fetch" } };
          journal("__passages", args.p_borne);
          const b = base(); if (b.indexOf(args.p_borne) === -1) b.push(args.p_borne);
          sessionStorage.setItem("__base", JSON.stringify(b));
          return { data: { ok: true }, error: null }; }
        if (nom === "reprendre_partie") return { data: { ok: true, code_id: "c1", code: "K7NPX4RT",
          direction: SENS, expires_at: "2099-01-01T00:00:00Z" }, error: null };
        return { data: { ok: true }, error: null }; },
      from: (t) => ({
        select: () => ({ eq: () => (t === "scans"
          ? Promise.resolve({ data: base().map(l => ({ qr_points: { label: l } })), error: null })
          : ({ maybeSingle: async () => ({ data: { id: "pt-1" } }) })) }),
        insert: async (row) => { journal(t === "signalements" ? "__signalements" : "__autres", row);
          return {}; } }) }) };
    localStorage.setItem("sdb_session", JSON.stringify({
      codeId: "c1", code: "K7NPX4RT", direction: SENS,
      expiresAt: "2099-01-01T00:00:00Z", participantName: "Test", nbJoueurs: 4 }));
    """ % (json.dumps(sens), depart, "true" if reseau_en_panne else "false")


with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])

    def ouvrir(sens, faites, borne, panne=False):
        pg = nouvelle_page(nav)
        pg.__erreurs = []
        pg.on("pageerror", lambda e: pg.__erreurs.append(str(e)))
        pg.add_init_script(stub(sens, faites, panne))
        pg.goto(U(borne)); pg.wait_for_timeout(600)
        return pg
    lire = lambda pg, cle: pg.evaluate("JSON.parse(sessionStorage.getItem(%s) || '[]')" % json.dumps(cle))
    def sortie(pg):
        """Montre l'ecran « Ou aller ensuite » et rend son texte."""
        pg.evaluate("""() => { const e = [...document.querySelectorAll('.ecran')];
            const s = e.find(x => x.hasAttribute('data-sortie'));
            e.forEach(x => x.hidden = (x !== s)); }""")
        return pg.inner_text(".ecran:not([hidden])")
    A = ["E01", "E02", "E03"]

    print("\n1. Le groupe saute l'enclos : la passante le refuse, sans rien enregistrer")
    pg = ouvrir("horaire", A, "E05")
    txt = pg.inner_text("[data-blocage]") if pg.query_selector("[data-blocage]") else ""
    note("ecran de blocage affiche", "pas encore" in txt.lower(), txt)
    note("nom lisible de la borne manquante", "l'enclos des loups" in txt and "L'ENCLOS" not in txt, txt)
    note("le chemin vers l'enclos est donne", "haut de l'enclos des loups" in txt, txt)
    note("la photo de l'enclos est proposee", pg.query_selector("[data-blocage] .photo-destination") is not None)
    note("la borne refusee n'est PAS enregistree", lire(pg, "__passages") == [], lire(pg, "__passages"))
    note("bouton « Nous ne trouvons pas cette borne »",
         pg.query_selector("[data-introuvable-ouvrir]") is not None)
    note("pas d'erreur JavaScript", not pg.__erreurs, pg.__erreurs)
    pg.close()

    print("\n2. Deux bornes d'avance : refus, et pas de raccourci")
    pg = ouvrir("horaire", A, "E06")
    note("bloque", pg.query_selector("[data-blocage]") is not None)
    note("aucun bouton pour sauter", pg.query_selector("[data-introuvable-ouvrir]") is None)
    note("rien d'enregistre", lire(pg, "__passages") == [], lire(pg, "__passages"))
    pg.close()

    print("\n3. Le parcours ordinaire : l'enclos mene a la passante, comme avant")
    pg = ouvrir("horaire", A, "E04")
    t = sortie(pg)
    note("passage de l'enclos enregistre", lire(pg, "__passages") == [NOMS["E04"]], lire(pg, "__passages"))
    note("texte d'origine conserve", "fond de l'impasse" in t and "Inutile" not in t, t)
    pg.close()

    print("\n4. Le groupe revient a l'enclos apres la passante et le quiz")
    pg = ouvrir("horaire", A + ["E05", "E06"], "E04")
    t = sortie(pg)
    note("l'enclos s'ouvre et s'enregistre", lire(pg, "__passages") == [NOMS["E04"]], lire(pg, "__passages"))
    note("il est dirige vers le veterinaire", "Votre prochaine borne : le vétérinaire" in t, t)
    note("on lui dit ce qu'il a deja fait", "la passante, le quiz animalier" in t and "Inutile" in t, t)
    note("l'ancien chemin (vers la passante) a disparu", "fond de l'impasse" not in t, t)
    note("le chemin vers le veterinaire est donne", "Enfoncez-vous dans la forêt" in t, t)
    plan = pg.get_attribute(".ecran:not([hidden]) .plan-chemin", "src") if pg.query_selector(".ecran:not([hidden]) .plan-chemin") else None
    note("le plan est celui du trajet vers le veterinaire",
         plan is None or plan.endswith("chemin-e06-vers-e07.webp"), plan)
    note("le scanner reste la", pg.query_selector(".ecran:not([hidden]) [data-scanner]") is not None)
    note("pas d'erreur JavaScript", not pg.__erreurs, pg.__erreurs)
    pg.close()

    print("\n5. Le groupe saute l'appel et bute sur le bureau de Greg")
    jusqu_au_sac = ["E%02d" % i for i in range(1, 12)]
    pg = ouvrir("horaire", jusqu_au_sac, "E13")
    txt = pg.inner_text("[data-blocage]")
    note("il lui manque l'appel du commissaire", "l'appel du commissaire" in txt, txt)
    pg.click("[data-introuvable-ouvrir]"); pg.wait_for_timeout(150)
    note("une confirmation avant de sauter", pg.is_visible("[data-introuvable-oui]")
         and pg.is_visible("[data-introuvable-non]"))
    pg.click("[data-introuvable-non]"); pg.wait_for_timeout(100)
    note("« Je la cherche encore » referme sans rien faire",
         pg.is_visible("[data-introuvable-ouvrir]") and lire(pg, "__passages") == [])
    pg.click("[data-introuvable-ouvrir]"); pg.click("[data-introuvable-oui]")
    pg.wait_for_timeout(1500)
    passages = lire(pg, "__passages")
    note("l'appel compte comme passe, puis le bureau s'ouvre et s'enregistre",
         passages == [NOMS["E12"], NOMS["E13"]], passages)
    note("le bureau de Greg est affiche", pg.query_selector("[data-blocage]") is None
         and len(pg.query_selector_all(".ecran")) > 1)
    sg = lire(pg, "__signalements")
    note("l'equipe a un signalement « Borne introuvable »",
         len(sg) == 1 and sg[0]["borne"] == NOMS["E12"] and "Borne introuvable" in sg[0]["message"]
         and "bureau de Greg" in sg[0]["message"], sg)
    mails = lire(pg, "__mails")
    note("et un mail qui nomme la borne", len(mails) == 1 and NOMS["E12"] in mails[0]["_subject"], mails)
    note("pas d'erreur JavaScript", not pg.__erreurs, pg.__erreurs)
    pg.close()

    print("\n6. Sauter sans reseau : on le dit, on ne recharge pas en boucle")
    pg = ouvrir("horaire", jusqu_au_sac, "E13", panne=True)
    pg.click("[data-introuvable-ouvrir]"); pg.click("[data-introuvable-oui]"); pg.wait_for_timeout(800)
    note("message d'erreur visible", pg.is_visible("[data-introuvable-erreur]"))
    note("toujours bloque, bouton de nouveau actif", pg.query_selector("[data-blocage]") is not None
         and pg.is_enabled("[data-introuvable-oui]"))
    note("aucun signalement envoye a tort", lire(pg, "__signalements") == [])
    pg.close()

    print("\n7. Sens B : Bill manque avant le sac")
    pg = ouvrir("antihoraire", ["E01", "E16"], "E11")
    txt = pg.inner_text("[data-blocage]")
    note("il lui manque Bill", "Bill" in txt and "grande volière" in txt, txt)
    note("aucun nom de travail", "version sens" not in txt and "Indice :" not in txt, txt)
    pg.close()

    print("\n8. Le botaniste manque : on guide vers le Jardin des Iris")
    pg = ouvrir("horaire", ["E%02d" % i for i in range(1, 14)], "E15")
    txt = pg.inner_text("[data-blocage]")
    note("le botaniste, au Jardin des Iris", "le botaniste" in txt and "Jardin des Iris" in txt, txt)
    pg.close()

    nav.close()

ko = [n for n, ok, _ in res if not ok]
print("\n%d controles\nECHECS : %d %s" % (len(res), len(ko), ko if ko else ""))
sys.exit(1 if ko else 0)
