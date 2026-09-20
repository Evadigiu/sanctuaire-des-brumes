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
