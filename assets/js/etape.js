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
