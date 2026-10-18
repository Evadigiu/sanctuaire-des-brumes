# ============================================================
# TESTER LES FAUSSES MANIPULATIONS — Le Sanctuaire des Brumes
#
# Ce qu'un vrai groupe fait de travers : code mal tape, double clic,
# rechargement en pleine borne, bouton « precedent » du telephone, reponses
# avec des espaces, touche Entree au lieu du bouton, numero fantaisiste...
# Sur une copie locale du site, avec une base simulee : aucun vrai code.
#
# Reprend le decor de tester-le-jeu.py (serveur local, base simulee).
# Lancer : python3 contenu/tester-les-fausses-manips.py
# ============================================================
import sys, os, json, re
R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(R, "contenu", "tester-le-jeu.py")).read()
__file__ = os.path.join(R, "contenu", "tester-le-jeu.py")
exec(src[:src.index("with sync_playwright() as pw:")])
from playwright.sync_api import sync_playwright
U = lambda c, q="": "http://127.0.0.1:%d/%s%s" % (PORT, PARC["pages"][c], q)
res = []
def note(nom, ok, detail=""):
    res.append((nom, ok, detail)); print(("  OK    " if ok else "  ECHEC ") + nom + ("" if ok else "  -> " + str(detail)[:300]))

with sync_playwright() as pw:
    nav = pw.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
    def page_jeu(sens="horaire", sans_session=False, extra=""):
        pg = nouvelle_page(nav)
        erreurs = []
        pg.on("pageerror", lambda e: erreurs.append(str(e)))
        i = init(sens).replace('if (nom === "activer_code") return',
            'if (nom === "activer_code" && (args.p_code || "").replace(/\\s/g, "").toUpperCase() !== "K7NPX4RT") '
            'return { data: { ok: false, message: "Ce code n\'existe pas." }, error: null }; '
            'if (nom === "activer_code") return', 1)
        if sans_session: i = i.split('localStorage.setItem("sdb_session"')[0]
        pg.add_init_script(i + extra)
        pg.__erreurs = erreurs
        return pg
    vis = lambda pg: [e for e in pg.query_selector_all(".ecran") if e.is_visible()]

    print("\n1. Le depart au commissaire : saisies fautives")
    cas = [("", "4", True, "code vide"), ("ZZZZZZZZ", "4", True, "code inexistant"),
           ("k7npx4rt", "0", True, "0 joueur"), ("k7npx4rt", "9", True, "9 joueurs"),
           ("k7npx4rt", "", True, "nombre vide")]
    for code, nb, regles, nom in cas:
        pg = page_jeu(sans_session=True); pg.goto(U("E01")); pg.wait_for_timeout(400)
        pg.click("#versSaisieDepart")
        pg.fill("#participantName", "Testeurs"); pg.fill("#nbJoueurs", nb); pg.fill("#codeInput", code)
        if regles and not pg.is_checked("#acceptRules"): pg.check("#acceptRules")
        bloque = pg.is_disabled("#startBtn")
        if not bloque:
            pg.click("#startBtn"); pg.wait_for_timeout(400)
        reste = "/8055/" in pg.url or pg.url.endswith(PARC["pages"]["E01"])
        demarre = pg.evaluate("localStorage.getItem('sdb_session') !== null")
        note("depart, %s : refuse sans demarrer" % nom, not demarre, pg.url)
        pg.close()
    pg = page_jeu(sans_session=True); pg.goto(U("E01")); pg.wait_for_timeout(400)
    pg.click("#versSaisieDepart"); pg.fill("#participantName", "Testeurs")
    pg.uncheck("#acceptRules"); pg.fill("#codeInput", "K7NPX4RT"); pg.fill("#nbJoueurs", "4")
    note("depart sans cocher les regles : bouton grise", pg.is_disabled("#startBtn"))
    pg.check("#acceptRules"); pg.fill("#participantName", "")
    note("depart sans nom d'equipe : bouton grise", pg.is_disabled("#startBtn"))
    pg.fill("#participantName", "Les Testeurs"); pg.fill("#codeInput", "  k7np x4rt ")
    try:
        with pg.expect_navigation(timeout=4000):
            pg.click("#startBtn"); pg.click("#startBtn", timeout=500, force=True)
    except Exception as e: pass
    pg.wait_for_timeout(600)
    act = [a for a in pg.evaluate("JSON.parse(sessionStorage.getItem('__rpcs')||'[]')") if a[0] == "activer_code"]
    note("code en minuscules avec espaces, double clic : une seule activation, partie ouverte",
         len(act) == 1 and pg.evaluate("localStorage.getItem('sdb_session') !== null"), str(act))
    note("pas d'erreur JavaScript au depart", not pg.__erreurs, pg.__erreurs)
    pg.close()

    print("\n2. Rechargements et bouton precedent du navigateur")
    pg = page_jeu(); pg.goto(U("E05")); pg.wait_for_timeout(400)
    pg.locator(".ecran:visible [data-suivant]").first.click(); pg.wait_for_timeout(200)
    avant = pg.evaluate("[...document.querySelectorAll('.ecran')].findIndex(e=>!e.hidden)")
    pg.reload(); pg.wait_for_timeout(500)
    apres = pg.evaluate("[...document.querySelectorAll('.ecran')].findIndex(e=>!e.hidden)")
    note("recharger en pleine borne : on retrouve le meme ecran", avant == apres and avant > 0, (avant, apres))
    pg.goto(U("E06")); pg.wait_for_timeout(400); pg.go_back(); pg.wait_for_timeout(500)
    note("bouton precedent du navigateur : la borne d'avant s'affiche, une seule carte",
         pg.url.endswith(PARC["pages"]["E05"]) and len(vis(pg)) == 1, (pg.url, len(vis(pg))))
    note("aucune erreur JavaScript", not pg.__erreurs, pg.__erreurs)
    pg.close()

    print("\n3. Question bonus : clics multiples")
    bonus = [c for c in PARC["pages"] if 'data-popquiz' in open(os.path.join(R, PARC["pages"][c], "index.html")).read()]
    pg = page_jeu(); pg.goto(U(bonus[0])); pg.wait_for_timeout(400)
    for _ in range(6):
        if pg.locator("[data-popquiz]:visible").count(): break
        b = pg.locator(".ecran:visible [data-suivant]:visible")
        if not b.count(): break
        b.first.click(); pg.wait_for_timeout(150)
    props = pg.locator("[data-popquiz] [data-bonus-prop]")
    if props.count():
        props.nth(0).click(); props.nth(1).dispatch_event("click"); props.nth(2).dispatch_event("click")
        pg.wait_for_timeout(200)
        etat = pg.evaluate("""() => { const z=document.querySelector('[data-popquiz]');
          return { gagne: !z.querySelector('[data-bonus-gagne]').hidden, rate: !z.querySelector('[data-bonus-rate]').hidden,
                   bloques: [...z.querySelectorAll('[data-bonus-prop]')].every(b=>b.disabled) }; }""")
        note("bonus : un seul essai compte, les autres clics sont sans effet",
             etat["bloques"] and (etat["gagne"] != etat["rate"]), etat)
    else:
        note("bonus : atteint", False, bonus)
    pg.close()

    print("\n4. Le panneau d'empreinte, le sac, la porte de la serre : saisies fautives")
    pg = page_jeu(); pg.goto(U("E08")); pg.wait_for_timeout(400)
    for _ in range(5):
        if pg.is_visible("#reponse"): break
        pg.locator(".ecran:visible [data-suivant]:visible").first.click(); pg.wait_for_timeout(150)
    pg.fill("#reponse", " "); pg.click("#valider"); pg.wait_for_timeout(150)
    vide_ignore = pg.is_enabled("#reponse") and not pg.is_visible("#resultat")
    pg.fill("#reponse", " 11 "); pg.click("#valider"); pg.wait_for_timeout(150)
    note("panneau : une saisie vide ne coute pas d'essai, « 11 » avec espaces accepte",
         vide_ignore and pg.is_visible("#resultat"), (vide_ignore, pg.text_content("#aCote") if pg.query_selector("#aCote") else ""))
    pg.close()
    pg = page_jeu(); pg.goto(U("E14")); pg.wait_for_timeout(400)
    for _ in range(6):
        if pg.is_visible("#codeSerre"): break
        b = pg.locator(".ecran:visible [data-suivant]:visible")
        if not b.count(): break
        b.first.click(); pg.wait_for_timeout(150)
    pg.fill("#codeSerre", "1234"); pg.click("#validerSerre"); pg.wait_for_timeout(150)
    faux = pg.is_visible("#serreACote") and not pg.is_visible("#serreOuverte")
    pg.fill("#codeSerre", "58 24"); pg.click("#validerSerre"); pg.wait_for_timeout(150)
    note("porte de la serre : mauvais code refuse, « 58 24 » accepte",
         faux and pg.is_visible("#serreOuverte"))
    pg.close()
    pg = page_jeu(); pg.goto(U("E14")); pg.wait_for_timeout(400)
    for _ in range(6):
        if pg.is_visible("#codeSerre"): break
        b = pg.locator(".ecran:visible [data-suivant]:visible")
        if not b.count(): break
        b.first.click(); pg.wait_for_timeout(150)
    pg.fill("#codeSerre", "5824"); pg.press("#codeSerre", "Enter"); pg.wait_for_timeout(200)
    note("porte de la serre : la touche Entree du clavier valide", pg.is_visible("#serreOuverte"))
    pg.close()

    print("\n5. Le mot IRIS : variantes de saisie")
    for saisie in ["iris", " I R I S ", "Íris", "IRIS."]:
        pg = page_jeu(); pg.add_init_script("sessionStorage.setItem('sdb_ecran_/%s', '2')" % PARC["pages"]["E13"])
        pg.goto(U("E13")); pg.wait_for_timeout(400)
        pg.fill("#motFinal", saisie); pg.click("#validerMot"); pg.wait_for_timeout(150)
        note("mot final « %s » accepte du premier coup" % saisie,
             pg.is_visible("[data-mot-trouve]") and "Félicitations" in pg.text_content("[data-mot-bravo]"))
        pg.close()

    print("\n6. La fin : clics multiples, retour, rechargement")
    pg = page_jeu(); pg.add_init_script("sessionStorage.setItem('sdb_ecran_/%s', '1')" % PARC["pages"]["E15"])
    pg.goto(U("E15")); pg.wait_for_timeout(400)
    p = pg.locator("[data-conclusion]")
    p.nth(3).click(); p.nth(0).dispatch_event("click"); p.nth(1).dispatch_event("click"); pg.wait_for_timeout(300)
    ranges = pg.evaluate("window.__scans.filter(x=>x&&x.p_denouement).map(x=>x.p_denouement)")
    note("choix final, triple clic : une seule reponse enregistree", ranges == ["Bon"], ranges)
    pg.reload(); pg.wait_for_timeout(500)
    verr = pg.evaluate("[...document.querySelectorAll('[data-conclusion]')].every(b=>b.disabled)")
    note("recharger apres le choix : il reste verrouille", verr)
    # Aller jusqu'au verdict apres rechargement : les etincelles pour la bonne reponse.
    for _ in range(4):
        if pg.is_visible("[data-verdict-final]"): break
        pg.locator(".ecran:visible [data-suivant]:visible").first.click(); pg.wait_for_timeout(250)
    note("apres rechargement, le verdict reste « Bon »",
         pg.evaluate("[...document.querySelectorAll('[data-denouement]')].filter(x=>!x.hidden).map(x=>x.dataset.denouement)") == ["Bon"])
    pg.close()

    print("\n7. L'avis : double envoi")
    pg = page_jeu(); n = open(os.path.join(R, PARC["pages"]["E15"], "index.html")).read()
    rang = n.count('<section class="ecran', 0, n.index('<section class="ecran card avis"'))
    pg.add_init_script("sessionStorage.setItem('sdb_ecran_/%s', '%d')" % (PARC["pages"]["E15"], rang))
    pg.goto(U("E15")); pg.wait_for_timeout(400)
    pg.locator(".etoile").nth(4).click()
    pg.click("#envoyerAvis"); pg.locator("#envoyerAvis").dispatch_event("click"); pg.wait_for_timeout(300)
    note("avis, double clic sur Envoyer : un seul envoi", len(pg.evaluate("window.__avis || []")) == 1,
         pg.evaluate("window.__avis || []"))
    pg.close()

    print("\n8. Le signalement : numeros fantaisistes")
    for tel, attendu in [("abc", False), ("06 12", False), ("+33 6 12 34 56 78", True), ("0612345678", True)]:
        pg = page_jeu(); pg.route("**/formspree.io/**", lambda r: r.abort())
        pg.goto(U("E10")); pg.wait_for_timeout(300)
        pg.click("#boutonProbleme"); pg.fill("#telProbleme", tel); pg.click("#envoyerProbleme"); pg.wait_for_timeout(400)
        part = len(pg.evaluate("window.__signalements")) == 1
        note("signalement avec « %s » : %s" % (tel, "accepte" if attendu else "refuse"), part == attendu)
        pg.close()

    print("\n9. Le numero de secours")
    pg = page_jeu(); pg.goto(U("E05")); pg.wait_for_timeout(300)
    pg.click("#boutonSecours"); pg.fill("#champSecours", "1234"); pg.click("#validerSecours"); pg.wait_for_timeout(300)
    note("numero de secours faux : message, on reste sur la borne",
         pg.is_visible("#erreurSecours") and pg.url.endswith(PARC["pages"]["E05"]))
    pg.fill("#champSecours", "80 48"); pg.press("#champSecours", "Enter"); pg.wait_for_timeout(500)
    note("numero de secours « 80 48 » valide par Entree : la borne s'ouvre", pg.url.endswith(PARC["pages"]["E06"]), pg.url)
    pg.close()

    print("\n10. Anciennes adresses et adresses inventees")
    pg = page_jeu()
    r = pg.goto("http://127.0.0.1:%d/etapes/e04-indice-les-jumelles-la-carcasse.html" % PORT); pg.wait_for_timeout(300)
    note("ancienne adresse /etapes/... : pas une page blanche (404 du serveur local attendu)",
         r is not None, r and r.status)
    pg.goto(U("E05", "?revoir=<script>alert(1)</script>")); pg.wait_for_timeout(300)
    note("?revoir= piege : aucun bouton, aucune erreur", pg.query_selector(".retour-borne") is None and not pg.__erreurs)
    pg.close()

    nav.close()

ko = [r for r in res if not r[1]]
print("\n%d controles" % len(res))
print("ECHECS : %d %s" % (len(ko), [r[0] for r in ko] if ko else ""))
sys.exit(1 if ko else 0)
