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
  // Avant le premier jour de jeu, la page est couverte par la fenêtre de la
  // billetterie : on n'enregistre rien, pas même un signalement, pour que
  // les curieux ne remplissent pas le tableau de bord. Voir avant-ouverture.js.
  if (typeof avantOuverture === "function" && avantOuverture()) return;

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
    couperLesMediasCaches();
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
  brancherQuestionBonus();
  brancherQuizVideo();
  brancherCoupDePouce();
  brancherMotFinal();
  garderLesMediasSousControle();
  afficher(courant);
  brancherSecours();
  brancherRetourAMaBorne();
  conseillerLeScanner();
}

// ------------------------------------------------------------
// LE SON NE DOIT JAMAIS JOUER DERRIÈRE LE JOUEUR
//
// Constaté sur le terrain, sur iPhone : on verrouille le téléphone entre
// deux bornes, on le rouvre sur « Où aller ensuite », et le témoignage
// d'avant reparle tout seul. Ou bien on quitte un témoignage en cours, et
// le son suit le groupe sur l'écran suivant. L'iPhone relance volontiers un
// média : depuis l'écran verrouillé, au retour dans le navigateur, à la
// sortie du plein écran.
//
// On ne cherche pas à deviner lequel de ces chemins : une seule règle les
// couvre tous. Un média ne joue que si son écran est affiché et la page
// visible. Tout le reste est coupé, y compris un média qui tente de
// repartir de lui-même.
// ------------------------------------------------------------

/** Le média est-il sur l'écran que le joueur a sous les yeux ? */
function mediaVisible(m) {
  // Une vidéo en plein écran est, par définition, sous les yeux du joueur.
  // Sur iPhone, le lecteur natif passe PAR-DESSUS la page, que le navigateur
  // peut alors tenir pour cachée : sans cette exception, la garde coupait la
  // vidéo du commissaire en pleine lecture, vers 50 secondes, au moment où
  // l'iPhone chargeait la suite.
  //
  // Mais l'écran passe avant tout : un écran quitté coupe sa vidéo, plein
  // écran ou non.
  const ecran = m.closest(".ecran");
  if (!ecran || ecran.hidden) return false;
  if (m.webkitDisplayingFullscreen || document.fullscreenElement === m) return true;
  return !document.hidden;
}

function couperLesMediasCaches() {
  document.querySelectorAll("video, audio").forEach(m => {
    if (!mediaVisible(m)) m.pause();
  });
}

function couperTousLesMedias() {
  document.querySelectorAll("video, audio").forEach(m => m.pause());
}

function garderLesMediasSousControle() {
  document.querySelectorAll("video, audio").forEach(m => {
    // La garde : un média qui démarre sur un écran caché, ou page masquée,
    // est arrêté aussitôt. C'est elle qui tient le cas de l'écran verrouillé.
    // Seulement au DÉMARRAGE de la lecture (« play »), pas à chaque reprise
    // après un chargement (« playing ») : celle-là, l'iPhone la déclenche
    // seul en cours de lecture, et la couper arrêtait la vidéo.
    m.addEventListener("play", () => { if (!mediaVisible(m)) m.pause(); });
    // Sortir du plein écran, c'est avoir fini de regarder. Sur iPhone, la
    // vidéo continuait alors dans la page, son compris.
    if (!m.hasAttribute("data-quiz-video")) {
      m.addEventListener("webkitendfullscreen", () => m.pause());
    }
  });
  // La vidéo du quiz ne va JAMAIS en plein écran : les questions
  // apparaissent dessous, le groupe ne les verrait pas. Sur iPhone, on la
  // fait ressortir aussitôt ; ailleurs, controlslist retire déjà le bouton.
  document.querySelectorAll("video[data-quiz-video]").forEach(v => {
    v.addEventListener("webkitbeginfullscreen", () => {
      setTimeout(() => { try { v.webkitExitFullscreen(); } catch (e) {} }, 0);
    });
  });
  document.addEventListener("fullscreenchange", () => {
    const fs = document.fullscreenElement;
    if (fs && fs.matches && fs.matches("video[data-quiz-video]")) {
      try { document.exitFullscreen(); } catch (e) {}
    }
  });
  // Plein écran des autres téléphones : on coupe la vidéo qui en sort.
  document.addEventListener("fullscreenchange", () => {
    if (!document.fullscreenElement) {
      document.querySelectorAll("video:not([data-quiz-video])").forEach(v => v.pause());
    }
  });
  // Téléphone verrouillé, autre application, page quittée : tout s'arrête.
  // Au retour, rien ne repart sans que le joueur appuie sur lecture.
  // Une vidéo en plein écran n'est pas touchée : l'iPhone la met lui-même en
  // pause au verrouillage, et la page peut sembler cachée pendant qu'on la regarde.
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) return;
    document.querySelectorAll("video, audio").forEach(m => {
      if (!(m.webkitDisplayingFullscreen || document.fullscreenElement === m)) m.pause();
    });
  });
  window.addEventListener("pagehide", couperTousLesMedias);
}

/**
 * Le groupe vient de ressaisir son code, parce que le QR s'est ouvert dans
 * une autre fenêtre que celle du départ. Sans conseil, la même chose se
 * reproduira à la borne suivante : on le lui dit une fois, en haut de page.
 */
