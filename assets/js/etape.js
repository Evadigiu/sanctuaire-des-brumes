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
  const session = requireActiveSession();
  if (!session) return;

  startCountdown("timer");

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

  // 2. Le numéro d'étape et le lien de sortie dépendent du sens.
  const pos = document.querySelector("#position");
  if (pos) pos.textContent = pos.getAttribute("data-" + sens) || "";

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

  function afficher(i) {
    courant = i;
    try { sessionStorage.setItem(CLE, String(i)); } catch (e) {}
    ecrans.forEach((el, n) => { el.hidden = (n !== i); });
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
  document.querySelectorAll("[data-retour]").forEach(b => {
    b.addEventListener("click", () => {
      if (courant > 0) afficher(courant - 1);
    });
  });

  afficher(courant);
  brancherSecours();
}

// ------------------------------------------------------------
// Épreuve à réponse vérifiée (le panneau d'empreintes).
// La lettre n'apparaît que si la réponse est la bonne.
// ------------------------------------------------------------
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
    window.location.href = PARCOURS.pages[cible];
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

function brancherSecours() {
  const b1 = document.getElementById("boutonSecours");
  const b2 = document.getElementById("boutonProbleme");
  if (b1) b1.addEventListener("click", ouvrirSecours);
  if (b2) b2.addEventListener("click", ouvrirProbleme);
}
