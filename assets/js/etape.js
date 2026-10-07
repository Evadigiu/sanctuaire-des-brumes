// ============================================================
// NAVIGATION D'UNE PAGE D'ÉTAPE — Le Sanctuaire des Brumes
//
// Chaque borne est UNE page, qui contient les écrans des deux sens.
// Au chargement, on retire les écrans qui ne concernent pas le sens
// du groupe, puis on les fait défiler un par un.
//
// Une seule page par borne, parce qu'une borne physique dans le parc
// porte un seul QR code : c'est la page qui s'adapte, pas le joueur.
// ============================================================

function demarrerEtape() {
  // Aucune partie dans ce navigateur : ce n'est pas forcément qu'il n'y en a
  // pas. Le QR a pu ouvrir un autre navigateur que celui du départ. On
  // propose de la retrouver ici, sans quitter la borne.
  //
  // Une partie au chrono écoulé compte comme absente. C'est le plus souvent
  // le reste d'une partie précédente sur ce téléphone (un essai la veille) :
  // la borne renvoyait alors à l'accueil avec « Votre session de jeu est
  // terminée », et le groupe ne pouvait plus démarrer depuis un QR.
  //
  // Seulement pour un code de test : l'équipe remet ces codes à zéro entre
  // deux essais. Un vrai joueur dont le temps est écoulé apprend que son
  // enquête est finie, au lieu d'être invité à la redémarrer. Ce n'est pas
  // le téléphone qui l'empêche de rejouer, c'est la base : elle refuse tout
  // code dont les 3 h sont passées.
  const trouvee = getSession();
  if (trouvee && partieTerminee(trouvee) && !/^TEST/i.test(trouvee.code || "")) {
    afficherPartieTerminee();
    return;
  }
  if (!trouvee || partieTerminee(trouvee)) {
    if (trouvee) oublierPartie();
    proposerDeRetrouverLaPartie(!!trouvee);
    return;
  }

  const session = requireActiveSession();
  if (!session) return;

  startCountdown("timer");
  pleinEcranALaLecture();

  const sens = (session.direction === "antihoraire") ? "B" : "A";
  document.body.setAttribute("data-sens", sens);

  // Le jeu consiste à trouver les bornes. Une borne trop en avance sur la
  // progression réelle du groupe est refusée, sinon deviner une adresse
  // suffirait à sauter la moitié de l'enquête.
  const codeEtape = document.body.getAttribute("data-etape");
  progressionAutorise(codeEtape).then(verdict => {
    if (verdict.ok) { noterVisiteLocale(codeEtape); return; }
    afficherBlocage(verdict);
  });

  // 1. On retire les écrans de l'autre sens.
  document.querySelectorAll("[data-sens]").forEach(el => {
    if (el.getAttribute("data-sens") !== sens) el.remove();
  });

  // 2. La barre de progression et le lien de sortie dépendent du sens.
  afficherProgression(sens);

  // 3. Enregistrement du passage, dès l'arrivée sur la borne.
  //    Choix assumé : on mesure le moment où le groupe arrive physiquement,
  //    pas celui où il appuie sur un bouton. C'est ce qui permet de repérer
  //    les bouchons dans le parc.
  logScan(document.body.getAttribute("data-borne"));

  // 4. Le raccourci vers l'étape suivante n'existe que pour les codes de test.
  //    Un vrai joueur doit trouver la borne et scanner son QR code : c'est le
  //    jeu. L'équipe, elle, doit pouvoir répéter le parcours sans traverser
  //    le parc seize fois.
  const estTest = /^TEST/i.test(session.code || "");
  document.querySelectorAll("[data-lien-test]").forEach(a => {
    if (estTest) a.hidden = false; else a.remove();
  });

  // 5. Défilement des écrans.
  const ecrans = Array.from(document.querySelectorAll(".ecran"));
  const CLE = "sdb_ecran_" + window.location.pathname;
  let courant = parseInt(sessionStorage.getItem(CLE) || "0", 10);
  if (isNaN(courant) || courant < 0 || courant >= ecrans.length) courant = 0;

  // Chaque borne se souvient de l'écran où on l'a quittée, pour qu'un
  // téléphone qui se verrouille ne fasse pas tout recommencer. Mais quand on
  // revient exprès pour revoir un témoignage, ce souvenir joue contre nous :
  // on rouvrait la borne sur son dernier écran, « où aller ensuite », alors
  // qu'on venait précisément pour la vidéo. On repart donc du début.
  if (new URLSearchParams(window.location.search).has("revoir")) courant = 0;

  function afficher(i) {
    courant = i;
    try { sessionStorage.setItem(CLE, String(i)); } catch (e) {}
    ecrans.forEach((el, n) => { el.hidden = (n !== i); });
    reglerRetour(i);
    window.scrollTo(0, 0);
    // On coupe toute vidéo ou audio de l'écran qu'on quitte.
    document.querySelectorAll("video, audio").forEach(m => {
      if (!m.closest(".ecran") || m.closest(".ecran").hidden) { m.pause(); }
    });
  }

  document.querySelectorAll("[data-suivant]").forEach(b => {
    b.addEventListener("click", () => {
      if (courant < ecrans.length - 1) afficher(courant + 1);
    });
  });
  // « Revenir en arrière » ne pouvait rien faire sur le premier écran d'une
  // borne : il n'y a pas d'écran avant. Il ramène désormais à la borne
  // précédente, pour revoir un témoignage. Le verrouillage l'autorisait déjà
  // — il autorise toute borne déjà visitée — il manquait juste le chemin.
  const precedente = document.body.getAttribute("data-prec-" + sens) || "";
  const pagePrecedente = PARCOURS.pages[precedente] || "";

  document.querySelectorAll("[data-retour]").forEach(b => {
    b.addEventListener("click", () => {
      if (courant > 0) { afficher(courant - 1); return; }
      if (pagePrecedente) {
        // On emporte le code de la borne d'où l'on vient, pour pouvoir y
        // revenir sans rescanner le QR.
        window.location.href = BASE_PATH + pagePrecedente
                             + "?revoir=" + encodeURIComponent(codeEtape);
      }
    });
  });

  /**
   * Le bouton de retour du premier écran ne dit pas la même chose que les
   * autres, et disparaît quand il n'y a nulle part où revenir : un bouton
   * qui ne fait rien use la confiance plus vite qu'un bouton absent.
   */
  function reglerRetour(i) {
    const bouton = ecrans[i] && ecrans[i].querySelector("[data-retour]");
    if (!bouton) return;
    if (i > 0) {
      bouton.hidden = false;
      bouton.textContent = "Revenir en arrière";
    } else if (pagePrecedente) {
      bouton.hidden = false;
      bouton.textContent = "Revoir le témoignage précédent";
    } else {
      bouton.hidden = true;
    }
  }

  brancherConfirmationIndice();
  afficher(courant);
  brancherSecours();
  brancherRetourAMaBorne();
}

