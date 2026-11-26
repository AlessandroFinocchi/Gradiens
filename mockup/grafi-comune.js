// Gradiens – parti comuni delle preview dei grafi (fase 3, 25 nov 2026). Usano lo stile della dashboard di oggi
// (src/gradiens/dashboard/static/stile.css) e la sua sidebar, non le preview del 2-6 nov. Dati finti.

const ICONE = {
  home: '<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>',
  timeline: '<path d="M12 3v18"/><circle cx="12" cy="7" r="2"/><circle cx="12" cy="17" r="2"/><path d="M14 7h6M4 17h6"/>',
  archivio: '<rect x="3" y="4" width="18" height="5" rx="1"/><path d="M5 9v10a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V9M10 13h4"/>',
  grafi: '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="9" r="2.5"/><circle cx="9" cy="18" r="2.5"/><path d="M8.4 6.6l7.2 1.8M6.7 8.4l1.6 7.2M16.4 10.9l-5.7 5.4"/>',
  aiuto: '<circle cx="12" cy="12" r="9"/><path d="M9.6 9.4a2.5 2.5 0 1 1 3.4 2.4c-.6.3-1 .8-1 1.5v.6"/><path d="M12 17h.01"/>',
  ingranaggio: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
  cuore: '<path d="M12 20s-7.5-4.6-7.5-10.2A4.3 4.3 0 0 1 12 7a4.3 4.3 0 0 1 7.5 2.8C19.5 15.4 12 20 12 20z"/>',
  esterno: '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
  sito: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
  arxiv: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M8 13h8M8 17h6"/>',
  youtube: '<rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="m10 9.5 4.5 2.5-4.5 2.5z"/>',
  video: '<rect x="3" y="5" width="18" height="14" rx="3"/><path d="m10 9 5 3-5 3z"/>',
  indietro: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
  chiudi: '<path d="M6 6l12 12M18 6 6 18"/>',
  cestino: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6"/>',
  aggiungi: '<path d="M12 5v14M5 12h14"/>',
  matita: '<path d="M4 20h4L19 9l-4-4L4 16z"/>',
  argomento: '<path d="M5 4v10a4 4 0 0 0 4 4h10M15 14l4 4-4 4"/>',
  riordina: '<path d="M4 12a8 8 0 0 1 13.7-5.6L20 8.7M20 4v4.7h-4.7M20 12a8 8 0 0 1-13.7 5.6L4 15.3M4 20v-4.7h4.7"/>',
  freccia: '<path d="M5 19 19 5M10 5h9v9"/>',
  sezione: '<rect x="3" y="4" width="18" height="16" rx="3" stroke-dasharray="3 2.5"/><path d="M7 9h6"/>',
  angolo: '<path d="M4 6h8v12h8"/><circle cx="4" cy="6" r="1.5"/><path d="m17 15 3 3-3 3"/>',
  cerca: '<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
};
const ic = (nome) => `<svg class="icona" viewBox="0 0 24 24" aria-hidden="true">${ICONE[nome]}</svg>`;

// Sidebar come in base.html, con Grafi tra Timeline e Archivio (GRA-10).
function sidebar(attiva) {
  const voce = (id, nome, href, icona = id) =>
    `<a class="voce" href="${href}"${id === attiva ? ' aria-current="page"' : ""}>${ic(icona)}<span>${nome}</span></a>`;
  return `<nav class="sidebar" aria-label="Pagine">
    <button class="marchio" type="button"><span class="segno">∇</span><span>Gradiens</span></button>
    ${voce("home", "Home", "#")}
    <div class="titolo-sezione"><span>Notizie</span></div>
    ${voce("siti", "Siti web", "#", "sito")}${voce("youtube", "YouTube", "#")}${voce("arxiv", "ArXiv", "#")}
    <hr class="divisore-sidebar">
    ${voce("timeline", "Timeline", "#")}${voce("grafi", "Grafi", "grafi.html")}${voce("archivio", "Archivio", "#")}
    <div class="basso">${voce("aiuto", "Aiuto", "#")}${voce("impostazioni", "Impostazioni", "#", "ingranaggio")}</div>
  </nav>`;
}

