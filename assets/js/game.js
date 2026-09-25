// ============================================================
// LOGIQUE DE JEU — Le Sanctuaire des Brumes
// Utilisé par index.html (activation) et toutes les pages /etapes/
// Dépend de supabase-client.js, chargé avant ce fichier.
// ============================================================

const SESSION_KEY = "sdb_session";

// Chemin vers la racine du site. Chaque page de borne le déclare elle-même
// (data-racine sur <body>), parce qu'il ne se devine plus depuis l'adresse :
// les bornes vivent dans des dossiers numériques (/1868/) dont le nom ne suit
// aucune règle reconnaissable. La page d'accueil, elle, est déjà à la racine.
const BASE_PATH = document.body.getAttribute("data-racine") || "";

/**
 * Tente d'activer un code au point de départ.
 * Retourne { ok: true, session } ou { ok: false, message }
 *
 * Le site ne touche plus à la table des codes : elle est fermée. Il passe
 * par le guichet activer_code(), une fonction de la base qui vérifie le
 * code et ouvre elle-même la partie. Trois conséquences :
 *   - la liste des codes n'est plus lisible depuis un téléphone ;
 *   - le chrono de 3h est calculé par la base, pas par l'horloge du joueur ;
 *   - c'est la base qui rédige le message de refus, affiché tel quel.
 */
async function activateCode(code, participantName, nbJoueurs) {
  const { data, error } = await supabaseClient.rpc("activer_code", {
    p_code: code,
    p_nb_joueurs: nbJoueurs || null,
  });

  if (error) {
    console.warn("Guichet injoignable :", error.message);
    return { ok: false, message: "Erreur de connexion, réessaie dans un instant." };
  }
  if (!data || !data.ok) {
    return {
      ok: false,
      message: (data && data.message)
        || "Ce code n'a pas pu être activé. Adresse-toi à l'accueil du zoo.",
    };
  }

  const session = {
    codeId: data.code_id,
    code: data.code,
    direction: data.direction,
    expiresAt: data.expires_at,
    participantName: participantName || "",
    nbJoueurs: nbJoueurs || null,
  };
  saveSession(session);
  return { ok: true, session };
}

function saveSession(session) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function getSession() {
  const raw = localStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw); } catch { return null; }
}

/**
 * À appeler en haut de chaque page d'étape.
 * Vérifie qu'une session existe et n'est pas expirée.
 * Redirige vers l'accueil si ce n'est pas le cas.
 */
function requireActiveSession() {
  const session = getSession();
  if (!session) {
    window.location.href = BASE_PATH + "index.html?error=no_session";
    return null;
  }
  if (new Date(session.expiresAt) < new Date()) {
    window.location.href = BASE_PATH + "index.html?error=expired";
    return null;
  }
  return session;
}

/**
 * Enregistre le passage à une borne, par le guichet.
 *
 * La table des passages n'accepte plus d'écriture directe : sans cela, un
 * joueur pouvait s'inscrire d'un coup les seize bornes et déverrouiller
 * tout le parcours sans marcher.
 *
 * Le guichet répond aussi quand le libellé de la borne ne correspond à
 * rien en base. Avant, ce cas-là passait inaperçu et le passage était
 * simplement perdu : c'est la panne qu'on ne voyait qu'au dépouillement.
 */
async function logScan(qrLabel) {
  const session = getSession();
  if (!session) return;

  const { data, error } = await supabaseClient.rpc("enregistrer_passage", {
    p_code_id: session.codeId,
    p_borne: qrLabel,
  });

  if (error) {
    console.warn("Passage non enregistré :", error.message);
    return;
  }
  if (!data || !data.ok) {
    console.warn("Passage refusé :", (data && data.message) || "raison inconnue");
  }
}

/**
 * Affiche un chrono décompte dans l'élément donné, à partir de la
 * date d'expiration de la session. Redirige en fin de temps.
 */
function startCountdown(elementId) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const session = getSession();
  if (!session) return;

  function tick() {
    const remainingMs = new Date(session.expiresAt) - new Date();
    if (remainingMs <= 0) {
      el.textContent = "Temps écoulé";
      clearInterval(interval);
      setTimeout(() => { window.location.href = BASE_PATH + "index.html?error=expired"; }, 2000);
      return;
    }
    const totalSec = Math.floor(remainingMs / 1000);
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = totalSec % 60;
    el.textContent = `${h}h ${String(m).padStart(2, "0")}min ${String(s).padStart(2, "0")}s restantes`;
  }

  tick();
  const interval = setInterval(tick, 1000);
}

// ============================================================
// PROGRESSION DANS LE PARCOURS
//
// Le jeu consiste à trouver les bornes dans le parc. On refuse donc une
// borne trop en avance sur ce que le groupe a réellement scanné : sans
// cela, il suffirait de deviner une adresse pour sauter la moitié de
// l'enquête.
//
// La base fait foi, mais le téléphone garde une trace locale de ce qu'il
// a visité. Si la base est momentanément injoignable, c'est cette trace
// qui décide, plutôt que de bloquer un groupe au milieu du parc. Un
// tricheur devrait fabriquer cette trace à la main, ce qui est autrement
// plus difficile que de taper une adresse dans la barre du navigateur.
// ============================================================

const VISITES_KEY = "sdb_visites";

function visitesLocales() {
  try { return JSON.parse(localStorage.getItem(VISITES_KEY)) || []; }
  catch { return []; }
}

function noterVisiteLocale(codeEtape) {
  const v = visitesLocales();
  if (!v.includes(codeEtape)) {
    v.push(codeEtape);
    try { localStorage.setItem(VISITES_KEY, JSON.stringify(v)); } catch (e) {}
  }
}

/** Le sens du groupe, "A" ou "B". */
function sensDuGroupe(session) {
  return (session && session.direction === "antihoraire") ? "B" : "A";
}

/**
 * La borne demandée est-elle accessible au groupe ?
 * On autorise toute borne déjà visitée (relire un témoignage) et la
 * suivante attendue. Au-delà, c'est un saut : on refuse.
 */
async function progressionAutorise(codeEtape) {
  const session = getSession();
  if (!session) return { ok: false, raison: "pas de partie en cours" };

  const sens = sensDuGroupe(session);
  const positions = PARCOURS.ordre[sens];
  const position = positions[codeEtape];

  if (position === undefined) {
    // Borne de l'autre sens : la page l'explique elle-même, on laisse passer.
    return { ok: true };
  }
  if (position <= 1) return { ok: true };   // le départ est toujours ouvert

  let visites = null;
  const { data, error } = await supabaseClient
    .from("scans")
    .select("qr_points(label)")
    .eq("code_id", session.codeId);

  if (!error && data) {
    const labels = data.map(s => s.qr_points && s.qr_points.label).filter(Boolean);
    visites = Object.keys(PARCOURS.noms).filter(c => labels.includes(PARCOURS.noms[c]));
  } else {
    visites = visitesLocales();       // repli : la trace du téléphone
  }

  const atteinte = visites.reduce(
    (max, c) => Math.max(max, positions[c] || 0), 0);

  if (position <= atteinte + 1) return { ok: true };
  return {
    ok: false,
    raison: "saut",
    attendue: atteinte + 1,
    demandee: position,
  };
}