/**
 * La borne s'ouvre sans partie en cours. Deux groupes arrivent ici :
 *   - ceux qui n'ont pas encore démarré, parce qu'ils ont scanné le QR de
 *     la borne au lieu de passer par l'accueil. C'est le cas le plus
 *     fréquent, il passe donc en premier ;
 *   - ceux dont le téléphone a perdu la partie en route. Ils ressaisissent
 *     le code du billet et restent sur la borne.
 *
 * Avant, la borne renvoyait tout le monde à l'accueil avec un message
 * d'erreur, y compris ceux qui n'avaient rien fait de travers.
 */
function proposerDeRetrouverLaPartie(ancienneTrouvee) {
  if (!ancienneTrouvee && !borneDeDepart()) signalerPartieIntrouvable();
  document.querySelectorAll(".ecran").forEach(e => e.remove());
  const timer = document.getElementById("timer");
  if (timer) timer.remove();
  brancherSecours();

  const accueil = BASE_PATH + "index.html";
  const bloc = document.createElement("section");
  bloc.className = "ecran card";
  bloc.id = "retrouverPartie";
  bloc.innerHTML =
    '<div class="ecran-titre">Votre enquête commence à l\'accueil</div>'
    + '<p>Pour démarrer, munissez-vous du code inscrit sur votre billet.</p>'
    + '<a href="' + accueil + '" class="btn" id="versAccueil">Démarrer l\'enquête</a>'
    + '<p class="muted">Votre enquête est déjà en cours ? Saisissez votre code '
    + 'pour la retrouver ici.</p>'
    + '<label for="codeReprise">Le code de votre billet</label>'
    + '<input type="text" id="codeReprise" autocomplete="off" autocapitalize="characters" '
    + 'spellcheck="false" placeholder="Ex. K7NPX4RT">'
    + '<div class="error-box visible" id="erreurReprise" hidden></div>'
    + '<button class="btn-secondary" id="validerReprise">Reprendre mon enquête</button>';
  document.querySelector(".wrap").appendChild(bloc);
  bloc.hidden = false;

  const champ = document.getElementById("codeReprise");
  const bouton = document.getElementById("validerReprise");
  const err = document.getElementById("erreurReprise");

  bouton.addEventListener("click", async () => {
    bouton.disabled = true;
    bouton.textContent = "Vérification...";
    err.hidden = true;

    const result = await reprendrePartie(champ.value);
    if (result.ok) { window.location.reload(); return; }

    // Un code jamais activé : le groupe n'a pas encore démarré. On l'envoie
    // à l'accueil avec son code déjà saisi, plutôt que de lui opposer un refus.
    if (result.pasCommencee) {
      window.location.href = accueil + "?code=" + encodeURIComponent(champ.value.trim());
      return;
    }

    err.textContent = result.message;
    err.hidden = false;
    bouton.disabled = false;
    bouton.textContent = "Reprendre mon enquête";
  });
}

