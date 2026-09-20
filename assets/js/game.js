// ============================================================
// LOGIQUE DE JEU — Le Sanctuaire des Brumes
// Utilisé par index.html (activation) et toutes les pages /etapes/
// Dépend de supabase-client.js, chargé avant ce fichier.
// ============================================================

const SESSION_KEY = "sdb_session";

// Calcule le chemin vers la racine du site, que ce fichier soit appelé
// depuis index.html (racine) ou depuis une page dans /etapes/.
// Évite d'avoir à coder en dur l'adresse du site (github.io/nom-du-depot/,
// puis plus tard un nom de domaine personnalisé).
const BASE_PATH = window.location.pathname.includes("/etapes/") ? "../" : "";

/**
 * Tente d'activer un code au point de départ.
 * Retourne { ok: true, session } ou { ok: false, message }
 */
async function activateCode(code, participantName, nbJoueurs) {
  const cleanCode = code.trim().toUpperCase();

  const { data: existing, error: fetchError } = await supabaseClient
    .from("codes")
    .select("*")
    .eq("code", cleanCode)
    .maybeSingle();

  if (fetchError) {
    return { ok: false, message: "Erreur de connexion, réessaie dans un instant." };
  }
  if (!existing) {
    return { ok: false, message: "Ce code n'existe pas. Vérifie la saisie ou demande à l'accueil." };
  }
  if (existing.status === "expired") {
    return { ok: false, message: "Ce code a expiré. Adresse-toi à l'accueil du zoo." };
  }
  if (existing.status === "active") {
    // Un code déjà activé dont les 3h sont écoulées ne doit pas rouvrir une
    // partie : on laisserait le joueur entrer pour l'éjecter à l'écran
    // suivant, sans qu'il comprenne pourquoi. On refuse ici, clairement.
    if (existing.expires_at && new Date(existing.expires_at) <= new Date()) {
      return { ok: false, message: "Ce code a déjà servi et sa partie est terminée. Adresse-toi à l'accueil du zoo." };
    }
    // Sinon on relance la partie en cours plutôt que de refuser : utile si le
    // joueur recharge la page ou change de téléphone dans le groupe.
    const session = buildSession(existing, participantName, nbJoueurs);
    saveSession(session);
    return { ok: true, session };
  }

  // status === "unused" : première activation
  const activatedAt = new Date();
  const expiresAt = new Date(activatedAt.getTime() + 3 * 60 * 60 * 1000); // +3h

  const base = {
    status: "active",
    activated_at: activatedAt.toISOString(),
    expires_at: expiresAt.toISOString(),
  };

  function activer(champs) {
    return supabaseClient
      .from("codes")
      .update(champs)
      .eq("id", existing.id)
      .eq("status", "unused") // garde-fou anti double-activation simultanée
      .select()
      .maybeSingle();
  }

  // On tente d'enregistrer aussi le nombre réel de joueurs. Si la colonne
  // n'existe pas encore dans cette base, la requête entière est refusée et
  // rien n'est modifié : on réessaie alors sans ce champ.
  //
  // Le nombre de joueurs est un confort ; démarrer la partie ne l'est pas.
  // Un groupe qui attend à la caisse ne doit jamais rester bloqué à cause
  // d'une colonne manquante.
  let updated = null, updateError = null;
  if (nbJoueurs) {
    ({ data: updated, error: updateError } =
      await activer(Object.assign({ participants_reels: nbJoueurs }, base)));
    if (updateError) {
      console.warn("Nombre de joueurs non enregistré :", updateError.message);
      ({ data: updated, error: updateError } = await activer(base));
    }
  } else {
    ({ data: updated, error: updateError } = await activer(base));
  }

  if (updateError || !updated) {
    return { ok: false, message: "Ce code vient d'être activé ailleurs. Réessaie ou demande un nouveau code." };
  }

  const session = buildSession(updated, participantName, nbJoueurs);
  saveSession(session);
  return { ok: true, session };
}

function buildSession(codeRow, participantName, nbJoueurs) {
  return {
    codeId: codeRow.id,
    code: codeRow.code,
    direction: codeRow.direction,
    expiresAt: codeRow.expires_at,
    participantName: participantName || "",
    nbJoueurs: nbJoueurs || null,
  };
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
 * Enregistre le passage à une borne (table scans), en retrouvant
 * le point QR par son label dans la table qr_points.
 */
async function logScan(qrLabel) {
  const session = getSession();
  if (!session) return;

  const { data: point } = await supabaseClient
    .from("qr_points")
    .select("id")
    .eq("label", qrLabel)
    .maybeSingle();

  if (!point) {
    console.warn("Point QR introuvable en base :", qrLabel);
    return;
  }

  await supabaseClient.from("scans").insert({
    code_id: session.codeId,
    qr_point_id: point.id,
  });
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
