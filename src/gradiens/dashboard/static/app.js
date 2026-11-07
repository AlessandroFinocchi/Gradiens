// Gradiens: il poco JavaScript scritto a mano. Il resto lo fa htmx.

// Finestra delle Impostazioni (UI-10): <dialog> nativo riempito da htmx. Esc la chiude da solo.
document.addEventListener("htmx:afterSwap", (e) => {
  if (e.target.id === "impostazioni" && !e.target.open) e.target.showModal();
});
document.addEventListener("click", (e) => {
  const finestra = document.getElementById("impostazioni");
  // Il clic sul velo intorno alla finestra arriva al <dialog> stesso.
  if (e.target.closest("[data-chiudi]") || e.target === finestra) finestra.close();
});

// Il server conferma il nuovo tema (sezione Aspetto): lo si applica senza ricaricare.
document.addEventListener("tema-cambiato", (e) => {
  const tema = e.detail.value;
  if (tema === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", tema);
});

// Fine di un'esecuzione: si ricarica la parte della pagina che ne dipende (elenco delle notizie o Home).
document.addEventListener("esecuzione-finita", () => {
  const parte = document.querySelector("#elenco, #home");
  if (parte) htmx.ajax("GET", location.href, { target: `#${parte.id}`, select: `#${parte.id}`, swap: "outerHTML" });
});

// Indirizzo diretto a una sezione, es. /#impostazioni/aspetto (UI-10).
document.addEventListener("DOMContentLoaded", () => {
  const m = location.hash.match(/^#impostazioni\/([\w-]+)$/);
  if (m) htmx.ajax("GET", `/impostazioni/${m[1]}`, "#impostazioni");
});