function conseillerLeScanner() {
  let aConseiller = false, auDepart = false;
  try {
    aConseiller = sessionStorage.getItem("sdb_conseil_scanner") === "1";
    auDepart = sessionStorage.getItem("sdb_conseil_depart") === "1";
    sessionStorage.removeItem("sdb_conseil_scanner");
    sessionStorage.removeItem("sdb_conseil_depart");
  } catch (e) {}
  if (!aConseiller && !auDepart) return;

  const note = document.createElement("div");
  note.className = "card";
  note.id = "conseilScanner";
  note.innerHTML =
      (auDepart ? '<p><strong>Votre enquête commence, le chrono est lancé.</strong></p>'
                : '<p><strong>Votre enquête est retrouvée.</strong></p>')
    + '<p class="muted">Pour ne pas avoir à ressaisir votre code, scannez les prochaines '
    + 'bornes avec le bouton « Scanner le QR code » proposé à la fin de chaque borne, '
    + 'et non avec l\'appareil photo.</p>';
  const titre = document.querySelector(".wrap h1");
  if (titre) titre.insertAdjacentElement("afterend", note);
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

  // La borne du départ est la porte d'entrée du jeu : c'est le premier QR
  // que le groupe scanne. Elle l'accueille et ouvre la partie sur place.
  if (borneDeDepart()) { accueillirAuDepart(); return; }

  // L'accueil, en emportant la borne qu'on vient de scanner. Elle sert a
  // renvoyer le groupe ici meme une fois sa partie ouverte, au lieu de lui
  // demander de rescanner le QR code qu'il a sous les yeux. L'accueil ne
  // la suit que si c'est la premiere borne de son sens : c'est lui qui
  // decide, pas la borne.
  const codeBorne = document.body.getAttribute("data-etape") || "";
  const accueil = BASE_PATH + "index.html";
  const accueilDepuisIci = accueil
        + (codeBorne ? "?borne=" + encodeURIComponent(codeBorne) : "");
  const bloc = document.createElement("section");
  bloc.className = "ecran card";
  bloc.id = "retrouverPartie";

  const saisie =
      '<label for="codeReprise">Le code de votre billet</label>'
    + '<input type="text" id="codeReprise" autocomplete="off" autocapitalize="characters" '
    + 'spellcheck="false" placeholder="Ex. K7NPX4RT">'
    + '<div class="error-box visible" id="erreurReprise" hidden></div>';

  // Sur une borne de départ, le groupe qui arrive sans partie n'a le plus
  // souvent pas encore commencé : on le pousse vers l'accueil. Sur une borne
  // du milieu du parcours, c'est l'inverse. Il a démarré, et le lecteur de QR
  // a ouvert un autre navigateur que celui du départ. Lui proposer d'abord
  // de « démarrer l'enquête » lui laissait croire qu'il avait tout perdu.
  if (borneDeDepart()) {
    bloc.innerHTML =
      '<div class="ecran-titre">Votre enquête commence à l\'accueil</div>'
      + '<p>Pour démarrer, munissez-vous du code inscrit sur votre billet.</p>'
      + '<a href="' + accueilDepuisIci + '" class="btn" id="versAccueil">Démarrer l\'enquête</a>'
      + '<p class="muted">Votre enquête est déjà en cours ? Saisissez votre code '
      + 'pour la retrouver ici.</p>'
      + saisie
      + '<button class="btn-secondary" id="validerReprise">Reprendre mon enquête</button>';
  } else {
    bloc.innerHTML =
      '<div class="ecran-titre">Retrouvez votre enquête</div>'
      + '<p>Ce téléphone ne retrouve pas votre partie : le lecteur de QR code a '
      + 'sans doute ouvert un autre navigateur que celui du départ. Saisissez le '
      + 'code de votre billet pour reprendre ici, sans rien perdre.</p>'
      + saisie
      + '<button class="btn" id="validerReprise">Reprendre mon enquête</button>'
      + '<p class="muted">Vous n\'avez pas encore commencé ? '
      + '<a href="' + accueil + '" id="versAccueil">Démarrez l\'enquête à l\'accueil</a>.</p>';
  }
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
    if (result.ok) {
      // La partie est retrouvée dans ce navigateur. Elle n'y restera que si
      // les bornes suivantes s'ouvrent ici aussi, donc par le scanner du site.
      try { sessionStorage.setItem("sdb_conseil_scanner", "1"); } catch (e) {}
      window.location.reload();
      return;
    }

    // Un code jamais activé : le groupe n'a pas encore démarré. On l'envoie
    // à l'accueil avec son code déjà saisi, plutôt que de lui opposer un refus.
    if (result.pasCommencee) {
      window.location.href = accueil + "?code=" + encodeURIComponent(champ.value.trim())
                          + (codeBorne ? "&borne=" + encodeURIComponent(codeBorne) : "");
      return;
    }

    err.textContent = result.message;
    err.hidden = false;
    bouton.disabled = false;
    bouton.textContent = "Reprendre mon enquête";
  });
}

/**
 * L'ACCUEIL SUR LA BORNE DU DÉPART.
 *
 * Le premier QR que voit un groupe est celui du commissaire. Il le scanne
 * avant d'avoir rien démarré : la borne lui souhaite la bienvenue, lui
 * demande son équipe, son nombre et le code de son billet, et ouvre la
 * partie ici même. Avant, elle le renvoyait à la page d'accueil, qui le
 * renvoyait ensuite à la borne : deux détours pour un groupe déjà sur place.
 *
 * Les textes sont ceux de la page d'accueil (étape E00 du cahier). Les
 * changer ici ET dans index.html.
 *
 * Un code déjà activé rouvre sa partie au lieu d'être refusé (le guichet
 * activer_code s'en charge) : le même formulaire sert donc à reprendre.
 */
