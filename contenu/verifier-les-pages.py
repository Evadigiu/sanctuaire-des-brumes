# -*- coding: utf-8 -*-
"""
Verifie les pages fabriquees, avant de les mettre en ligne.

    python3 contenu/verifier-les-pages.py

Ne modifie rien. Parcourt les deux sens de bout en bout comme le ferait un
joueur, et s'assure qu'aucune borne ne le laisse sans porte de sortie.
"""
import os, re, sys, glob, io, html as H

ICI    = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
ETAPES = RACINE
DEPART = None   # calcule depuis le plan du parcours

def lire(f): return io.open(f, encoding="utf-8").read()

def libelles_sql():
    """Les libelles de borne, apostrophes SQL ('') ramenees a une seule."""
    t = lire(os.path.join(ICI, "bornes.sql"))
    bruts = re.findall(r"\('((?:[^']|'')+)',\s*'(?:temoin|side_quest|final)'\)", t)
    return set(b.replace("''", "'") for b in bruts)

def main():
    pb, av = [], []
    import json
    plan = json.loads(lire(os.path.join(RACINE, "assets", "js", "parcours.js"))
                      .split("const PARCOURS =", 1)[1].rstrip().rstrip(";"))
    pages = sorted(glob.glob(os.path.join(ETAPES, "[0-9]*", "index.html")))
    global DEPART
    DEPART = [c for c in plan["ordre"]["A"] if plan["ordre"]["A"][c] == 1][0]
    DEPART = plan["pages"][DEPART]
    if not pages:
        print("Aucune page. Lancer d'abord fabriquer-les-pages.py."); return 1

    # 1. Les libelles envoyes a la base existent-ils en base ?
    #    Les entites HTML sont decodees : &#x27; est une apostrophe pour le
    #    navigateur, donc la comparaison doit se faire apres decodage.
    bornes = libelles_sql()
    for f in pages:
        m = re.search(r'data-borne="([^"]+)"', lire(f))
        if not m:
            pb.append("%s : aucune borne declaree, le passage ne sera pas enregistre."
                      % os.path.basename(os.path.dirname(f))); continue
        lab = H.unescape(m.group(1))
        if lab not in bornes:
            pb.append("%s : la borne \"%s\" n'existe pas dans bornes.sql. Le passage du "
                      "groupe serait perdu sans aucun message d'erreur."
                      % (os.path.basename(os.path.dirname(f)), lab))

    # 2. Les deux parcours, suivis de bout en bout
    attendu = len(pages) - 1          # une borne n'appartient qu'a un seul sens
    fins = {}
    for sens in ("A", "B"):
        vus, cur, n = [], DEPART, 0
        while cur and n < 40:
            p = os.path.join(ETAPES, cur.strip("/"), "index.html")
            if not os.path.exists(p):
                pb.append("SENS %s : lien mort vers %s." % (sens, cur)); break
            h = lire(p)
            vus.append(re.search(r"<h1>(.*?)</h1>", h).group(1))
            bloc = re.search(r'<section class="ecran card" data-sens="%s" hidden>(.*?)</section>'
                             % sens, h, re.S)
            if not bloc:
                # Pas d'ecran propre a ce sens : soit c'est la derniere etape,
                # commune aux deux parcours, soit le joueur est vraiment bloque.
                if 'data-sens=' in h:
                    pb.append("SENS %s : %s n'a aucun écran pour ce sens. Le joueur serait bloqué."
                              % (sens, cur))
                fins.setdefault(sens, cur)
                break
            m = re.search(r'href="\.\./([0-9]+/)"', bloc.group(1))
            if not m: fins.setdefault(sens, cur)
            cur = m.group(1) if m else None
            n += 1
        if len(vus) != attendu:
            av.append("SENS %s : %d étapes enchaînées, %d attendues." % (sens, len(vus), attendu))
        print("SENS %s : %d étapes" % (sens, len(vus)))
        print("   " + " > ".join(v[:16] for v in vus))

    if fins.get("A") != fins.get("B"):
        av.append("Les deux sens ne finissent pas au même endroit : %s en sens A, %s en sens B."
                  % (fins.get("A"), fins.get("B")))

    # 3. Une borne qui parle a un seul sens doit quand meme repondre a l'autre :
    #    elle est physique, un groupe peut tomber dessus en se promenant.
    #    Une page sans aucun ecran propre a un sens est une etape commune,
    #    elle s'affiche pareil pour tout le monde, c'est legitime.
    for f in pages:
        h = lire(f)
        if 'data-sens=' not in h: continue
        for sens in ("A", "B"):
            if 'data-sens="%s"' % sens not in h:
                pb.append("%s : rien de prévu pour un joueur du sens %s qui scannerait "
                          "cette borne par hasard." % (os.path.basename(os.path.dirname(f)), sens))

    # 4. Balises equilibrees
    for f in pages:
        h = lire(f)
        for tag in ("div", "section", "script", "body", "html", "video"):
            o = len(re.findall(r"<%s[ >]" % tag, h)); c = len(re.findall(r"</%s>" % tag, h))
            if o != c:
                pb.append("%s : balise <%s> déséquilibrée (%d ouvertes, %d fermées)."
                          % (os.path.basename(os.path.dirname(f)), tag, o, c))

    # 5. bornes.sql est-il du SQL valide ?
    #    Un insert multi-lignes ou une virgule tombe dans un commentaire est
    #    rejete en bloc par Postgres. C'est arrive une fois, plus jamais.
    sqltxt = lire(os.path.join(ICI, "bornes.sql"))
    corps = sqltxt[sqltxt.index("values") + 6:] if "values" in sqltxt else ""
    corps = corps.split("select count")[0]
    tuples = 0
    for ligne in corps.splitlines():
        code = ligne.split("--")[0].rstrip()     # on jette le commentaire
        if not code.strip(): continue
        tuples += 1
        dernier = tuples == len(bornes)
        if dernier and not code.endswith(";"):
            pb.append("bornes.sql : le dernier tuple ne finit pas par \";\". "
                      "La requête serait incomplète.")
        elif not dernier and not code.endswith(","):
            pb.append("bornes.sql : virgule manquante après %s. Postgres rejetterait "
                      "la requête entière." % code.strip()[:40])
    if tuples != len(bornes):
        pb.append("bornes.sql : %d lignes de valeurs pour %d bornes." % (tuples, len(bornes)))

    # 6. Ce qui reste a faire, signale sans alarmer
    for f in pages:
        h = lire(f)
        n = h.count("A CONSTRUIRE") + h.count("a-construire")
        if n: av.append("%s : contient une mécanique encore à construire." % os.path.basename(os.path.dirname(f)))
        if '<source src=""' in h:
            av.append("%s : média non encore intégré (vidéo ou audio vide)." % os.path.basename(os.path.dirname(f)))

    print("\n" + "=" * 78)
    print("BLOQUANT (%d)" % len(pb)); print("-" * 78)
    for x in pb: print("  * " + x)
    if not pb: print("  aucun")
    print("\nA SAVOIR (%d)" % len(av)); print("-" * 78)
    for x in av: print("  - " + x)
    return 1 if pb else 0

if __name__ == "__main__":
    sys.exit(main())
