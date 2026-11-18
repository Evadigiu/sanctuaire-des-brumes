// ============================================================
// LA DÉMO — Le Sanctuaire des Brumes
//
// Une suite d'écrans, sans billet, sans verrou et sans base de données :
// rien n'est envoyé nulle part, seules les vidéos sont chargées (Bunny).
// Page fabriquée par contenu/fabriquer-la-demo.py ; ce script, lui, est
// écrit à la main.
// ============================================================
function demarrerDemo(codeSac) {
  const ecrans = Array.from(document.querySelectorAll(".ecran"));
  let ici = 0;
  let fin = null;

  function couperLesMedias() {
    document.querySelectorAll("video, audio").forEach(m => { try { m.pause(); } catch (e) {} });
  }

  function montrer(i) {
    couperLesMedias();
    ici = Math.max(0, Math.min(ecrans.length - 1, i));
    ecrans.forEach((s, k) => { s.hidden = (k !== ici); });
    const s = ecrans[ici];
    if (s.hasAttribute("data-verdict")) afficherVerdict(s);
    window.scrollTo(0, 0);
  }

  ecrans.forEach(s => {
    s.querySelectorAll("[data-suivant]").forEach(b => b.addEventListener("click", () => montrer(ici + 1)));
    s.querySelectorAll("[data-retour]").forEach(b => b.addEventListener("click", () => montrer(ici - 1)));
    s.querySelectorAll("[data-passer]").forEach(b => b.addEventListener("click", () => montrer(ici + 1)));
  });

  // Les galeries : un bouton pour ouvrir, puis précédente et suivante.
  document.querySelectorAll("[data-galerie]").forEach(g => {
    const photos = Array.from(g.querySelectorAll("[data-galerie-photo]"));
    const compte = g.querySelector("[data-galerie-compte]");
    const prec = g.querySelector("[data-galerie-prec]");
    const suiv = g.querySelector("[data-galerie-suiv]");
    let n = 0;
    function voir(k) {
      n = Math.max(0, Math.min(photos.length - 1, k));
      photos.forEach((p, j) => { p.hidden = (j !== n); });
      compte.textContent = (n + 1) + " / " + photos.length;
      prec.disabled = (n === 0);
      suiv.disabled = (n === photos.length - 1);
    }
    g.querySelector("[data-galerie-ouvrir]").addEventListener("click", ev => {
      ev.target.hidden = true;
      g.querySelector("[data-galerie-vue]").hidden = false;
      voir(0);
    });
    prec.addEventListener("click", () => voir(n - 1));
    suiv.addEventListener("click", () => voir(n + 1));
  });

  // L'appel du commissaire.
  const decrocher = document.getElementById("decrocher");
  if (decrocher) decrocher.addEventListener("click", () => {
    decrocher.hidden = true;
    document.getElementById("blocAppel").hidden = false;
    const audio = document.getElementById("audioAppel");
    if (audio) audio.play().catch(() => {});
  });

  // Le code du sac : le bouton « Suivant » n'apparaît qu'une fois la serre ouverte.
  const ecranCode = document.querySelector('[data-bloque="code"]');
  if (ecranCode) {
    const suivant = ecranCode.querySelector("[data-suivant]");
    const champ = document.getElementById("codeDemo");
    const faux = document.getElementById("codeFaux");
    const bon = document.getElementById("codeBon");
    const aide = document.getElementById("codeAide");
    suivant.hidden = true;
    function ouvrir() {
      bon.hidden = false; faux.hidden = true; aide.hidden = true;
      champ.disabled = true; document.getElementById("validerCode").disabled = true;
      suivant.hidden = false;
    }
    function valider() {
      const saisi = (champ.value || "").replace(/\s+/g, "");
      if (!saisi) return;
      if (saisi === String(codeSac)) { ouvrir(); return; }
      champ.value = "";
      faux.textContent = "Ce code n'ouvre pas la porte. Regardez de nouveau les objets du sac.";
      faux.hidden = false;
    }
    document.getElementById("validerCode").addEventListener("click", valider);
    champ.addEventListener("keydown", ev => { if (ev.key === "Enter") { ev.preventDefault(); valider(); } });
    aide.addEventListener("click", () => {
      champ.value = String(codeSac);
      faux.className = "quiz-verdict";
      faux.textContent = "Le code est le " + codeSac + ".";
      faux.hidden = false;
      bon.hidden = false; aide.hidden = true;
      champ.disabled = true; document.getElementById("validerCode").disabled = true;
      suivant.hidden = false;
    });
  }

  // La question finale : le choix part aussitôt vers la vidéo de la vérité.
  document.querySelectorAll("[data-qcm] .quiz-prop").forEach(b => {
    b.addEventListener("click", () => { fin = b.getAttribute("data-fin"); montrer(ici + 1); });
  });

  function afficherVerdict(s) {
    s.querySelectorAll("[data-denouement]").forEach(d => {
      d.hidden = (d.getAttribute("data-denouement") !== (fin || "Mauvais"));
    });
    if (fin === "Bon") etincelles();
  }

  function etincelles() {
    const couleurs = ["#E4C87A", "#C9A24B", "#7BB27D", "#E9E6DC"];
    for (let i = 0; i < 70; i++) {
      const p = document.createElement("span");
      p.className = "etincelle";
      p.style.left = Math.random() * 100 + "vw";
      p.style.background = couleurs[i % couleurs.length];
      p.style.animationDuration = (2.2 + Math.random() * 2) + "s";
      p.style.animationDelay = (Math.random() * 0.8) + "s";
      document.body.appendChild(p);
      setTimeout(() => p.remove(), 5000);
    }
  }

  montrer(0);
}
