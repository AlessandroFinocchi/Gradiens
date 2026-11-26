# Grafi di notizie – requisiti in lavorazione

Funzione nuova proposta dall'utente il 25 novembre 2026. Qui si raccolgono le decisioni della fase 1
(requisiti), una domanda alla volta; a fase chiusa confluiscono nel PRD e in CONTEXT.md.

## Idea dell'utente

Grafi tra le notizie: un nodo radice identifica il grafo, ogni nodo è una notizia, e ci sono nodi intermedi
che definiscono sezioni del grafo. Si possono creare più grafi e aggiungere notizie a un grafo; dentro un
grafo si assegnano frecce in ingresso e in uscita. La disposizione dei nodi si fa sia in automatico sia a mano.

## Comprensione di partenza

- Il grafo è costruito a mano dall'utente, a differenza dell'Argomento, che è assegnato dall'LLM e lineare
  nel tempo. I due concetti restano distinti.

## Decisioni

1. **Conservazione** (25 nov): una notizia che sta in almeno un grafo non viene cancellata dopo 7 giorni,
   anche senza cuore. Il grafo non mette il cuore e non entra nel raffinamento degli interessi. Uscita
   dall'ultimo grafo, la notizia torna alla regola dei 7 giorni (`ESE-09`).
2. **Sezioni e visualizzazione** (25 nov): ci sono due visualizzazioni, e ogni grafo sceglie la sua
   (si può cambiare in qualsiasi momento):
   - **a riquadri**: la radice è il riquadro esterno con il titolo del grafo, le sezioni sono riquadri che
     contengono le loro notizie (e sottosezioni);
   - **a nodi**: radice e sezioni sono nodi con titolo personalizzabile e un colore diverso da quello delle
     notizie, collegati ai loro elementi da frecce tratteggiate di appartenenza.

   Ne segue che i dati sono gli stessi per le due visualizzazioni: ogni notizia o sezione ha al più una
   sezione genitore nel grafo (senza genitore sta sotto la radice), e l'appartenenza non è una freccia
   dell'utente ma si disegna come riquadro o come freccia tratteggiata. Le frecce dell'utente sono un'altra
   cosa e si disegnano allo stesso modo nelle due visualizzazioni. Esempi disegnati nella conversazione
   del 25 nov (grafo "Sicurezza degli agenti LLM").
3. **Frecce** (25 nov): una freccia va da una notizia a un'altra dello stesso grafo e può avere
   un'etichetta facoltativa, breve (es. "approfondisce", "smentisce").
4. **Tutto a mano** (25 nov): appartenenza alle sezioni e frecce le decide solo l'utente. Gradiens non le
   propone e non le assegna da sé (niente LLM).
5. **Disposizione** (25 nov): all'inizio il grafo si dispone da solo, e a ogni aggiunta si ricalcola la
   posizione dei soli nodi mai spostati. Un nodo spostato a mano tiene la sua posizione. Il bottone
   "Riordina" ricalcola tutto, anche le posizioni manuali, dopo una conferma. Le posizioni si salvano
   separatamente per ciascuna visualizzazione.
6. **Aggiunta delle notizie** (25 nov): da entrambi i lati. Dalla notizia (pagina della notizia ed elenchi
   di Notizie, Archivio e Timeline) con "Aggiungi a un grafo", scegliendo il grafo e, facoltativa, la
   sezione (senza sezione va sotto la radice). Dal grafo con una ricerca tra le notizie esistenti (ultimi
   7 giorni, archivio, notizie già in altri grafi). La pagina della notizia elenca i grafi in cui compare,
   con il link a ciascuno.
7. **Fuori casa ed eliminazione** (25 nov): da fuori casa si aggiunge e si modifica, si toglie solo dal PC
   (come per cuori, interessi e fonti, ADR 0013).
   - Da fuori casa e dal PC: vedere i grafi, creare un grafo, aggiungere notizie, sezioni e frecce,
     rinominare, cambiare colore ed etichetta, spostare i nodi, cambiare visualizzazione, "Riordina".
   - Solo dal PC: eliminare un grafo o una sezione, togliere una notizia da un grafo, togliere una freccia.
   - Eliminare un grafo chiede conferma e ricorda che le notizie senza cuore e in nessun altro grafo
     tornano alla regola dei 7 giorni.
   - Eliminare una sezione non elimina il contenuto: notizie e sottosezioni passano alla sezione che la
     conteneva (o sotto la radice), le frecce restano.
   - Togliere una notizia da un grafo toglie anche le sue frecce in quel grafo.