/**
 * Le temps est écoulé pour un vrai billet. On le dit sur la borne même,
 * sans renvoyer à l'accueil. Le lien sert aux visiteurs revenus un autre
 * jour avec un nouveau billet : l'ancien code, lui, reste refusé par la base.
 */
function afficherPartieTerminee() {
  document.querySelectorAll(".ecran").forEach(e => e.remove());
  const timer = document.getElementById("timer");
  if (timer) timer.remove();
  brancherSecours();

  const bloc = document.createElement("section");
  bloc.className = "ecran card";
  bloc.id = "partieTerminee";
  bloc.innerHTML =
    '<div class="ecran-titre">Votre enquête est terminée</div>'
    + '<p>Les 3 heures de votre partie sont écoulées. Merci d\'avoir mené l\'enquête !</p>'
    + '<p class="muted">Vous avez un nouveau billet ? '
    + '<a href="' + BASE_PATH + 'index.html" id="nouveauBillet">Démarrez une nouvelle enquête</a>.</p>';
  document.querySelector(".wrap").appendChild(bloc);
  bloc.hidden = false;
}

/** La borne ouvre-t-elle le parcours, dans l'un des deux sens ? */
function borneDeDepart() {
  const c = document.body.getAttribute("data-etape");
  return ["A", "B"].some(sens => PARCOURS.ordre[sens] && PARCOURS.ordre[sens][c] === 1);
}

/**
 * Une partie qui disparaît entre deux scans faits du même geste, on ne sait
 * pas encore l'expliquer à coup sûr. Plutôt que de deviner, la borne laisse
 * une trace dans les signalements du tableau de bord, sans rien demander au
 * joueur. Deux indices départagent les explications :
 *   - les bornes déjà visitées sont-elles encore en mémoire ? Si oui, seule
 *     la partie a disparu, et c'est une affaire de code. Si non, toute la
 *     mémoire est vide : la page s'est ouverte dans un autre navigateur, un
 *     autre profil ou un onglet privé ;
 *   - le navigateur annoncé : une application qui ouvre ses liens dans sa
 *     propre fenêtre se reconnaît à son nom (CriOS, GSA, Instagram...).
 */
