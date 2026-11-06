// Gradiens – parti condivise delle preview (fase 3): icone, sidebar, finestra Impostazioni,
// controllo del tema. Dati finti. Nella fase 4 diventeranno template Jinja2.

const ICONE = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
  notizie: '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 8.5h10M7 12h10M7 15.5h6"/>',
  timeline: '<path d="M12 3v18"/><circle cx="12" cy="7" r="2"/><circle cx="12" cy="17" r="2"/><path d="M14 7h6M4 17h6"/>',
  archivio: '<rect x="3" y="4" width="18" height="5" rx="1"/><path d="M5 9v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9M10 13h4"/>',
  aiuto: '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.4a2.5 2.5 0 1 1 3.4 2.4c-.6.3-1 .8-1 1.5v.6"/><path d="M12 17h.01"/>',
  ingranaggio: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  cuore: '<path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7a4.3 4.3 0 0 1 7.5 2.8C19.5 15.4 12 20 12 20z"/>',
  esterno: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  sito: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  arxiv: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M8 13h8M8 17h6"/>',
  video: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3z"/>',
  short: '<rect x="7" y="3" width="10" height="18" rx="2.5"/><path d="m11 10 3 2-3 2z"/>',
  avvia: '<path d="M7 4.5v15l12-7.5z" fill="currentColor" stroke="none"/>',
  argomento: '<path d="M5 4v10a4 4 0 0 0 4 4h10M15 14l4 4-4 4"/>',
  indietro: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  chiudi: '<path d="M6 6l12 12M18 6 6 18"/>',
  avvertimento: '<path d="M10.3 3.9 2.4 17.6A2 2 0 0 0 4.1 20.6h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
  interessi: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.2"/>',
  youtube: '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="m10 9.5 4.5 2.5-4.5 2.5z"/>',
  modelli: '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
  esecuzione: '<circle cx="12" cy="13" r="8"/><path d="M12 9v4l2.5 2.5M9 2h6"/>',
  accensione: '<path d="M12 3v9M6.3 6.3a8 8 0 1 0 11.4 0"/>',
  telegram: '<path d="M21 4 3 11l6 2.5L18 7l-7 8 7 5z"/>',
  aggiungi: '<path d="M12 5v14M5 12h14"/>',
  aspetto: '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor"/>',
  matita: '<path d="M4 20h4L19 9l-4-4L4 16z"/>',
  unisci: '<path d="M6 4v5a6 6 0 0 0 6 6 6 6 0 0 1 6 6M18 4v5a6 6 0 0 1-3 5.2"/>',
  bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4M9 13h.01M15 13h.01"/>',
  spunta: '<path d="m5 12 5 5 9-10"/>',
  cestino: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6"/>',
};
const ic = (nome, classe = "") => `<svg class="icona ${classe}" viewBox="0 0 24 24" aria-hidden="true">${ICONE[nome]}</svg>`;

// Sezioni delle Impostazioni con i segnali di UI-14 (dati finti).
const SEZIONI = [
  { gruppo: "Contenuti", id: "interessi", nome: "Interessi", icona: "interessi", segnale: ["novita", "1 proposta di raffinamento da approvare"] },
  { gruppo: "Contenuti", id: "canali-youtube", nome: "Canali YouTube", icona: "youtube" },
  { gruppo: "Contenuti", id: "siti-web", nome: "Siti web", icona: "sito", segnale: ["avvertimento", "projectdiscovery.io: nessuna strategia funzionante"] },
  { gruppo: "Contenuti", id: "arxiv", nome: "arXiv", icona: "arxiv", segnale: ["novita", "Tetto di paper raggiunto nell'ultima esecuzione"] },
  { gruppo: "Funzionamento", id: "modelli", nome: "Modelli LLM", icona: "modelli" },
  { gruppo: "Funzionamento", id: "esecuzione", nome: "Esecuzione", icona: "esecuzione" },
  { gruppo: "Funzionamento", id: "avvio", nome: "Avvio", icona: "accensione" },
  { gruppo: "Funzionamento", id: "telegram", nome: "Telegram", icona: "telegram" },
  { gruppo: "Interfaccia", id: "aspetto", nome: "Aspetto", icona: "aspetto" },
];