/**
 * Les logos des partenaires, sur leur plaque claire. Une seule image : la
 * planche fournie par l'organisation. Sans lien : un logo touché par erreur
 * ferait quitter l'enquête.
 */
function blocPartenaires(titre) {
  return '<div class="partenaires">'
    + '<div class="partenaires-titre">' + titre + '</div>'
    + '<div class="partenaires-plaque"><img src="' + BASE_PATH + 'assets/img/partenaires.webp" '
    + 'loading="lazy" alt="Les Pouss\'murs, Melfor, Maisons Clever\'Hom, Mercedes-Benz Kroely, Fimaris, Olivia\'s Garden, Xperience Park, Aveline, Costco Wholesale, Énergie de l\'Est, L\'Alsace, JDS"></div>'
    + '</div>';
}

function accueillirAuDepart() {
  const wrap = document.querySelector(".wrap");
  const codeBorne = document.body.getAttribute("data-etape") || "";
  const params = new URLSearchParams(window.location.search);

  const bienvenue = document.createElement("section");
  bienvenue.className = "ecran card";
  bienvenue.id = "accueilDepart";
  bienvenue.innerHTML =
      '<div class="ecran-titre">Bienvenue, enquêteur·rice</div>'
    + '<p>Bienvenue au Parc Zoologique et Botanique de Mulhouse. Vous êtes sur le point de prendre part à une expérience unique en son genre : une enquête de police grandeur nature.</p>'
    + '<p>Armez-vous de bon sens et observez bien ce qu\'il se passe autour de vous. Suivez les consignes qui vous sont données et respectez le sens des énigmes qui vous est proposé.</p>'
    + '<p>Vous aurez 3 heures, à partir du moment où vous démarrez, pour terminer l\'enquête.</p>'
    + '<p class="muted">Merci de ne pas toucher aux décors : d\'autres enquêteurs passeront après vous.</p>'
    + blocPartenaires("Ce jeu vous est proposé par")
    + '<button id="versSaisieDepart">Suivant</button>';

  const saisie = document.createElement("section");
  saisie.className = "ecran card";
  saisie.id = "saisieDepart";
  saisie.hidden = true;
  saisie.innerHTML =
      '<p>Ces trois informations sont nécessaires pour démarrer :</p>'
    + '<label for="participantName">Nom de votre équipe</label>'
    + '<input type="text" id="participantName" maxlength="40" placeholder="Ex. Les Limiers du Dimanche">'
    + '<label for="nbJoueurs">Nombre de joueurs</label>'
    + '<input type="number" id="nbJoueurs" min="1" max="6" step="1" inputmode="numeric" placeholder="Entre 1 et 6">'
    + '<label for="codeInput">Le code de votre billet</label>'
    + '<input type="text" id="codeInput" maxlength="16" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="Ex. K7NPX4RT">'
    + '<div class="checkbox-row">'
    + '  <input type="checkbox" id="acceptRules">'
    + '  <label for="acceptRules" style="margin:0; text-transform:none; letter-spacing:0; font-size:0.9rem; color:var(--fog);">'
    + '    J\'accepte les consignes et je suis prêt·e à démarrer l\'enquête.</label>'
    + '</div>'
    + '<div class="error-box" id="errorBox"></div>'
    + '<button id="startBtn" disabled>Démarrer l\'enquête</button>'
    + '<p class="muted" id="ceQuiManque"></p>'
    + '<button class="btn-secondary" id="retourBienvenue">Revenir en arrière</button>';

  wrap.appendChild(bienvenue);
  wrap.appendChild(saisie);
  bienvenue.hidden = false;

  const nom = saisie.querySelector("#participantName");
  const nb = saisie.querySelector("#nbJoueurs");
  const code = saisie.querySelector("#codeInput");
  const accord = saisie.querySelector("#acceptRules");
  const bouton = saisie.querySelector("#startBtn");
  const manque = saisie.querySelector("#ceQuiManque");
  const erreur = saisie.querySelector("#errorBox");

  // Un code venu d'ailleurs (une borne du milieu, l'accueil) reste saisi.
  if (params.get("code")) code.value = params.get("code").trim().toUpperCase();

  bienvenue.querySelector("#versSaisieDepart").addEventListener("click", () => {
    bienvenue.hidden = true; saisie.hidden = false; window.scrollTo(0, 0);
  });
  saisie.querySelector("#retourBienvenue").addEventListener("click", () => {
    saisie.hidden = true; bienvenue.hidden = false; window.scrollTo(0, 0);
  });

  // Comme à l'accueil : on dit ce qui manque, tant qu'il manque quelque chose.
  function verifier() {
    const n = parseInt(nb.value, 10);
    const reste = [];
    if (!nom.value.trim())     reste.push("le nom de votre équipe");
    if (!(n >= 1 && n <= 6))   reste.push("le nombre de joueurs, de 1 à 6");
    if (!code.value.trim())    reste.push("votre code");
    if (!accord.checked)       reste.push("votre accord sur les consignes");
    bouton.disabled = reste.length > 0;
    manque.textContent = reste.length ? "Il reste à renseigner : " + reste.join(", ") + "." : "";
  }
  [nom, nb, code].forEach(c => c.addEventListener("input", verifier));
  accord.addEventListener("change", verifier);
  verifier();

  bouton.addEventListener("click", async () => {
    bouton.disabled = true;
    bouton.textContent = "Vérification...";
    erreur.classList.remove("visible");

    const result = await activateCode(code.value, nom.value, parseInt(nb.value, 10));
    if (!result.ok) {
      erreur.textContent = result.message;
      erreur.classList.add("visible");
      bouton.textContent = "Démarrer l'enquête";
      verifier();
      return;
    }

    // C'est le sens du billet qui commande. Le jour où les deux parcours ne
    // partiraient plus de la même borne, un billet de l'autre sens est
    // renvoyé à l'accueil, qui lui indique où aller.
    const sens = sensDuGroupe(result.session);
    if ((PARCOURS.ordre[sens] || {})[codeBorne] !== 1) {
      window.location.href = BASE_PATH + "index.html";
      return;
    }
    try { sessionStorage.setItem("sdb_conseil_depart", "1"); } catch (e) {}
    // La partie est ouverte : la borne redémarre, cette fois avec elle.
    window.location.href = window.location.pathname;
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
  // La vidéo d'un quiz est exclue : en plein écran elle recouvrirait les
  // questions, qui sont justement ce qu'on vient faire sur cette borne.
  document.querySelectorAll("video:not([data-quiz-video])").forEach(video => {
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

/**
 * LE JUGEMENT DES CONCLUSIONS.
 *
 * Le joueur écrit librement ce qui est arrivé à Isabelle, et le jeu
 * cherche dans sa phrase les idées attendues.
 *
 * La comparaison est volontairement indulgente. Un enfant de neuf ans qui
 * tape sur le téléphone de sa mère écrit « valeriane », « valérianne » ou
 * « la tizane » : on retire donc les accents, on passe tout en minuscules,
 * et on cherche des DÉBUTS de mots — « endorm » attrape endormie, endormi
 * et s'endormait. Trois heures d'enquête ne doivent pas se jouer sur un
 * accent.
 *
 * Les règles viennent du cahier, pas du code : les fins sont essayées de
 * haut en bas et la dernière sert de défaut, donc une conclusion
 * inattendue reçoit toujours une réponse.
 */
function sansAccent(t) {
  return String(t || "").toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function jugerLesConclusions(idChamp, idBouton, regles) {
  const champ = document.getElementById(idChamp);
  const bouton = document.getElementById(idBouton);
  const vides = document.getElementById("conclusionsVides");
  if (!champ || !bouton || !regles || !regles.length) return;

  /** Le texte contient-il l'une des façons de dire la même chose ? */
  function contient(texte, groupe) {
    return groupe.split("|").map(m => sansAccent(m).trim())
                 .filter(Boolean)
                 .some(m => texte.indexOf(m) !== -1);
  }
  function convient(texte, regle) {
    const attendus = (regle.attendus || "").split(";").filter(g => g.trim());
    const interdits = (regle.interdits || "").trim();
    if (interdits && contient(texte, interdits)) return false;
    return attendus.every(g => contient(texte, g));
  }

  bouton.addEventListener("click", () => {
    const brut = champ.value.trim();
    if (brut.length < 10) {           // deux mots jetés ne sont pas une enquête
      if (vides) vides.hidden = false;
      return;
    }
    if (vides) vides.hidden = true;
    const texte = sansAccent(brut);
    const fin = regles.find(r => convient(texte, r)) || regles[regles.length - 1];

    document.querySelectorAll("[data-denouement]").forEach(d => {
      d.hidden = (d.getAttribute("data-denouement") !== fin.nom);
    });
    champ.disabled = true;
    bouton.disabled = true;
    // On garde la trace de ce qu'ils ont écrit, mais JAMAIS au prix de la
    // fin du jeu : si la base ne répond pas, le dénouement s'affiche quand
    // même. C'est le moment où il faut le moins planter de toute l'enquête.
    try { enregistrerConclusions(brut, fin.nom); } catch (e) { }
  });
}

/**
 * LA QUESTION BONUS.
 *
 * Elle surgit sans QR code, au milieu du parcours. Une seule tentative :
 * qui répond juste du premier coup gagne un indice que les autres n'auront
 * pas. On ne bloque jamais — une mauvaise réponse coûte l'indice, pas la
 * suite du jeu.
 *
 * Les deux issues sont écrites d'avance dans la page. Le téléphone n'a donc
 * rien à demander à personne au moment de répondre, et la borne reste juste
 * même si le réseau du parc tombe entre-temps.
 *
 * Le bouton « Continuer » n'apparaît qu'après la réponse. Posé sous les
 * propositions dès l'arrivée, il inviterait à sauter la question, et donc à
 * perdre l'indice sans savoir qu'il existait.
 */
function brancherQuestionBonus() {
  document.querySelectorAll("[data-popquiz]").forEach(zone => {
    const bonne   = parseInt(zone.getAttribute("data-bonne"), 10);
    const gagne   = zone.querySelector("[data-bonus-gagne]");
    const rate    = zone.querySelector("[data-bonus-rate]");
    const suivant = zone.querySelector("[data-bonus-suivant]");
    const props   = Array.from(zone.querySelectorAll("[data-bonus-prop]"));
    if (!props.length || isNaN(bonne)) return;

    let repondu = false;
    props.forEach((bouton, n) => {
      bouton.addEventListener("click", () => {
        if (repondu) return;        // une seule tentative, c'est la règle
        repondu = true;
        props.forEach(b => { b.disabled = true; });
        bouton.classList.add("est-choisie", n === bonne ? "est-bonne" : "est-fausse");
        const issue = (n === bonne) ? gagne : rate;
        if (issue) issue.hidden = false;
        if (suivant) suivant.hidden = false;
      });
    });
  });
}

/**
 * LE QUIZ QUI SUIT UNE VIDÉO (la borne Sabri & Arez).
 *
 * La vidéo tourne en haut de l'écran, et les questions apparaissent en
 * dessous au fil des minutes. Le joueur répond pendant la lecture : c'est
 * tout l'intérêt, et c'est pour ça que cette vidéo reste dans la page au
 * lieu de partir en plein écran.
 *
 * Une question à la fois : la suivante remplace la précédente. Le groupe a
 * dix secondes pour répondre, après quoi la question se verrouille et
 * montre la bonne réponse — il perd le point, mais il apprend quand même.
 *
 * Trois décisions qui ne sautent pas aux yeux :
 *
 * 1. Tout le minutage vient du temps de la VIDÉO, jamais de l'horloge du
 *    téléphone. Sur le réseau d'un parc, une vidéo qui se recharge aurait
 *    sinon mangé les dix secondes sans que personne ait rien lu. Contrepartie
 *    assumée : un groupe qui met la vidéo en pause arrête aussi le chrono.
 *
 * 2. L'affichage est recalculé à chaque battement depuis ce temps, et jamais
 *    déclenché « une fois pour toutes ». Un joueur qui revient en arrière
 *    dans la vidéo retrouve donc l'écran cohérent, et une lecture qui saute
 *    ne perd aucune question au passage.
 *
 * 3. Le bouton « Suivant » attend la fin du quiz, SAUF si la vidéo refuse
 *    de se charger. Une vidéo muette ne doit jamais enfermer un groupe.
 */
function brancherQuizVideo() {
  const zone = document.querySelector("[data-quiz]");
  if (!zone) return;

  const ecran     = zone.closest(".ecran");
  const video     = ecran && ecran.querySelector("video");
  const questions = Array.from(zone.querySelectorAll("[data-question]"));
  const bilan     = zone.querySelector("[data-bilan]");
  const score     = bilan && bilan.querySelector("[data-score]");
  const suivant   = ecran && ecran.querySelector("[data-quiz-suivant]");
  if (!questions.length) return;

  const DELAI   = parseFloat(zone.getAttribute("data-delai")) || 10;
  const VERDICT = parseFloat(zone.getAttribute("data-verdict-delai")) || 0;
  const attente = zone.querySelector("[data-attente]");
  let justes = 0, repondues = 0, fini = false;

  const depart   = q => parseFloat(q.getAttribute("data-t"));
  const echeance = q => depart(q) + DELAI;
  const close    = q => q.hasAttribute("data-repondu") || q.hasAttribute("data-expiree");

  /** Bloque les propositions et souligne la bonne. */
  function verrouiller(q) {
    const bonne = parseInt(q.getAttribute("data-bonne"), 10);
    q.querySelectorAll(".quiz-prop").forEach((b, m) => {
      b.disabled = true;
      if (m === bonne) b.classList.add("est-bonne");
    });
    const chrono = q.querySelector("[data-chrono]");
    if (chrono) chrono.hidden = true;
  }

  function direVerdict(q, texte, classe) {
    const v = q.querySelector("[data-verdict]");
    if (!v) return;
    v.textContent = texte;
    v.className = "quiz-verdict " + classe;
    v.hidden = false;
  }

  // --- Répondre à une question ---------------------------------------
  questions.forEach(q => {
    const bonne = parseInt(q.getAttribute("data-bonne"), 10);
    q.querySelectorAll(".quiz-prop").forEach((bouton, n) => {
      bouton.addEventListener("click", () => {
        if (close(q)) return;            // une seule réponse, et pas après l'heure
        q.setAttribute("data-repondu", "");
        repondues++;
        verrouiller(q);
        bouton.classList.add("est-choisie");
        if (n === bonne) {
          justes++;
          direVerdict(q, "Bonne réponse.", "quiz-juste");
        } else {
          bouton.classList.add("est-fausse");
          direVerdict(q, "Ce n'était pas la bonne réponse.", "quiz-faux");
        }
        majScore();
        if (repondues === questions.length) finir();
      });
    });
  });

  /* Le compte à rebours d'une question, et sa fin.
     Rien n'est déclenché par un minuteur : on relit le temps de la vidéo et
     on en déduit l'état. Une vidéo qui se recharge fige donc le compte à
     rebours au lieu de le laisser filer dans le vide. */
  function majChrono(q, t) {
    const reste  = Math.max(0, echeance(q) - t);
    const chrono = q.querySelector("[data-chrono]");

    if (reste <= 0 && !close(q)) {
      q.setAttribute("data-expiree", "");
      verrouiller(q);
      // On nomme la bonne réponse plutôt que de la désigner : « elle est
      // soulignée » suppose qu'on repère un trait vert sur un téléphone en
      // plein jour, et la question disparaît dans quelques secondes.
      const bonne = q.querySelectorAll(".quiz-prop")[
                      parseInt(q.getAttribute("data-bonne"), 10)];
      direVerdict(q, "Temps écoulé. La bonne réponse était « "
                   + (bonne ? bonne.textContent : "") + " ».", "quiz-faux");
      return;
    }
    if (close(q) || !chrono) return;

    chrono.hidden = false;
    const barre = chrono.querySelector(".quiz-chrono-barre span");
    const texte = chrono.querySelector("[data-reste]");
    if (barre) barre.style.width = (reste / DELAI * 100) + "%";
    if (texte) texte.textContent = Math.ceil(reste) + " s";
    chrono.classList.toggle("quiz-chrono-urgent", reste <= 3);
  }

  // --- Dérouler les questions au rythme de la vidéo -------------------
  function majAffichage() {
    // Une fois le bilan tombé, la vidéo peut continuer à battre la mesure :
    // elle ne doit plus faire réapparaître de question derrière la lettre.
    if (fini) return;
    const t = video ? video.currentTime : 0;
    // La question en cours est la dernière que la vidéo ait atteinte. Les
    // autres disparaissent : c'est le parti pris du jeu, une question à la
    // fois, et tant pis pour qui n'a pas levé les yeux.
    let courante = null;
    questions.forEach(q => { if (t >= depart(q)) courante = q; });

    // Le délai écoulé, on laisse le verdict quelques secondes puis la
    // question s'efface : une question morte qui traîne quarante secondes
    // sous la vidéo détourne l'oreille de ce qu'il y a à entendre.
    if (courante) {
      majChrono(courante, t);
      // La question garde sa place pendant TOUT son compte à rebours, même
      // répondue à la troisième seconde. La vidéo affiche son propre chrono :
      // une question qui s'effacerait avant la fin de celui-ci donnerait
      // l'impression d'un bug. Le verdict reste quelques secondes de plus,
      // puis l'écran rend l'oreille au son.
      if (t >= echeance(courante) + VERDICT) courante = null;
    }
    questions.forEach(q => { q.hidden = (q !== courante); });
    if (attente) attente.hidden = !!courante;

    // Le bilan et la lettre attendent la FIN de la vidéo, pas la dernière
    // question : le témoignage continue souvent après elle, et la lettre
    // arrivait par-dessus. Seule exception, un groupe qui a répondu à tout
    // et dont la dernière question est passée depuis longtemps : il a fini
    // son travail, il n'est pas retenu si la vidéo s'arrête en route.
    const derniere = questions[questions.length - 1];
    if (repondues === questions.length && t >= echeance(derniere) + VERDICT) finir();
  }

  /* Le compte des bonnes réponses.

     Il se recalcule à chaque réponse, y compris APRÈS l'affichage du bilan.
     Sans cela, un groupe qui répond à la dernière question au moment où le
     bilan s'affiche voit son score figé : le jeu lui dit « bonne réponse »,
     et le total ne bouge pas. */
  function majScore() {
    if (!score) return;
    const n = questions.length;
    if (justes === n) {
      score.textContent = "Sans faute : " + justes + " bonnes réponses sur " + n + ".";
      return;
    }
    const pluriel = justes > 1 ? "s" : "";
    score.textContent = "Vous avez " + justes + " bonne" + pluriel
                      + " réponse" + pluriel + " sur " + n + ".";
  }

  function finir() {
    if (fini) return;
    fini = true;
    questions.forEach(q => {
      if (!close(q)) { q.setAttribute("data-expiree", ""); verrouiller(q); }
      q.hidden = true;
    });
    majScore();
    if (attente) attente.hidden = true;
    boutonFinal();
    if (bilan) {
      bilan.hidden = false;
      // La lettre est la récompense, et elle arrive sous le pli.
      try { bilan.scrollIntoView({ behavior: "smooth", block: "nearest" }); }
      catch (e) { }
    }
    libererSuivant();
  }

  function libererSuivant() {
    if (suivant) suivant.hidden = false;
  }

  // « Passer la vidéo » : demandé sur le terrain. La vidéo dure près de
  // quatre minutes, et un groupe pressé doit pouvoir avancer. Il perd les
  // points des questions qu'il saute, pas la lettre : elle est sur l'écran
  // d'après. Le même bouton devient « Suivant » une fois le quiz fini.
  if (suivant) {
    suivant.textContent = "Passer la vidéo";
    suivant.classList.add("btn-secondary");
    suivant.hidden = false;
  }
  function boutonFinal() {
    if (!suivant) return;
    suivant.textContent = "Suivant";
    suivant.classList.remove("btn-secondary");
    suivant.hidden = false;
  }

  /* Le quiz sans sa vidéo.
     Ce chemin-là n'est pas un cas d'école : tant que le fichier n'est pas
     chargé chez l'hébergeur, c'est le comportement normal de la borne. Et
     le jour du jeu, une vidéo qui ne descend pas sur le réseau d'un parc
     est l'incident le plus probable de tous. On montre alors la première
     question sans compte à rebours — il n'y a plus d'horloge pour le faire
     courir — et la sortie, plutôt que de laisser un groupe devant un
     rectangle noir avec un bouton « Suivant » invisible. */
  let filet = null;
  function ouvrirSansVideo() {
    zone.hidden = false;
    if (attente) attente.hidden = true;
    questions[0].hidden = false;
    const chrono = questions[0].querySelector("[data-chrono]");
    if (chrono) chrono.hidden = true;
    boutonFinal();
  }

  if (video) {
    // Si le fichier n'existe pas, le navigateur ne le signale pas sur la
    // vidéo mais sur la balise <source>, et cette erreur-là ne remonte pas :
    // d'où l'écoute en phase de capture, seule façon de l'entendre.
    ecran.addEventListener("error", e => {
      if (e.target && e.target.tagName === "SOURCE") ouvrirSansVideo();
    }, true);
    // Et il faut encore la provoquer : le navigateur a déjà cherché la vidéo
    // pendant la lecture de la page, bien avant que ce script existe, donc
    // cette erreur est passée sans témoin. load() refait la recherche, cette
    // fois devant nous. Avec preload="none", elle ne télécharge rien : elle
    // se contente de vérifier qu'il y a bien un fichier à aller chercher.
    try { video.load(); } catch (e) { }
    // Dernier filet, si rien ne se produit du tout — ni lecture, ni erreur.
    // Celui-ci ne montre PAS les questions : un groupe qui n'a pas encore
    // appuyé sur lecture ne doit pas voir le quiz démarrer sans lui. Il rend
    // seulement la sortie, pour que personne ne reste enfermé.
    filet = setTimeout(libererSuivant, 25000);

    // Le cadre d'attente est un 16/9 ; dès que les vraies dimensions sont
    // connues, la vidéo reprend sa forme exacte, sans bandes noires.
    video.addEventListener("loadedmetadata", () => {
      video.style.aspectRatio = "auto";
    }, { once: true });

    // Les questions n'apparaissent qu'à la lecture : avant d'appuyer sur
    // play, l'écran ne doit pas être un mur de questions sans contexte.
    video.addEventListener("play", () => {
      if (filet) { clearTimeout(filet); filet = null; }
      zone.hidden = false;
      majAffichage();
    });
    video.addEventListener("timeupdate", majAffichage);
    video.addEventListener("seeked", majAffichage);
    video.addEventListener("ended", finir);
    video.addEventListener("error", ouvrirSansVideo);
  } else {
    ouvrirSansVideo();
  }
}

/**
 * Le coup de pouce (l'enclos des loups) : une phrase d'aide derrière un
 * bouton. Elle oriente le regard, elle ne donne pas la réponse.
 */
function brancherCoupDePouce() {
  document.querySelectorAll("[data-coup-de-pouce]").forEach(zone => {
    const bouton = zone.querySelector("[data-coup-de-pouce-ouvrir]");
    const texte = zone.querySelector("[data-coup-de-pouce-texte]");
    if (!bouton || !texte) return;
    bouton.addEventListener("click", () => { bouton.hidden = true; texte.hidden = false; });
  });
}

/**
 * Le mot des quatre lettres, après la dernière. Juste : le dernier lieu est
 * révélé. Faux deux fois : on donne le mot, et le lieu quand même — à la
 * dernière étape, personne ne reste dehors. Le scanner n'apparaît qu'après.
 *
 * Indulgent : majuscules, accents et espaces ne comptent pas.
 */
function brancherMotFinal() {
  const zone = document.querySelector("[data-mot-final]");
  if (!zone) return;
  const attendu = sansAccent(zone.getAttribute("data-mot")).replace(/[^a-z]/g, "");
  const champ = zone.querySelector("#motFinal");
  const bouton = zone.querySelector("#validerMot");
  const faux = zone.querySelector("[data-mot-faux]");
  const trouve = zone.querySelector("[data-mot-trouve]");
  const ecran = zone.closest(".ecran");
  const apres = ecran && ecran.querySelector("[data-apres-mot]");
  if (!champ || !bouton || !trouve) return;

  let manques = 0;
  function reveler(texteFaux) {
    if (faux) {
      faux.hidden = !texteFaux;
      if (texteFaux) faux.textContent = texteFaux;
    }
    trouve.hidden = false;
    champ.disabled = true; bouton.disabled = true;
    if (apres) apres.hidden = false;
  }
  function valider() {
    const saisi = sansAccent(champ.value).replace(/[^a-z]/g, "");
    if (!saisi) return;
    if (saisi === attendu) { reveler(""); return; }
    manques++;
    champ.value = "";
    if (manques >= 2) {
      reveler("Le mot était " + zone.getAttribute("data-mot") + ".");
    } else if (faux) {
      faux.textContent = "Ce n'est pas ce mot. Essayez vos lettres dans un autre ordre.";
      faux.hidden = false;
    }
  }
  bouton.addEventListener("click", valider);
  champ.addEventListener("keydown", e => { if (e.key === "Enter") valider(); });
}

/**
 * Une épreuve à réponse vérifiée (le panneau d'empreintes).
 *
 * Une mauvaise réponse ne bloque plus. Au deuxième essai manqué, le jeu
 * donne le bon numéro et la lettre quand même : quatre personnes debout
 * devant un panneau un dimanche de novembre abandonnent avant de chercher
 * longtemps, et la lettre leur sera nécessaire pour finir l'enquête. On
 * perd la fierté d'avoir trouvé, pas la suite du jeu.
 */
function epreuveReponse(idChamp, idBouton, bonneReponse, idResultat, idACote) {
  const champ = document.getElementById(idChamp);
  const bouton = document.getElementById(idBouton);
  const resultat = document.getElementById(idResultat);
  const aCote = idACote ? document.getElementById(idACote) : null;
  const titre = document.getElementById("resultatTitre");
  if (!champ || !bouton || !resultat) return;

  let manques = 0;
  function reveler(trouve) {
    if (titre && !trouve) titre.textContent = "La réponse était le " + bonneReponse;
    resultat.hidden = false;
    champ.disabled = true;
    bouton.disabled = true;
  }

  bouton.addEventListener("click", () => {
    const saisi = champ.value.trim().toLowerCase();
    if (saisi === String(bonneReponse).toLowerCase()) {
      if (aCote) aCote.hidden = true;
      reveler(true);
      return;
    }
    manques++;
    champ.setAttribute("aria-invalid", "true");
    champ.value = "";
    if (manques >= 2) {
      if (aCote) {
        aCote.textContent = "Ce n'était pas le bon numéro. Le voici tout de même.";
        aCote.hidden = false;
      }
      reveler(false);
    } else if (aCote) {
      aCote.textContent = "Ce n'est pas le bon numéro. Regardez mieux le panneau.";
      aCote.hidden = false;
    }
  });
}

/**
 * Les photos qu'on fait défiler sur place (le contenu du sac perdu).
 *
 * Rien ne se télécharge avant le clic sur « Voir » : sur le réseau d'un
 * parc, cinq photos qui partent toutes seules à l'ouverture de la borne,
 * c'est l'écran qui reste blanc pendant que le groupe attend.
 */
function galeriePhotos() {
  document.querySelectorAll("[data-galerie]").forEach(zone => {
    const ouvrir = zone.querySelector("[data-galerie-ouvrir]");
    const vue    = zone.querySelector("[data-galerie-vue]");
    const photos = Array.from(zone.querySelectorAll("[data-galerie-photo]"));
    const compte = zone.querySelector("[data-galerie-compte]");
    const prec   = zone.querySelector("[data-galerie-prec]");
    const suiv   = zone.querySelector("[data-galerie-suiv]");
    if (!photos.length || !vue) return;

    let n = 0;
    function montrer(i) {
      n = Math.max(0, Math.min(i, photos.length - 1));
      photos.forEach((p, k) => { p.hidden = (k !== n); });
      if (compte) compte.textContent = (n + 1) + " / " + photos.length;
      if (prec) prec.disabled = (n === 0);
      if (suiv) suiv.disabled = (n === photos.length - 1);
    }
    if (ouvrir) ouvrir.addEventListener("click", () => {
      ouvrir.hidden = true; vue.hidden = false; montrer(0);
    });
    if (prec) prec.addEventListener("click", () => montrer(n - 1));
    if (suiv) suiv.addEventListener("click", () => montrer(n + 1));
    montrer(0);
  });
}

/**
 * Le nombre à reconstituer depuis les objets du sac.
 *
 * On ne dit pas à quoi il sert : le joueur note quatre chiffres sans
 * savoir, et c'est ce silence qui fait l'effet trois bornes plus loin.
 * Au deuxième essai manqué, on le donne — il est indispensable à la suite.
 */
function codeATrouver(idChamp, idBouton, bonCode, idJuste, idACote) {
  const champ = document.getElementById(idChamp);
  const bouton = document.getElementById(idBouton);
  const juste = document.getElementById(idJuste);
  const aCote = document.getElementById(idACote);
  if (!champ || !bouton || !juste) return;

  let manques = 0;
  bouton.addEventListener("click", () => {
    if (champ.value.trim() === String(bonCode)) {
      if (aCote) aCote.hidden = true;
      juste.hidden = false; champ.disabled = true; bouton.disabled = true;
      return;
    }
    manques++;
    champ.value = "";
    if (manques >= 2) {
      if (aCote) {
        aCote.textContent = "Ce n'était pas cela. Le voici, notez-le.";
        aCote.hidden = false;
      }
      juste.hidden = false; champ.disabled = true; bouton.disabled = true;
    } else if (aCote) {
      aCote.textContent = "Ce n'est pas cela. Les objets portaient des chiffres : "
                        + "relisez-les dans l'ordre où vous les avez vus.";
      aCote.hidden = false;
    }
  });
}

/**
 * La porte à code (la serre).
 *
 * « J'ai perdu le code » existe parce qu'un papier s'envole, qu'un
 * téléphone se verrouille et qu'on ne laisse personne dehors à la
 * dernière étape de trois heures d'enquête.
 */
function porteACode(idChamp, idBouton, bonCode, idOuverte, idACote, idPerdu) {
  const champ = document.getElementById(idChamp);
  const bouton = document.getElementById(idBouton);
  const ouverte = document.getElementById(idOuverte);
  const aCote = document.getElementById(idACote);
  const perdu = idPerdu ? document.getElementById(idPerdu) : null;
  if (!champ || !bouton || !ouverte) return;

  function ouvrir() {
    ouverte.hidden = false;
    champ.disabled = true; bouton.disabled = true;
    if (perdu) perdu.hidden = true;
  }
  bouton.addEventListener("click", () => {
    if (champ.value.trim() === String(bonCode)) {
      if (aCote) aCote.hidden = true;
      ouvrir();
    } else if (aCote) {
      champ.value = "";
      aCote.textContent = "Ce code n'ouvre pas la porte.";
      aCote.hidden = false;
    }
  });
  if (perdu) perdu.addEventListener("click", () => {
    if (aCote) {
      aCote.className = "quiz-verdict";
      aCote.textContent = "Le code est le " + bonCode + ".";
      aCote.hidden = false;
    }
    champ.value = String(bonCode);
    ouvrir();
  });
}

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