function signalerPartieIntrouvable() {
  let traces = "?", ecrans = "?";
  try { traces = localStorage.getItem(VISITES_KEY) ? "oui" : "non"; } catch (e) { traces = "illisible"; }
  try {
    ecrans = Object.keys(sessionStorage).filter(k => k.indexOf("sdb_ecran_") === 0).length;
  } catch (e) { ecrans = "illisible"; }

  const message = [
    "Diagnostic automatique : partie introuvable à l'ouverture de la borne.",
    "Bornes visitées en mémoire : " + traces,
    "Écrans en mémoire dans cet onglet : " + ecrans,
    "Pages dans cet onglet : " + history.length,
    "Venue de : " + (document.referrer || "aucune page"),
    "Navigateur : " + navigator.userAgent,
  ].join("\n").slice(0, 500);

  supabaseClient.from("signalements").insert({
    code_id: null,
    borne: document.body.getAttribute("data-borne"),
    categorie: "bug",
    message: message,
  }).then(() => {}, () => {});
}

// ------------------------------------------------------------
// Épreuve à réponse vérifiée (le panneau d'empreintes).
// La lettre n'apparaît que si la réponse est la bonne.
// ------------------------------------------------------------
/**
 * Fait basculer la vidéo en plein écran dès que le joueur appuie sur
 * lecture. Un témoignage filmé dans un rectangle de six centimètres au
 * milieu d'une page, ce n'est pas une scène, c'est une vignette.
 *
 * Trois façons de le demander selon le téléphone. Sur iPhone c'est la
 * première, et elle marche déjà toute seule depuis qu'on a retiré
 * l'attribut "playsinline" du lecteur : celui-ci demandait justement
 * l'inverse.
 *
 * Le navigateur a le droit de refuser, et il le fait parfois sans qu'on
 * sache pourquoi. Dans ce cas la vidéo se lit dans la page, comme avant :
 * on ne bloque jamais la lecture pour une question de confort.
 */
function pleinEcranALaLecture() {
  document.querySelectorAll("video").forEach(video => {
    // La feuille de style donne d'avance au cadre la forme d'une video de
    // telephone, pour qu'il ne soit pas ecrase avant lecture. Des que les
    // vraies dimensions sont connues, on lui rend sa liberte : une video
    // horizontale reprend sa forme plutot que d'etre encadree de noir.
    video.addEventListener("loadedmetadata", () => {
      video.style.aspectRatio = "auto";
    }, { once: true });

    video.addEventListener("play", () => {
      try {
        if (video.webkitEnterFullscreen)        video.webkitEnterFullscreen();
        else if (video.requestFullscreen)       video.requestFullscreen().catch(() => {});
        else if (video.webkitRequestFullscreen) video.webkitRequestFullscreen();
      } catch (e) {
        console.warn("Plein écran refusé :", e && e.message);
      }
    }, { once: true });   // une seule fois : qui ressort du plein écran l'a voulu
  });
}

/**
 * Remplit la barre de progression selon le sens du groupe.
 *
 * Une ligne de texte disait « Étape 2 sur 15 ». Une barre se lit d'un coup
 * d'œil, sans lire : c'est ce qu'on veut d'un groupe qui marche dans un
 * parc avec un chrono de 3 h. Le compte chiffré reste à côté, parce qu'un
 * trait rempli au tiers ne dit pas combien de bornes il reste à trouver.
 *
 * Sur une borne qui n'appartient pas au parcours du groupe (elles sont
 * physiques, on peut tomber dessus en se promenant), le numéro est vide :
 * on retire la barre plutôt que d'en afficher une à zéro, qui ferait
 * croire au groupe qu'il est revenu au début.
 */
