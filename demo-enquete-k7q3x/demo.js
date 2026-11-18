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
    const d = document.getElementById("decrocher");
    if (d) d.classList.remove("sonne");
    if (navigator.vibrate) { try { navigator.vibrate(0); } catch (e) {} }
  }

  function montrer(i) {
    couperLesMedias();
    // Les étincelles du verdict ne suivent pas le joueur sur l'écran suivant.
    document.querySelectorAll(".etincelle").forEach(p => p.remove());
    ici = Math.max(0, Math.min(ecrans.length - 1, i));
    ecrans.forEach((s, k) => { s.hidden = (k !== ici); });
    const s = ecrans[ici];
    // Comme sur une borne : le nom de l'étape en grand titre, et la barre
    // de progression remplie selon son numéro.
    const titre = document.getElementById("titreEtape");
    if (titre) titre.textContent = s.getAttribute("data-nom") || "";
    const barre = document.getElementById("position");
    if (barre) {
      const compte = barre.querySelector(".progression-compte");
      const total = parseInt(compte.getAttribute("data-total"), 10) || 1;
      const num = parseInt(s.getAttribute("data-num"), 10);
      const part = num ? num / total * 100 : (ici === 0 ? 0 : 100);
      barre.style.setProperty("--part", Math.round(part) + "%");
      barre.setAttribute("aria-valuenow", Math.round(part));
      compte.textContent = num ? num + " / " + total : "";
    }
    if (s.hasAttribute("data-verdict")) afficherVerdict(s);
    if (s.hasAttribute("data-appel")) fairesonner();
    window.scrollTo(0, 0);
  }

  ecrans.forEach(s => {
    s.querySelectorAll("[data-suivant]").forEach(b => b.addEventListener("click", () => montrer(ici + 1)));
    s.querySelectorAll("[data-retour]").forEach(b => b.addEventListener("click", () => montrer(ici - 1)));
    // « Passer la démo » : droit aux écrans qui parlent à l'organisateur.
    s.querySelectorAll("[data-passer-demo]").forEach(b => b.addEventListener("click", () => {
      const k = ecrans.findIndex(x => x.getAttribute("data-nom") === "Côté organisateur");
      montrer(k >= 0 ? k : ecrans.length - 1);
    }));
    s.querySelectorAll("[data-rejouer]").forEach(b => b.addEventListener("click", () => window.location.reload()));
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
      // Un fondu entre deux images déjà chargées : pas d'écran noir.
      photos.forEach((p, j) => { p.classList.toggle("actif", j === n); });
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

  // L'appel du commissaire : le téléphone sonne à l'arrivée sur l'écran.
  // Le joueur vient d'appuyer sur « Suivant » : le navigateur accepte donc
  // de jouer un son. S'il refuse quand même, le bouton pulse en silence.
  const decrocher = document.getElementById("decrocher");
  const sonnerie = document.getElementById("sonnerie");
  function fairesonner() {
    if (!decrocher || decrocher.hidden) return;
    decrocher.classList.add("sonne");
    if (sonnerie) { try { sonnerie.currentTime = 0; } catch (e) {} sonnerie.play().catch(() => {}); }
    if (navigator.vibrate) { try { navigator.vibrate([400, 200, 400, 2000, 400, 200, 400]); } catch (e) {} }
  }
  function arreterSonnerie() {
    if (sonnerie) sonnerie.pause();
    if (decrocher) decrocher.classList.remove("sonne");
    if (navigator.vibrate) { try { navigator.vibrate(0); } catch (e) {} }
  }
  if (decrocher) decrocher.addEventListener("click", () => {
    arreterSonnerie();
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