8. **Pagine** (25 nov): nella sidebar la pagina Grafi sta tra Timeline e Archivio. La pagina Grafi è un
   elenco compatto (nome, notizie, sezioni, visualizzazione, ultima modifica) con "Nuovo grafo", che chiede
   solo il nome. La pagina del grafo ha un indirizzo proprio, il disegno occupa quasi tutto lo spazio, in
   alto ci sono nome, visualizzazione, "Riordina", "Nuova sezione" e la ricerca; un clic su una notizia
   apre un riquadro laterale con titolo, fonte, data, link alla pagina della notizia e azioni sul nodo.

9. **Frecce spezzate** (25 nov, dopo la preview): un doppio clic su una freccia aggiunge un punto di piega lì,
   che si trascina; un doppio clic sul punto lo toglie. I punti si vedono solo con la freccia selezionata. Le
   pieghe si salvano in proporzione ai due nodi, così seguono la freccia quando un nodo si sposta, e
   separatamente per ciascuna visualizzazione; "Riordina" le toglie. In più, un'opzione per grafo disegna
   tutte le frecce ad angolo retto (come lo stile ortogonale di draw.io), passando anche dalle pieghe.
10. **Aggancio dei nodi** (25 nov, dopo la preview): nella barra del grafo si sceglie "Aggancia", ricordato per
    grafo: **guide** (predefinito, come draw.io: linee di allineamento con centri e bordi degli altri nodi e guide
    di distribuzione, il nodo si aggancia alla linea), **griglia** (il nodo si muove a scatti sulla griglia),
    **libero**. Tenendo premuto Alt l'aggancio si sospende per quel movimento.

Fase 1 chiusa il 25 novembre 2026: i requisiti sono nel PRD (sezione 8.1, codici `GRA-*`) e in CONTEXT.md.

## Fase 2

- **Libreria** (25 nov): Cytoscape.js con fCoSE, vedi [ADR 0014](../adr/0014-grafi-disegnati-con-cytoscape-e-fcose.md).

## Fase 3 (preview)

Preview del 25 nov: [grafi.html](../../mockup/grafi.html), [grafo.html](../../mockup/grafo.html),
[notizia-grafi.html](../../mockup/notizia-grafi.html), con [grafi-comune.js](../../mockup/grafi-comune.js) e
[grafi.css](../../mockup/grafi.css). Usano lo stile e la sidebar della dashboard di oggi
(`src/gradiens/dashboard/static/stile.css`), non le preview del 2-6 nov, rimaste indietro. Cytoscape e fCoSE
vengono dalla CDN con le versioni bloccate; nel codice saranno file della repo (ADR 0014). Si aprono con un
server locale sulla cartella della repo (configurazione `preview-mockup` in `.claude/launch.json`, porta 8791,
perché la 8765 è di Gradiens).

Verificato nel browser: le due visualizzazioni sugli stessi dati; un nodo spostato a mano resta fermo, alla
stessa coordinata, dopo l'aggiunta di una notizia e dopo un ricaricamento (`fixedNodeConstraint`, ADR 0014);
freccia nuova con etichetta; azioni per togliere disattivate con la simulazione dell'accesso da fuori casa;
tema chiaro e scuro.

Scelte di dettaglio fatte nella preview, da approvare:
- la ricerca aggiunge la notizia nella sezione selezionata, altrimenti sotto la radice; "Nuova sezione" la crea
  dentro la sezione selezionata;
- cambiare la sezione di una notizia (o il contenitore di una sezione) libera la sua posizione manuale nella
  visualizzazione a riquadri, perché il nodo deve finire dentro il riquadro nuovo; nella vista a nodi resta;
- togliere da un grafo una notizia che ha più di 7 giorni, senza cuore e in nessun altro grafo chiede una
  conferma, perché verrà cancellata alla pulizia;
- la radice nella vista a riquadri non si trascina (trascinandola si sposta la vista), altrimenti un
  trascinamento fisserebbe tutti i nodi;
- la freccia nuova si crea con "Nuova freccia da qui" nel riquadro laterale e poi un clic sulla notizia
  d'arrivo; l'etichetta si scrive subito dopo, nel riquadro della freccia.

Seconda preview (25 nov), con `GRA-12` e `GRA-13`: bottone "Angoli retti" e scelta "Aggancia" nella barra,
pieghe con doppio clic, "Togli le pieghe" nel riquadro della freccia. Verificato in JavaScript nel browser, nelle
due visualizzazioni: ogni piega disegnata cade nel punto salvato, segue la freccia quando un nodo si sposta,
gli angoli retti passano dalle pieghe; con le guide un nodo si allinea esattamente al centro di un altro, con la
griglia il centro cade su multipli di 20, con Alt non si aggancia, e la posizione salvata è quella agganciata.
Trovato e corretto: Cytoscape prende il verso della perpendicolare dalla retta tra i bordi dei due nodi, che si
inverte quando i nodi sono accavallati (funzione `verso` in `grafo.html`; da portare in `grafo.js`).