function segnale(s) {
  if (!s) return "";
  const [tipo, motivo] = s;
  const icona = tipo === "avvertimento" ? ic("avvertimento") : "";
  return `<span class="segnale ${tipo}" title="${motivo}">${icona}<span class="nascosto">${motivo}</span></span>`;
}
// L'ingranaggio mostra il segnale più grave tra quelli delle sezioni.
function segnaleGlobale() {
  const s = SEZIONI.map((x) => x.segnale).filter(Boolean);
  if (!s.length) return "";
  const grave = s.find(([t]) => t === "avvertimento") || s[0];
  return segnale([grave[0], s.length === 1 ? grave[1] : `${s.length} sezioni delle Impostazioni da guardare`]);
}

function sidebar(attiva) {
  const pagine = [["home", "Home", "home.html"], ["notizie", "Notizie", "notizie.html"], ["timeline", "Timeline", "timeline.html"], ["archivio", "Archivio", "archivio.html"]];
  const voce = ([id, nome, href]) =>
    `<a class="voce" href="${href}" ${id === attiva ? 'aria-current="page"' : ""}>${ic(id)}<span>${nome}</span></a>`;
  return `<nav class="sidebar" aria-label="Pagine">
    <a class="marchio" href="home.html"><span class="segno">∇</span><span>Gradiens</span></a>
    ${pagine.map(voce).join("")}
    <div class="basso">
      ${voce(["aiuto", "Aiuto", "aiuto.html"])}
      <button class="voce apri-impostazioni" type="button">${ic("ingranaggio")}<span>Impostazioni</span>
        <span class="pallino-voce">${segnaleGlobale()}</span></button>
    </div>
  </nav>`;
}

/* ---------- Contenuto delle sezioni delle Impostazioni ---------- */
const riga = (titolo, descrizione, controllo, classe = "") =>
  `<div class="riga ${classe}"><div class="testo"><div class="titolo">${titolo}</div>${descrizione ? `<div class="descrizione">${descrizione}</div>` : ""}</div><div class="controllo">${controllo}</div></div>`;
const interruttore = (on, etichetta) => `<input type="checkbox" role="switch" class="interruttore" ${on ? "checked" : ""} aria-label="${etichetta}">`;

