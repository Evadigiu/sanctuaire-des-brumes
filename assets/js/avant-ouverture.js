// ============================================================
// AVANT L'OUVERTURE — Le Sanctuaire des Brumes
//
// Les affichettes sont posées dans le parc avant le premier jour de jeu.
// Un visiteur curieux qui scanne un QR code tombe sur une borne qui lui
// demande un code qu'il n'a pas, et chaque scan laissait une fausse alerte
// « partie introuvable » dans le tableau de bord.
//
// Jusqu'à l'ouverture, toutes les pages du jeu se couvrent donc d'une
// fenêtre qui renvoie vers la billetterie. Elle ne se ferme pas : derrière,
// il n'y a rien que le visiteur puisse faire avant samedi.
//
// Elle disparaît d'elle-même à l'heure d'ouverture, sans mise en ligne.
// Ce fichier peut être retiré après coup, mais rien ne presse : passé
// cette date, il ne fait plus rien.
//
// L'équipe garde la main par un passe, posé dans le navigateur :
//   - en ouvrant une fois https://enquete.pomelolab.fr/?equipe
//   - ou par le lien discret « Accès équipe » de la fenêtre, avec le mot
//     de passe de l'équipe, quand un scan à l'appareil photo a ouvert une
//     fenêtre qui ne connaît pas le passe.
// Le dépôt est public, ce passe n'a rien d'un secret : il ne fait que
// lever la fenêtre, il faut encore un vrai code pour jouer.
// ============================================================

// Samedi 17 octobre 2026, minuit, heure de Paris (heure d'été, UTC+2).
const OUVERTURE_DU_JEU = new Date("2026-10-17T00:00:00+02:00");
const BILLETTERIE = "https://www.pomelolab.fr/sanctuairedesbrumes";
const PASSE_EQUIPE_KEY = "sdb_passe_equipe";
const MOT_DE_PASSE_EQUIPE = "brumes2026";

function aLePasseEquipe() {
  try { return localStorage.getItem(PASSE_EQUIPE_KEY) === "1"; } catch (e) { return false; }
}

function poserLePasseEquipe() {
  try { localStorage.setItem(PASSE_EQUIPE_KEY, "1"); return true; } catch (e) { return false; }
}

/**
 * Vrai tant que le jeu n'est pas ouvert pour ce visiteur. Les pages s'en
 * servent pour ne rien faire (ni scan, ni signalement) sous la fenêtre.
 */
function avantOuverture() {
  if (new Date() >= OUVERTURE_DU_JEU) return false;
  // Les tests automatiques tournent sur la machine elle-même.
  if (["localhost", "127.0.0.1", ""].indexOf(window.location.hostname) !== -1) return false;
  return !aLePasseEquipe();
}

(function () {
  // Le passe s'emporte dans l'adresse : ?equipe
  if (new URLSearchParams(window.location.search).has("equipe")) poserLePasseEquipe();
  if (!avantOuverture()) return;

  const fond = document.createElement("div");
  fond.className = "avant-ouverture";
  fond.setAttribute("role", "dialog");
  fond.setAttribute("aria-modal", "true");
  fond.setAttribute("aria-labelledby", "avantOuvertureTitre");
  fond.innerHTML =
      '<div class="card">'
    + '  <div class="eyebrow">Le Sanctuaire des Brumes</div>'
    + '  <h1 id="avantOuvertureTitre">Patience, enquêteur·rice</h1>'
    + '  <p>Ce jeu ne démarre que le <strong>samedi 17 octobre</strong>.</p>'
    + '  <p>Prenez vos billets ici :</p>'
    + '  <a class="btn" href="' + BILLETTERIE + '">Prendre mes billets</a>'
    + '  <div class="avant-ouverture-equipe">'
    + '    <button type="button" class="btn-lien" id="accesEquipe">Accès équipe</button>'
    + '    <div id="zoneEquipe" hidden>'
    + '      <input type="text" id="motEquipe" autocomplete="off" autocapitalize="none"'
    + '             placeholder="Mot de passe de l\'équipe" aria-label="Mot de passe de l\'équipe">'
    + '      <div class="error-box visible" id="erreurEquipe" hidden>Ce n\'est pas le bon mot de passe.</div>'
    + '      <button type="button" class="btn-secondary" id="validerEquipe">Entrer</button>'
    + '    </div>'
    + '  </div>'
    + '</div>';

  // Rien sous la fenêtre ne doit se cliquer ni se lire au lecteur d'écran.
  Array.from(document.body.children).forEach(el => el.setAttribute("inert", ""));
  document.body.appendChild(fond);
  document.body.classList.add("sous-fenetre");

  const zone = fond.querySelector("#zoneEquipe");
  const champ = fond.querySelector("#motEquipe");
  const erreur = fond.querySelector("#erreurEquipe");

  fond.querySelector("#accesEquipe").addEventListener("click", () => {
    zone.hidden = false;
    champ.focus();
  });

  function valider() {
    if (champ.value.trim().toLowerCase() !== MOT_DE_PASSE_EQUIPE) {
      erreur.hidden = false;
      return;
    }
    poserLePasseEquipe();
    // On recharge : la page démarre alors comme si la fenêtre n'avait
    // jamais existé, avec sa partie, son chrono et son scan.
    window.location.reload();
  }
  fond.querySelector("#validerEquipe").addEventListener("click", valider);
  champ.addEventListener("keydown", e => { if (e.key === "Enter") valider(); });
})();
