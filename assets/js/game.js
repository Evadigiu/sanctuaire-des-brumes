// ============================================================
// LOGIQUE DE JEU — Le Sanctuaire des Brumes
// Utilisé par index.html (activation) et toutes les pages /etapes/
// Dépend de supabase-client.js, chargé avant ce fichier.
// ============================================================

const SESSION_KEY = "sdb_session";

/**
 * Tente d'activer un code au point de départ.
 * Retourne { ok: true, session } ou { ok: false, message }
 */
async function activateCode(code, participantName) {
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
    // Code déjà activé : on relance la session existante plutôt que de refuser,
    // utile si le joueur recharge la page ou change de téléphone dans le groupe.
    const session = buildSession(existing, participantName);
    saveSession(session);
    return { ok: true, session };
  }

  // status === "unused" : première activation
  const activatedAt = new Date();
  const expiresAt = new Date(activatedAt.getTime() + 3 * 60 * 60 * 1000); // +3h

  const { data: updated, error: updateError } = await supabaseClient
    .from("codes")
    .update({ status: "active", activated_at: activatedAt.toISOString(), expires_at: expiresAt.toISOString() })
    .eq("id", existing.id)
    .eq("status", "unused") // garde-fou anti double-activation simultanée
    .select()
    .maybeSingle();

  if (updateError || !updated) {
    return { ok: false, message: "Ce code vient d'être activé ailleurs. Réessaie ou demande un nouveau code." };
  }

  const session = buildSession(updated, participantName);
  saveSession(session);
  return { ok: true, session };
}

function buildSession(codeRow, participantName) {
  return {
    codeId: codeRow.id,
    code: codeRow.code,
    direction: codeRow.direction,
    expiresAt: codeRow.expires_at,
    participantName: participantName || "",
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
    window.location.href = "/index.html?error=no_session";
    return null;
  }
  if (new Date(session.expiresAt) < new Date()) {
    window.location.href = "/index.html?error=expired";
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
      setTimeout(() => { window.location.href = "/index.html?error=expired"; }, 2000);
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
