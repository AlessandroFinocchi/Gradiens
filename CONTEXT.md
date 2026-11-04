# Gradiens

Applicazione personale che raccoglie contenuti da YouTube, arXiv e siti web, li filtra con un LLM in base agli interessi dell'utente e li riassume.

## Linguaggio

**Esecuzione**:
Un singolo ciclo di raccolta, filtraggio e riassunto su tutte le fonti configurate, avviato a mano (dashboard, CLI, Telegram) o dalla programmazione giornaliera. Ogni esecuzione produce le proprie metriche.
_Evitare_: scraping, aggiornamento, run, job

**Notizia**:
Un singolo contenuto con data di pubblicazione proveniente da una fonte: un video YouTube, un paper arXiv o un articolo di un sito web.
_Evitare_: item, contenuto, post (come termine generale)

**Short**:
Video YouTube in formato breve. È una Notizia di tipo distinto dal video normale, così da poterla filtrare separatamente.
_Evitare_: video breve, clip

**Pertinenza**:
Punteggio da 0 a 100 che misura quanto una Notizia corrisponde a un Interesse. Una notizia ne ha uno per ogni interesse a cui è pertinente, e viene mostrata se almeno uno supera la soglia.
_Evitare_: rilevanza, score, rank

**Profilo del sito**:
Descrizione salvata di come trovare gli articoli di un sito web: perimetro, feed, sitemap, sezioni incluse o escluse, piattaforma e strategia. Viene generato all'aggiunta del sito, è modificabile dall'utente e viene rigenerato solo in caso di guasti ripetuti.
_Evitare_: configurazione del sito, regole, adattatore

**Interesse**:
Qualcosa che interessa all'utente. È formato da un nome (usato nei filtri), una descrizione scritta dall'utente e un Raffinamento facoltativo; la descrizione e il raffinamento servono insieme al filtro LLM.
_Evitare_: tema, categoria, tag

**Raffinamento**:
Testo associato a un Interesse e separato dalla sua descrizione, che precisa ciò che interessa all'utente sulla base delle notizie con Mi piace. L'utente lo può modificare o azzerare.
_Evitare_: descrizione appresa, profilo

**Proposta di raffinamento**:
Un nuovo testo di Raffinamento, oppure un nuovo Interesse, generato dall'LLM aggregando i Mi piace. Entra in vigore solo se l'utente lo approva.

**Argomento**:
Una storia precisa che si sviluppa nel tempo, come un singolo evento e la sua evoluzione (es. "Attacco ransomware alla ASL X", non "attacchi ransomware"). Raggruppa le notizie che ne seguono gli sviluppi e appare come timeline.
_Evitare_: tema, interesse, cluster, storia

**Preferito**:
Notizia segnata con la stella dall'utente. Un preferito entra nell'Archivio.
_Evitare_: salvato, bookmark

**Mi piace**:
Notizia segnata con il cuore perché è stata interessante. Un mi piace entra nell'Archivio e serve a raffinare gli Interessi.
_Evitare_: like, cuore (come nome del concetto)

**Archivio**:
L'insieme delle notizie che sono Preferito o Mi piace, conservate senza limite di tempo. Le notizie fuori dall'archivio vengono cancellate dopo 7 giorni.
_Evitare_: salvate, storico