function afficherProgression(sens) {
  const zone = document.getElementById("position");
  if (!zone) return;

  const n     = parseInt(zone.getAttribute("data-" + sens), 10);
  const total = parseInt(zone.getAttribute("data-total-" + sens), 10);

  if (!n || !total) { zone.remove(); return; }

  const part = Math.min(100, Math.round(n / total * 100));
  zone.style.setProperty("--part", part + "%");
  zone.setAttribute("aria-valuenow", part);
  zone.setAttribute("aria-valuetext", "Étape " + n + " sur " + total);

  const compte = zone.querySelector(".progression-compte");
  if (compte) compte.textContent = n + " / " + total;

  zone.hidden = false;
}

/**
 * L'écran qui demande au joueur s'il a trouvé l'indice avant de le lui
 * donner. « Oui » se comporte comme un bouton Suivant ordinaire ; « Non »
 * révèle la lettre, puis laisse continuer.
 *
 * On ne bloque jamais : un groupe coincé devant un enclos un dimanche de
 * novembre abandonne, il ne cherche pas plus longtemps.
 */
function brancherConfirmationIndice() {
  document.querySelectorAll("[data-confirmation]").forEach(zone => {
    const non    = zone.querySelector("[data-indice-non]");
    const choix  = zone.querySelector("[data-indice-choix]");
    const revele = zone.querySelector("[data-indice-revele]");
    if (!non || !choix || !revele) return;
    non.addEventListener("click", () => {
      choix.hidden = true;
      revele.hidden = false;
    });
  });
}

function epreuveReponse(idChamp, idBouton, bonneReponse, idResultat) {
  const champ = document.getElementById(idChamp);
  const bouton = document.getElementById(idBouton);
  const resultat = document.getElementById(idResultat);
  if (!champ || !bouton || !resultat) return;

  bouton.addEventListener("click", () => {
    const saisi = champ.value.trim().toLowerCase();
    if (saisi === String(bonneReponse).toLowerCase()) {
      resultat.hidden = false;
      champ.disabled = true;
      bouton.disabled = true;
    } else {
      resultat.hidden = true;
      champ.setAttribute("aria-invalid", "true");
      champ.value = "";
      champ.placeholder = "Ce n'est pas la bonne réponse, regardez mieux.";
    }
  });
}

// ------------------------------------------------------------
// Appel entrant : le son ne part qu'au clic sur "décrocher".
// ------------------------------------------------------------
function appelEntrant(idBouton, idAudio, idBloc) {
  const bouton = document.getElementById(idBouton);
  const audio = document.getElementById(idAudio);
  const bloc = document.getElementById(idBloc);
  if (!bouton) return;
  bouton.addEventListener("click", () => {
    bouton.hidden = true;
    if (bloc) bloc.hidden = false;
    if (audio) audio.play().catch(() => {});
  });
}

// ------------------------------------------------------------
// Écran de refus : le groupe a sauté des bornes.
// On ne l'accuse de rien, on lui dit où il en est.
// ------------------------------------------------------------
function afficherBlocage(verdict) {
  document.querySelectorAll(".ecran").forEach(e => e.remove());
  const session = getSession();
  const sens = sensDuGroupe(session);
  const attendue = Object.keys(PARCOURS.ordre[sens])
    .find(c => PARCOURS.ordre[sens][c] === verdict.attendue);

  const bloc = document.createElement("section");
  bloc.className = "ecran card";
  bloc.innerHTML =
    '<div class="ecran-titre">Cette borne n\'est pas la vôtre, pas encore</div>'
    + '<p>Votre enquête en est à l\'étape ' + verdict.attendue
    + ', et cette borne est la numéro ' + verdict.demandee + '.</p>'
    + '<p class="muted">Reprenez le chemin indiqué à votre dernière étape. '
    + 'Les bornes se suivent, et chacune vous apprend quelque chose dont '
    + 'la suivante a besoin.</p>'
    + (attendue ? '<p class="consigne-scan">Votre prochaine borne : '
        + PARCOURS.noms[attendue] + '.</p>' : '');
  document.querySelector(".wrap").appendChild(bloc);
  bloc.hidden = false;
}