const CONTENUTI = {
  interessi: () => `
    <h2>Interessi</h2>
    <p class="intro">Il nome si usa nei filtri. Descrizione e raffinamento guidano il filtro LLM. Il raffinamento lo propone l'LLM dalle notizie con il cuore, e vale solo se lo approvi.</p>
    <button class="bottone secondario piccolo">${ic("aggiungi")}Aggiungi interesse</button>

    <div class="interesse">
      <div class="interesse-testa"><strong>LLM e agenti</strong>${segnale(["novita", "Proposta di raffinamento da approvare"])}<button class="bottone-icona" aria-label="Elimina interesse" title="Elimina interesse">${ic("cestino")}</button></div>
      <label class="etichetta-campo">Descrizione</label>
      <textarea class="campo" rows="2">Modelli linguistici, agenti autonomi, tecniche di valutazione e di riduzione dei costi.</textarea>
      <div class="riga proposta" style="margin-top:14px; display:block">
        <div class="titolo">Proposta di raffinamento, da 4 notizie con il cuore</div>
        <div class="confronto">
          <div><span class="etichetta-campo">Attuale</span>Mi interessano soprattutto gli agenti che usano strumenti.</div>
          <div class="nuovo"><span class="etichetta-campo">Proposto</span>Mi interessano gli agenti che usano strumenti e i metodi per ridurre il costo dei modelli, come pre-filtri con modelli piccoli e cache dei prompt. Meno interesse per i benchmark generici.</div>
        </div>
        <div style="display:flex; gap:8px; margin-top:12px; flex-wrap:wrap">
          <button class="bottone piccolo">Approva</button>
          <button class="bottone secondario piccolo">Modifica e approva</button>
          <button class="bottone secondario piccolo">Scarta</button>
        </div>
      </div>
    </div>

    <div class="interesse">
      <div class="interesse-testa"><strong>Sicurezza informatica</strong><button class="bottone-icona" aria-label="Elimina interesse" title="Elimina interesse">${ic("cestino")}</button></div>
      <label class="etichetta-campo">Descrizione</label>
      <textarea class="campo" rows="2">Attacchi, vulnerabilità e incidenti, soprattutto in Italia e nella pubblica amministrazione.</textarea>
      <label class="etichetta-campo">Raffinamento (approvato il 2 nov)</label>
      <textarea class="campo" rows="2">Più attenzione a ransomware contro sanità e enti locali e agli attacchi alla supply chain del software.</textarea>
    </div>

    <div class="interesse">
      <div class="interesse-testa"><strong>Allenamento e riabilitazione</strong><button class="bottone-icona" aria-label="Elimina interesse" title="Elimina interesse">${ic("cestino")}</button></div>
      <label class="etichetta-campo">Descrizione</label>
      <textarea class="campo" rows="2">Forza, riabilitazione da infortuni a ginocchio e tendini, basate sulla ricerca.</textarea>
    </div>`,

  "canali-youtube": () => `
    <h2>Canali YouTube</h2>
    <p class="intro">Incolla un indirizzo qualsiasi del canale: <code>@nome</code>, <code>/channel/…</code> o il link di un video.</p>
    <div style="display:flex; gap:8px"><input class="campo" placeholder="https://www.youtube.com/@…"><button class="bottone">Aggiungi</button></div>
    <h3>Canali seguiti</h3>
    ${riga("Lab di Sicurezza", '<span class="stato ok">ok</span> · 4 video e 2 short nell\'ultima esecuzione', '<button class="bottone secondario piccolo">Rimuovi</button>')}
    ${riga("Coach Marta", '<span class="stato ok">ok</span> · 1 short nell\'ultima esecuzione', '<button class="bottone secondario piccolo">Rimuovi</button>')}
    ${riga("AI Explained Italia", 'nessun video nuovo · 2 video senza trascrizione nel resoconto', '<button class="bottone secondario piccolo">Rimuovi</button>')}`,

  "siti-web": () => `
    <h2>Siti web</h2>
    <p class="intro">Basta l'indirizzo: Gradiens analizza il sito e crea il suo profilo, che puoi modificare.</p>
    <div style="display:flex; gap:8px"><input class="campo" placeholder="https://…"><button class="bottone">Aggiungi</button></div>
    <h3>Siti seguiti</h3>
    ${riga(`projectdiscovery.io/blog ${segnale(["avvertimento", "Nessuna strategia funzionante"])}`, '<span class="stato errore">nessuna strategia funzionante</span> Da 2 esecuzioni la pagina del blog non elenca articoli leggibili. Se il sito ha un feed, puoi inserirlo a mano nel profilo.', '<button class="bottone secondario piccolo">Profilo</button><button class="bottone piccolo">Rigenera profilo</button>', "evidenziata")}
    ${riga(`acn.gov.it/portale/notizie ${segnale(["novita", "Profilo rigenerato"])}`, '<span class="stato">profilo rigenerato</span> Il feed precedente rispondeva con una pagina HTML; ora si usa la sitemap. Sito collegato proposto: <b>csirt.gov.it</b> (disattivato).', '<button class="bottone secondario piccolo">Vedi differenze</button><button class="bottone secondario piccolo">Profilo</button>', "proposta")}
    ${riga("redhotcyber.com", '<span class="stato ok">ok</span> · feed RSS e sitemap · 12 articoli nuovi', '<button class="bottone secondario piccolo">Profilo</button>')}
    ${riga("e3rehab.com/articles", 'nessun articolo nuovo · sezione, feed RSS', '<button class="bottone secondario piccolo">Profilo</button>')}
    ${riga("ilsoftware.it", '<span class="stato ok">ok</span> · feed RSS · 9 articoli nuovi', '<button class="bottone secondario piccolo">Profilo</button>')}`,

  arxiv: () => `
    <h2>arXiv</h2>
    <p class="intro">Tutti i paper nuovi delle categorie scelte passano dal pre-filtro. Serve almeno una categoria.</p>
    ${riga("Categorie", "", '<span class="chip">cs.CR ✕</span><span class="chip">cs.CL ✕</span><span class="chip">cs.AI ✕</span><button class="bottone secondario piccolo">Aggiungi</button>')}
    ${riga(`Tetto di paper per esecuzione ${segnale(["novita", "Tetto raggiunto"])}`, "Nell'ultima esecuzione il tetto è stato raggiunto: elaborati i 50 paper più recenti su 83.", '<input class="campo" type="number" value="50" style="width:90px">', "proposta")}`,

  modelli: () => `
    <h2>Modelli LLM</h2>
    <p class="intro">Provider e modello si scelgono separatamente per i due ruoli. Claude Code usa la quota del tuo abbonamento, senza costi in più. Le chiavi, se servono, stanno nel file <code>.env</code>, mai nei file versionati.</p>
    <h3>Pre-filtro</h3>
    ${riga("Provider", "Legge a blocchi titolo e sommario delle notizie nuove.", '<select class="selettore"><option>Claude Code (abbonamento)</option><option>API di Claude</option><option>Compatibile OpenAI (locale)</option></select>')}
    ${riga("Modello", "", '<select class="selettore"><option>Haiku</option><option>Sonnet</option></select>')}
    <h3>Elaborazione</h3>
    ${riga("Provider", "Valutazione, riassunto, argomento, proposte di raffinamento, analisi dei siti.", '<select class="selettore"><option>Claude Code (abbonamento)</option><option>API di Claude</option><option>Compatibile OpenAI (locale)</option></select>')}
    ${riga("Modello", "", '<select class="selettore"><option>Haiku</option><option>Sonnet</option></select>')}
    <h3>Collegamenti</h3>
    ${riga("Claude Code", '<span class="stato ok">collegato</span> · abbonamento Pro · quota disponibile', '<button class="bottone secondario piccolo">Verifica</button>')}
    ${riga("Chiave API di Claude", "Non configurata. Serve solo se scegli l'API di Claude, che è a pagamento.", '<button class="bottone secondario piccolo">Aggiungi</button>')}
    ${riga("Server compatibile OpenAI", "Per i modelli locali (Ollama, LM Studio). Non configurato.", '<input class="campo" placeholder="http://localhost:11434/v1" style="width:240px">')}`,

  esecuzione: () => `
    <h2>Esecuzione</h2>
    ${riga("Soglia di pertinenza", "Una notizia si mostra se almeno un punteggio la supera.", '<input type="range" min="0" max="100" value="60" aria-label="Soglia"><b>60</b>')}
    ${riga("Finestra di raccolta", "Si raccolgono le notizie pubblicate negli ultimi giorni indicati. Le notizie fuori dall'archivio si cancellano comunque dopo 7 giorni.", '<select class="selettore"><option>7 giorni</option><option>6 giorni</option><option>5 giorni</option><option>4 giorni</option><option>3 giorni</option><option>2 giorni</option><option>1 giorno</option></select>')}
    ${riga("Orario dell'esecuzione programmata", "Ogni giorno, mentre Gradiens è acceso.", '<input class="campo" type="time" value="07:30" style="width:110px">')}
    ${riga("Metti in pausa la programmazione", "Le esecuzioni avviate a mano funzionano comunque. Anche da Telegram con /pausa e /riprendi.", interruttore(false, "Pausa della programmazione"))}
    <h3>Esclusioni</h3>
    ${riga("Escludi contenuti sponsorizzati e offerte", "", interruttore(true, "Escludi contenuti sponsorizzati e offerte"))}
    ${riga("Escludi articoli a pagamento", "Se disattivo, gli articoli a pagamento si mostrano con il riassunto della parte pubblica.", interruttore(true, "Escludi articoli a pagamento"))}`,

  avvio: () => `
    <h2>Avvio</h2>
    ${riga("Avvia Gradiens all'accensione del PC", "Parte senza bisogno di accedere a Windows né di accendere il monitor. Cambiare questa impostazione richiede una conferma di amministratore sullo schermo del PC, quindi va fatto stando al PC.", interruttore(false, "Avvio all'accensione"))}
    ${riga("Stato", "Avvio a mano con <code>gradiens avvia</code>. Nessuna registrazione nel sistema operativo.", "")}`,

  telegram: () => `
    <h2>Telegram</h2>
    ${riga("Bot", '<span class="stato ok">collegato</span> · @mio_gradiens_bot', '<button class="bottone secondario piccolo">Ricollega con il tutorial</button>')}
    ${riga("Chat autorizzata", "Chat privata, confermata il 4 nov. Il bot ignora tutte le altre chat.", "")}
    ${riga("Messaggio di prova", "Manda un messaggio alla chat per controllare il collegamento.", '<button class="bottone secondario piccolo">Invia</button>')}
    <h3>Comandi del bot</h3>
    ${riga("/aggiorna", "Avvia un'esecuzione.", "")}
    ${riga("/stato", "Esecuzione in corso o ultima conclusa, e prossima programmata.", "")}
    ${riga("/ultima", "Rimanda il messaggio dell'ultima esecuzione.", "")}
    ${riga("/pausa · /riprendi", "Sospende e riattiva l'esecuzione programmata.", "")}
    ${riga("/help", "Elenca i comandi.", "")}`,

  aspetto: () => `
    <h2>Aspetto</h2>
    ${riga("Tema", "Come il sistema segue l'impostazione di Windows o del telefono.", `<div class="segmenti" role="group" aria-label="Tema">${[["auto", "Sistema"], ["light", "Chiaro"], ["dark", "Scuro"]].map(([t, n]) => `<button class="scelta-tema" data-tema="${t}" aria-pressed="${temaAttuale() === t}">${n}</button>`).join("")}</div>`)}`,
};

