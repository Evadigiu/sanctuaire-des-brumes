// ============================================================
// LE SCANNER INTÉGRÉ — Le Sanctuaire des Brumes
//
// Pourquoi scanner depuis le site plutôt qu'avec l'appareil photo :
// la partie en cours est rangée dans la mémoire du navigateur. Or le
// lecteur de QR du centre de contrôle de l'iPhone, Google Lens ou
// l'appareil photo de certains Android ouvrent la page dans une fenêtre
// à part, dont la mémoire est vide. La borne ne trouve alors plus la
// partie, et le groupe doit ressaisir son code, parfois à chaque borne.
//
// Lu depuis la page, le QR code ouvre la borne suivante dans le MÊME
// navigateur : la partie suit, quel que soit le téléphone.
//
// Les QR imprimés ne changent pas. Un joueur qui les scanne quand même
// avec son appareil photo tombe, au pire, sur l'écran de reprise.
//
// Deux moteurs de lecture : celui du téléphone quand il en a un
// (BarcodeDetector, la plupart des Android), sinon jsQR, hébergé sur le
// site (assets/js/vendor/), chargé seulement à l'ouverture du scanner.
// L'iPhone passe toujours par jsQR.
//
// Dépend de parcours.js (PARCOURS) et de game.js (BASE_PATH).
// ============================================================

// Les QR des bornes encodent https://enquete.pomelolab.fr/1965/ : le
// dossier est aussi le nombre de secours de l'affichette. On accepte le
// domaine du site, et celui où l'on se trouve (essais en local).
const DOMAINES_DES_BORNES = ["enquete.pomelolab.fr"];

let scannerOuvert = null;

function brancherScanner() {
  document.querySelectorAll("[data-scanner]").forEach(b => {
    b.addEventListener("click", ouvrirScanner);
  });
}

/**
 * Le QR lu est-il une borne de l'enquête ? Rend l'adresse de la page à
 * ouvrir, ou null. Un nombre de secours seul (4 chiffres) est accepté.
 */
function borneDepuisQR(texte) {
  const t = (texte || "").trim();
  let dossier = null;
  if (/^\d{4}$/.test(t)) {
    dossier = t;
  } else {
    let url;
    try { url = new URL(t, window.location.href); } catch (e) { return null; }
    const domaines = DOMAINES_DES_BORNES.concat([window.location.hostname]);
    if (domaines.indexOf(url.hostname) === -1) return null;
    const m = url.pathname.match(/(?:^|\/)(\d{4})(?:\/|\/index\.html)?$/);
    if (m) dossier = m[1];
  }
  const code = dossier && PARCOURS.secours[dossier];
  return code ? BASE_PATH + PARCOURS.pages[code] : null;
}

function chargerJsQR() {
  if (window.jsQR) return Promise.resolve(window.jsQR);
  return new Promise((ok, ko) => {
    const s = document.createElement("script");
    s.src = BASE_PATH + "assets/js/vendor/jsQR.min.js";
    s.onload = () => window.jsQR ? ok(window.jsQR) : ko(new Error("jsQR absent"));
    s.onerror = () => ko(new Error("jsQR injoignable"));
    document.head.appendChild(s);
  });
}

/** Le moteur de lecture : une fonction (vidéo) → texte du QR ou null. */
async function preparerLecteur() {
  if ("BarcodeDetector" in window) {
    try {
      const formats = await window.BarcodeDetector.getSupportedFormats();
      if (formats.indexOf("qr_code") !== -1) {
        const detecteur = new window.BarcodeDetector({ formats: ["qr_code"] });
        return async video => {
          const trouves = await detecteur.detect(video);
          return trouves.length ? trouves[0].rawValue : null;
        };
      }
    } catch (e) { /* on se rabat sur jsQR */ }
  }

  const jsQR = await chargerJsQR();
  const toile = document.createElement("canvas");
  const ctx = toile.getContext("2d", { willReadFrequently: true });
  return async video => {
    const w = video.videoWidth, h = video.videoHeight;
    if (!w || !h) return null;
    // Une image réduite suffit pour un QR qui remplit le cadre, et garde
    // la lecture fluide sur un téléphone d'entrée de gamme.
    const echelle = Math.min(1, 640 / Math.max(w, h));
    toile.width = Math.round(w * echelle);
    toile.height = Math.round(h * echelle);
    ctx.drawImage(video, 0, 0, toile.width, toile.height);
    const img = ctx.getImageData(0, 0, toile.width, toile.height);
    const r = jsQR(img.data, img.width, img.height, { inversionAttempts: "dontInvert" });
    return r ? r.data : null;
  };
}