// ============================================================
// LES DEUX SECOURS DU TERRAIN
// Toujours accessibles, sur chaque borne, sans quitter la page.
// ============================================================

/**
 * Le QR refuse de se lire : le joueur saisit le nombre à 4 chiffres
 * imprimé sur l'affichette, à côté du code.
 *
 * Ces nombres ne se suivent pas d'une borne à l'autre : lire une
 * affichette ne permet pas de deviner les suivantes. Et la borne
 * atteinte par ce chemin passe le même contrôle de progression que
 * celle atteinte par le QR, donc ce n'est pas une porte dérobée.
 */
function ouvrirSecours() {
  const zone = document.getElementById("zoneSecours");
  const champ = document.getElementById("champSecours");
  const err = document.getElementById("erreurSecours");
  zone.hidden = false;
  err.hidden = true;
  champ.value = "";
  champ.focus();

  document.getElementById("validerSecours").onclick = () => {
    const saisi = (champ.value || "").trim();
    const cible = PARCOURS.secours[saisi];
    if (!cible) {
      err.textContent = "Ce numéro ne correspond à aucune borne. Vérifiez les quatre chiffres.";
      err.hidden = false;
      return;
    }
    // Les bornes sont des dossiers voisins, pas des sous-dossiers : il faut
    // remonter à la racine, sinon on empile /1965/3215/ au lieu d'aller à /3215/.
    window.location.href = BASE_PATH + PARCOURS.pages[cible];
  };
}

/**
 * Un QR décollé, un décor abîmé, un écran qui se bloque : l'équipe doit
 * l'apprendre pendant l'événement, pas dans le bilan.
 */
function ouvrirProbleme() {
  const zone = document.getElementById("zoneProbleme");
  zone.hidden = false;
  document.getElementById("envoyerProbleme").onclick = async () => {
    const bouton = document.getElementById("envoyerProbleme");
    const retour = document.getElementById("retourProbleme");
    const session = getSession();
    bouton.disabled = true;
    bouton.textContent = "Envoi...";

    const { error } = await supabaseClient.from("signalements").insert({
      code_id: session ? session.codeId : null,
      borne: document.body.getAttribute("data-borne"),
      categorie: document.getElementById("categorieProbleme").value,
      message: (document.getElementById("messageProbleme").value || "").slice(0, 500),
    });

    if (error) {
      retour.textContent = "Le signalement n'est pas parti. Prévenez un membre de l'équipe sur place.";
      bouton.disabled = false;
      bouton.textContent = "Envoyer";
    } else {
      retour.textContent = "C'est noté, merci. L'équipe est prévenue. Vous pouvez continuer votre enquête.";
      document.getElementById("formProbleme").hidden = true;
    }
    retour.hidden = false;
  };
}

/**
 * Quand on arrive sur une borne par « revoir le témoignage précédent »,
 * l'adresse porte le code de la borne d'où l'on vient. On propose alors un
 * retour direct : sans lui, le groupe devrait rescanner le QR de la borne
 * devant laquelle il se tient déjà.
 *
 * Ce n'est pas une porte dérobée : le code doit désigner une borne connue du
 * parcours, et cette borne passe le même contrôle de progression que
 * n'importe quelle autre.
 */
function brancherRetourAMaBorne() {
  const demande = new URLSearchParams(window.location.search).get("revoir");
  const page = demande && PARCOURS.pages[demande];
  if (!page) return;

  const lien = document.createElement("a");
  lien.className = "btn btn-secondary retour-borne";
  lien.href = BASE_PATH + page;
  lien.textContent = "Revenir à ma borne : " + (PARCOURS.noms[demande] || "");

  const titre = document.querySelector("h1");
  if (titre && titre.parentNode) titre.parentNode.insertBefore(lien, titre.nextSibling);
}

function brancherSecours() {
  const b1 = document.getElementById("boutonSecours");
  const b2 = document.getElementById("boutonProbleme");
  if (b1) b1.addEventListener("click", ouvrirSecours);
  if (b2) b2.addEventListener("click", ouvrirProbleme);
}