function finestraImpostazioni() {
  let gruppo = "";
  const voci = SEZIONI.map((s) => {
    const titolo = s.gruppo !== gruppo ? `<h3>${(gruppo = s.gruppo)}</h3>` : "";
    return `${titolo}<button class="sezione-voce" data-sezione="${s.id}">${ic(s.icona)}<span class="nome">${s.nome}</span>${segnale(s.segnale)}</button>`;
  }).join("");
  return `<div class="velo" hidden>
    <div class="finestra" tabindex="-1" role="dialog" aria-modal="true" aria-labelledby="titolo-impostazioni">
      <div class="finestra-testata"><h2 id="titolo-impostazioni">Impostazioni</h2>
        <button class="bottone-icona chiudi-impostazioni" aria-label="Chiudi le Impostazioni">${ic("chiudi")}</button></div>
      <div class="finestra-corpo">
        <nav class="sezioni" aria-label="Sezioni delle Impostazioni">${voci}</nav>
        <section class="sezione-contenuto"></section>
      </div>
    </div>
  </div>`;
}

function apriImpostazioni(id = "interessi") {
  const velo = document.querySelector(".velo");
  velo.hidden = false;
  velo.querySelectorAll(".sezione-voce").forEach((b) => b.setAttribute("aria-current", b.dataset.sezione === id));
  velo.querySelector(".sezione-contenuto").innerHTML = CONTENUTI[id]();
  history.replaceState(null, "", `#impostazioni/${id}`);
  velo.querySelector(".finestra").focus();
}
function chiudiImpostazioni() {
  document.querySelector(".velo").hidden = true;
  history.replaceState(null, "", location.pathname);
  document.querySelector(".apri-impostazioni").focus();
}

