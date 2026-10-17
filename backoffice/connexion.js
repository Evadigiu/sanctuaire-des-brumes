// ============================================================
// LA PORTE DU BACKOFFICE — Le Sanctuaire des Brumes
//
// Le suivi en direct et les statistiques ne s'ouvrent qu'à un compte de
// l'équipe, créé à la main dans Supabase (Authentication, puis Users).
//
// Pourquoi ce n'est plus un mot de passe écrit dans la page : la page est
// publique, son code aussi. Un mot de passe qu'elle vérifie elle-même se
// lit dans le dépôt, et surtout il ne protège pas les données, que
// n'importe qui pouvait demander directement à Supabase avec la clé
// publique du site. Désormais c'est Supabase qui refuse : les vues du
// backoffice ne répondent qu'à un compte connecté (correctif 12), et les
// inscriptions sont fermées, si bien que personne ne peut s'en créer un.
//
// La connexion reste ouverte d'une visite à l'autre sur le même appareil,
// jusqu'au bouton « Se déconnecter ».
//
// Dépend de supabase-client.js (supabaseClient).
// ============================================================

/**
 * Ouvre la page à un compte connecté, sinon montre le formulaire.
 *   idPage : le bloc à révéler une fois connecté
 *   demarrer : appelée une seule fois, à l'ouverture
 */
function porteEquipe(idPage, demarrer) {
  const porte = document.getElementById("gate");
  const page = document.getElementById(idPage);
  const email = document.getElementById("gateEmail");
  const mdp = document.getElementById("gateMdp");
  const bouton = document.getElementById("enterBtn");
  const erreur = document.getElementById("gateError");
  let ouverte = false;

  function ouvrir(session) {
    if (ouverte) return;
    ouverte = true;
    porte.style.display = "none";
    page.style.display = "block";
    const qui = document.getElementById("quiEstConnecte");
    if (qui && session && session.user) qui.textContent = session.user.email || "";
    demarrer();
  }

  function direErreur(texte) {
    erreur.textContent = texte;
    erreur.classList.add("visible");
  }

  async function seConnecter() {
    erreur.classList.remove("visible");
    if (!email.value.trim() || !mdp.value) {
      direErreur("Saisissez votre e-mail et votre mot de passe.");
      return;
    }
    bouton.disabled = true;
    bouton.textContent = "...";
    const { data, error } = await supabaseClient.auth.signInWithPassword({
      email: email.value.trim(),
      password: mdp.value,
    });
    bouton.disabled = false;
    bouton.textContent = "Se connecter";
    if (error || !data || !data.session) {
      direErreur(error && /invalid/i.test(error.message)
        ? "E-mail ou mot de passe incorrect."
        : "Connexion impossible : " + ((error && error.message) || "raison inconnue") + ".");
      return;
    }
    mdp.value = "";
    ouvrir(data.session);
  }

  bouton.addEventListener("click", seConnecter);
  [email, mdp].forEach(c => c.addEventListener("keydown", e => {
    if (e.key === "Enter") seConnecter();
  }));

  const sortir = document.getElementById("seDeconnecter");
  if (sortir) sortir.addEventListener("click", async () => {
    try { await supabaseClient.auth.signOut(); } catch (e) { }
    window.location.reload();
  });

  // Déjà connecté sur cet appareil : on entre directement.
  supabaseClient.auth.getSession().then(({ data }) => {
    if (data && data.session) ouvrir(data.session);
  }, () => {});
}