// Notizie finte: quelle del grafo di esempio e qualcuna in più da cercare e aggiungere.
const TIPI = { sito: ["sito", "Sito web"], arxiv: ["arxiv", "Paper arXiv"], video: ["video", "Video YT"] };
const NOTIZIE = [
  { id: "n1", titolo: "Prompt injection nascosta nelle pagine web dirotta gli agenti del browser", tipo: "sito", fonte: "redhotcyber.com", data: "20 nov" },
  { id: "n2", titolo: "Jailbreak a più turni: come gli attacchi graduali aggirano i filtri", tipo: "arxiv", fonte: "cs.CR", data: "18 nov" },
  { id: "n3", titolo: "Un filtro sulle chiamate agli strumenti blocca l'80% delle iniezioni", tipo: "arxiv", fonte: "cs.CL", data: "21 nov" },
  { id: "n4", titolo: "Sandbox per agenti: isolare file system e rete", tipo: "video", fonte: "Lab di Sicurezza", data: "22 nov" },
  { id: "n5", titolo: "Furto di dati da un assistente di posta tramite un'email preparata", tipo: "sito", fonte: "ilsoftware.it", data: "15 nov", vecchia: true },
  { id: "n6", titolo: "Valutare la robustezza degli agenti: un benchmark con 2.000 attacchi", tipo: "arxiv", fonte: "cs.AI", data: "23 nov" },
  { id: "n7", titolo: "ACN pubblica le linee guida per l'uso sicuro degli LLM nella PA", tipo: "sito", fonte: "acn.gov.it", data: "24 nov" },
  { id: "n8", titolo: "Agenti che scrivono codice: dove sbagliano davvero", tipo: "video", fonte: "AI Explained Italia", data: "19 nov" },
  { id: "n9", titolo: "Ransomware alla ASL: ripristinati i sistemi dopo dieci giorni", tipo: "sito", fonte: "redhotcyber.com", data: "24 nov" },
];
const notizia = (id) => NOTIZIE.find((n) => n.id === id);

// Colori delle sezioni: toni medi leggibili sia nel tema chiaro sia nello scuro.
const COLORI = ["#C0613D", "#2F8A74", "#6A63C4", "#B7791F", "#3D7BBF", "#A2507F"];

// Grafo di esempio (GRA-01..03). Le posizioni sono per visualizzazione; "fissa" = spostata a mano (GRA-06).
const GRAFO_ESEMPIO = {
  nome: "Sicurezza degli agenti LLM",
  visualizzazione: "riquadri",
  sezioni: [
    { id: "s1", titolo: "Attacchi", colore: COLORI[0], genitore: null },
    { id: "s2", titolo: "Difese", colore: COLORI[1], genitore: null },
    { id: "s3", titolo: "Iniezioni", colore: COLORI[3], genitore: "s1" },
  ],
  notizie: [
    { id: "n1", sezione: "s3" }, { id: "n5", sezione: "s3" }, { id: "n2", sezione: "s1" },
    { id: "n3", sezione: "s2" }, { id: "n4", sezione: "s2" }, { id: "n6", sezione: null },
  ],
  collegamenti: [
    { id: "c1", da: "n1", a: "n2", etichetta: "" },
    { id: "c2", da: "n1", a: "n3", etichetta: "risposta" },
    { id: "c3", da: "n3", a: "n4", etichetta: "approfondisce" },
    { id: "c4", da: "n5", a: "n1", etichetta: "stessa tecnica" },
    { id: "c5", da: "n6", a: "n3", etichetta: "misura" },
  ],
  posizioni: { riquadri: {}, nodi: {} },
};

// Elenco della pagina Grafi (GRA-10).
const GRAFI = [
  { nome: "Sicurezza degli agenti LLM", notizie: 6, sezioni: 3, visualizzazione: "a riquadri", modificato: "oggi alle 10:42" },
  { nome: "Riabilitazione del ginocchio", notizie: 9, sezioni: 4, visualizzazione: "a nodi", modificato: "22 nov" },
  { nome: "Ransomware nella sanità", notizie: 4, sezioni: 0, visualizzazione: "a riquadri", modificato: "18 nov" },
];