/* ---------- Tema (UI-10, sezione Aspetto) ---------- */
// Nell'app vera la scelta sta nella configurazione in .gradiens/; nelle preview nel browser.
function temaAttuale() { try { return localStorage.getItem("gradiens-tema") || "auto"; } catch { return "auto"; } }
function applicaTema(t) {
  if (t === "auto") document.documentElement.removeAttribute("data-theme");
  else document.documentElement.setAttribute("data-theme", t);
  try { localStorage.setItem("gradiens-tema", t); } catch {}
  document.querySelectorAll(".scelta-tema").forEach((b) => b.setAttribute("aria-pressed", b.dataset.tema === t));
}
applicaTema(temaAttuale()); // subito, per evitare il lampo del tema sbagliato

/* ---------- Notizie (dati finti condivisi) ---------- */
const parametro = (nome) => new URLSearchParams(location.search).get(nome);
const TIPI = { sito: ["sito", "Sito"], arxiv: ["arxiv", "arXiv"], video: ["video", "Video YT"], short: ["short", "Short YT"] };

const NOTIZIE = [
  { tipo: "sito", fonte: "redhotcyber.com", data: "5 nov, 09:12", cuore: true,
    titolo: "Ransomware all'ASL Valle Verde: il gruppo pubblica i primi 40 GB di dati",
    riassunto: "Il gruppo che ha colpito l'ASL Valle Verde ha pubblicato sul proprio sito un primo archivio con documenti amministrativi e referti. L'azienda sanitaria conferma l'esfiltrazione e dice che le prenotazioni torneranno attive entro venerdì. Il Garante privacy ha aperto un'istruttoria.",
    interessi: [["Sicurezza informatica", 94]], argomento: "Attacco ransomware all'ASL Valle Verde" },
  { tipo: "arxiv", fonte: "cs.CL", data: "4 nov",
    titolo: "Modelli linguistici piccoli come pre-filtri nelle pipeline di recupero",
    originale: "Small Language Models as Pre-filters in Retrieval Pipelines",
    riassunto: "Gli autori usano un modello da un miliardo di parametri per scartare i documenti irrilevanti prima del modello principale. Su tre benchmark il costo scende del 70% con una perdita di accuratezza sotto il 2%. Il metodo funziona peggio sulle domande che richiedono più passaggi di ragionamento.",
    interessi: [["LLM e agenti", 91], ["Sicurezza informatica", 62]] },
  { tipo: "video", fonte: "Lab di Sicurezza · 24 min", data: "3 nov",
    titolo: "Supply chain npm: anatomia di un pacchetto compromesso",
    riassunto: "Il video ricostruisce passo per passo come un pacchetto molto usato è stato sostituito da una versione che rubava i token di accesso, e mostra tre controlli da aggiungere alla pipeline di build: lockfile verificati, permessi minimi dei token e firma dei pacchetti.",
    interessi: [["Sicurezza informatica", 86]], argomento: "Pacchetti npm compromessi di ottobre" },
  { tipo: "sito", fonte: "e3rehab.com", data: "3 nov", stato: "data incerta",
    titolo: "Tendinopatia rotulea: cosa dice la ricerca sul carico progressivo",
    originale: "Patellar Tendinopathy: What the Research Says About Progressive Loading",
    riassunto: "L'articolo riassume gli studi sugli esercizi isometrici e a carico lento: funzionano meglio del riposo, ma servono almeno 12 settimane. Propone una progressione in quattro fasi, con i criteri per passare alla successiva.",
    interessi: [["Allenamento e riabilitazione", 79]] },
  { tipo: "short", fonte: "Coach Marta · 52 s", data: "4 nov",
    titolo: "Squat bulgaro: l'errore che sposta il carico sul ginocchio",
    riassunto: "Il piede anteriore troppo vicino alla panca fa avanzare il ginocchio. Il consiglio è misurare la distanza con un passo e mezzo prima di iniziare la serie.",
    interessi: [["Allenamento e riabilitazione", 72]] },
  { tipo: "sito", fonte: "ilsoftware.it", data: "2 nov, 17:40", stato: "contenuto parziale",
    titolo: "Windows 11, patch d'emergenza per un errore di autenticazione Kerberos",
    riassunto: "Il contenuto è stato estratto solo in parte. L'aggiornamento corregge un difetto introdotto il mese scorso che impediva l'accesso ai controller di dominio.",
    interessi: [["Sicurezza informatica", 66]] },
];