function ouvrirScanner() {
  if (scannerOuvert) return;

  const fond = document.createElement("div");
  fond.className = "scanner";
  fond.setAttribute("role", "dialog");
  fond.setAttribute("aria-label", "Scanner le QR code de la borne");
  fond.innerHTML =
      '<div class="scanner-cadre">'
    + '  <video playsinline muted autoplay></video>'
    + '  <div class="scanner-viseur" aria-hidden="true"></div>'
    + '</div>'
    + '<p class="scanner-consigne" id="scannerConsigne">Visez le QR code de la borne.</p>'
    + '<div class="error-box visible" id="scannerErreur" hidden></div>'
    + '<button class="btn-secondary" id="scannerFermer">Annuler</button>'
    + '<button class="btn-lien" id="scannerSecours">Le QR code ne se lit pas ? Saisir le nombre à 4 chiffres</button>';
  document.body.appendChild(fond);

  const video = fond.querySelector("video");
  const consigne = fond.querySelector("#scannerConsigne");
  const erreur = fond.querySelector("#scannerErreur");
  let flux = null, actif = true, minuteur = null, dernierRefus = 0;

  function fermer() {
    actif = false;
    clearTimeout(minuteur);
    if (flux) flux.getTracks().forEach(t => t.stop());
    fond.remove();
    document.removeEventListener("visibilitychange", surVisibilite);
    scannerOuvert = null;
  }
  // Téléphone verrouillé ou onglet quitté : on rend la caméra.
  function surVisibilite() { if (document.hidden) fermer(); }
  document.addEventListener("visibilitychange", surVisibilite);
  scannerOuvert = { fermer };

  function direErreur(texte) {
    erreur.textContent = texte;
    erreur.hidden = false;
  }

  fond.querySelector("#scannerFermer").addEventListener("click", fermer);
  fond.querySelector("#scannerSecours").addEventListener("click", () => {
    fermer();
    if (typeof ouvrirSecours === "function" && document.getElementById("zoneSecours")) {
      const zone = document.getElementById("secoursDepart");
      if (zone) zone.hidden = false;
      ouvrirSecours();
      document.getElementById("zoneSecours").scrollIntoView({ behavior: "smooth", block: "center" });
    }
  });

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    consigne.hidden = true;
    direErreur("Ce navigateur ne donne pas accès à la caméra. Scannez le QR code avec "
             + "l'appareil photo de votre téléphone, ou saisissez le nombre à 4 chiffres de l'affichette.");
    return;
  }

  const lecteurPret = preparerLecteur();
  navigator.mediaDevices.getUserMedia({
    video: { facingMode: { ideal: "environment" } },
    audio: false,
  }).then(async f => {
    if (!actif) { f.getTracks().forEach(t => t.stop()); return; }
    flux = f;
    video.srcObject = f;
    try { await video.play(); } catch (e) {}

    let lire;
    try { lire = await lecteurPret; } catch (e) {
      consigne.hidden = true;
      direErreur("Le scanner n'a pas pu se charger. Vérifiez votre connexion, ou saisissez "
               + "le nombre à 4 chiffres de l'affichette.");
      return;
    }

    async function tour() {
      if (!actif) return;
      let texte = null;
      try { texte = await lire(video); } catch (e) {}
      if (!actif) return;
      if (texte) {
        const cible = borneDepuisQR(texte);
        if (cible) {
          if (navigator.vibrate) navigator.vibrate(60);
          consigne.textContent = "Borne trouvée, ouverture...";
          erreur.hidden = true;
          fermer();
          window.location.href = cible;
          return;
        }
        // Un autre QR du zoo (un panneau, une affiche) : on le dit, sans
        // couper la caméra, et sans répéter le message à chaque image.
        if (Date.now() - dernierRefus > 2500) {
          dernierRefus = Date.now();
          direErreur("Ce QR code n'appartient pas à l'enquête. Visez celui de la borne.");
        }
      }
      minuteur = setTimeout(tour, 150);
    }
    tour();
  }).catch(err => {
    if (!actif) return;
    consigne.hidden = true;
    const refus = err && (err.name === "NotAllowedError" || err.name === "SecurityError");
    direErreur(refus
      ? "L'accès à la caméra a été refusé. Autorisez-le dans les réglages du navigateur pour ce site, "
        + "ou saisissez le nombre à 4 chiffres de l'affichette."
      : "La caméra ne répond pas. Fermez les autres applications qui l'utilisent, ou saisissez "
        + "le nombre à 4 chiffres de l'affichette.");
  });
}

// Chargé en fin de page, après les écrans : les boutons existent déjà.
brancherScanner();