function rigaNotizia(n) {
  const [icona, tipo] = TIPI[n.tipo];
  const argomento = n.argomento ? `<span>·</span><a class="argomento" href="argomento.html" title="Apri la timeline dell'argomento" style="position:relative;z-index:1">${ic("argomento")}${n.argomento}</a>` : "";
  return `<li class="notizia">
    <div class="n-corpo">
      <h3 class="n-titolo"><a href="notizia.html">${n.titolo}</a></h3>
      ${n.originale ? `<p class="n-originale">Titolo originale: ${n.originale}</p>` : ""}
      <div class="n-meta">${ic(icona)}<span>${tipo}</span>·<span>${n.fonte}</span>·<span>${n.data}</span>
        ${n.stato ? `<span class="stato">${n.stato}</span>` : ""}${argomento}</div>
      <p class="n-riassunto">${n.riassunto}</p>
      <div class="n-piede">${n.interessi.map(([nome, p]) => `<span class="punteggio${p >= 80 ? " alto" : ""}">${nome} <b>${p}</b></span>`).join("")}</div>
    </div>
    <div class="n-azioni">
      <a class="bottone-icona" href="#" target="_blank" rel="noopener" aria-label="Apri l'originale in una nuova scheda" title="Apri l'originale">${ic("esterno")}</a>
      <button class="bottone-icona cuore" aria-pressed="${!!n.cuore}" aria-label="${n.cuore ? "Togli il cuore" : "Metti il cuore"}">${ic("cuore")}</button>
    </div>
  </li>`;
}

/* ---------- Argomenti (dati finti condivisi da Timeline e pagina dell'argomento) ---------- */
const ARGOMENTI = [
  { nome: "Attacco ransomware all'ASL Valle Verde", info: "dal 1 nov · aggiornato oggi", nuove: 2, notizie: [
    ["5 nov", "Ransomware all'ASL Valle Verde: il gruppo pubblica i primi 40 GB di dati", "sito", "redhotcyber.com", true],
    ["4 nov", "ASL Valle Verde, il Garante privacy apre un'istruttoria sull'attacco", "sito", "redhotcyber.com"],
    ["3 nov", "ASL Valle Verde, prenotazioni ferme per il terzo giorno: si lavora su carta", "sito", "ilsoftware.it"],
    ["2 nov", "Il gruppo criminale rivendica l'attacco all'ASL Valle Verde e chiede un riscatto", "sito", "redhotcyber.com"],
    ["1 nov", "Attacco informatico all'ASL Valle Verde: sistemi spenti in tutti gli ospedali", "sito", "acn.gov.it"],
  ]},
  { nome: "Pacchetti npm compromessi di ottobre", info: "dal 24 ott · aggiornato il 3 nov", notizie: [
    ["3 nov", "Supply chain npm: anatomia di un pacchetto compromesso", "video", "Lab di Sicurezza"],
    ["29 ott", "Pacchetti npm compromessi: il registro revoca 2.000 token", "sito", "redhotcyber.com", true],
    ["24 ott", "Un pacchetto npm molto usato distribuiva un malware che ruba token", "sito", "redhotcyber.com", true],
  ]},
  { nome: "Falla critica nei router CasaNet", info: "dal 31 ott · aggiornato il 2 nov", notizie: [
    ["2 nov", "Router CasaNet, disponibile l'aggiornamento che chiude la falla critica", "sito", "ilsoftware.it"],
    ["31 ott", "Falla critica nei router CasaNet: accesso da remoto senza password", "sito", "acn.gov.it"],
  ]},
];

function metadatiArgomento(a) {
  const archivio = a.notizie.filter((n) => n[4]).length;
  return [`${a.notizie.length} notizie`, a.info, archivio ? `${archivio} in archivio` : ""].filter(Boolean).join(" · ");
}

// Rinomina, unisci ed elimina: pannelli nativi <details>, uguali in elenco e nella pagina dell'argomento.
function azioniArgomento(a) {
  const altri = ARGOMENTI.filter((x) => x !== a).map((x) => `<option>${x.nome}</option>`).join("");
  return `<div class="azioni-argomento">
    <details><summary class="bottone-icona" title="Rinomina" aria-label="Rinomina l'argomento">${ic("matita")}</summary>
      <div class="popover"><input class="campo" value="${a.nome}" aria-label="Nuovo nome"><button class="bottone piccolo">Rinomina</button></div></details>
    <details><summary class="bottone-icona" title="Unisci a un altro argomento" aria-label="Unisci a un altro argomento">${ic("unisci")}</summary>
      <div class="popover"><p>Le notizie di questo argomento passano nell'argomento scelto, che mantiene il suo nome.</p>
        <select class="selettore" aria-label="Argomento di destinazione">${altri}</select><button class="bottone piccolo">Unisci</button></div></details>
    <details><summary class="bottone-icona" title="Elimina" aria-label="Elimina l'argomento">${ic("cestino")}</summary>
      <div class="popover"><p>Le notizie restano, ma non appartengono più a nessun argomento.</p><button class="bottone piccolo">Elimina l'argomento</button></div></details>
  </div>`;
}

// Un solo pannello aperto alla volta.
document.addEventListener("toggle", (e) => {
  if (e.target.open && e.target.closest(".azioni-argomento"))
    document.querySelectorAll(".azioni-argomento details[open]").forEach((d) => d !== e.target && (d.open = false));
}, true);

// Gli elementi con data-icona="nome" ricevono l'icona all'inizio.
function inserisciIcone(radice = document) {
  radice.querySelectorAll("[data-icona]").forEach((el) => { el.insertAdjacentHTML("afterbegin", ic(el.dataset.icona)); el.removeAttribute("data-icona"); });
}

/* ---------- Avvio ---------- */
document.addEventListener("DOMContentLoaded", () => {
  inserisciIcone();
  const app = document.querySelector(".app");
  if (!app || app.hasAttribute("data-senza-sidebar")) return; // configurazione iniziale: niente sidebar né Impostazioni
  app.insertAdjacentHTML("afterbegin", sidebar(app.dataset.pagina));
  document.body.insertAdjacentHTML("beforeend", finestraImpostazioni());

  const m = location.hash.match(/^#impostazioni(?:\/([\w-]+))?/);
  if (m) apriImpostazioni(CONTENUTI[m[1]] ? m[1] : undefined);

  document.addEventListener("click", (e) => {
    const t = e.target;
    if (t.closest(".apri-impostazioni")) return apriImpostazioni();
    if (t.closest(".chiudi-impostazioni") || t.classList.contains("velo")) return chiudiImpostazioni();
    const sez = t.closest(".sezione-voce");
    if (sez) return apriImpostazioni(sez.dataset.sezione);
    const tema = t.closest(".scelta-tema");
    if (tema) return applicaTema(tema.dataset.tema);
    const link = t.closest("a[data-impostazioni]");
    if (link) { e.preventDefault(); return apriImpostazioni(link.dataset.impostazioni); }
    const premuto = t.closest("button[aria-pressed]");
    if (premuto) {
      const on = premuto.getAttribute("aria-pressed") !== "true";
      premuto.setAttribute("aria-pressed", on);
      if (premuto.classList.contains("cuore")) {
        premuto.setAttribute("aria-label", on ? "Togli il cuore" : "Metti il cuore");
        const testo = premuto.querySelector(".testo-cuore");
        if (testo) testo.textContent = on ? "Ha il cuore" : "Metti il cuore";
      }
    }
    if (t.closest('a[href="#"]')) e.preventDefault();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !document.querySelector(".velo").hidden) chiudiImpostazioni();
  });
});
