# I grafi si disegnano nel browser con Cytoscape.js e fCoSE

I grafi di notizie (PRD, sezione 8.1) sono la prima interazione ricca della dashboard: nodi da trascinare,
sezioni disegnate come riquadri o come nodi, frecce con etichetta, disposizione automatica che rispetta le
posizioni scelte a mano (`GRA-05`, `GRA-06`). ADR 0003 prevedeva che interazioni così costassero più fatica
che in una SPA, e quel momento è arrivato. Si usa una libreria di grafi solo nella pagina del grafo, senza
cambiare il resto della dashboard.

La pagina del grafo è un template Jinja2 come le altre. Dentro c'è una tela disegnata da **Cytoscape.js**
(MIT), con il modulo di disposizione **fCoSE** (MIT, con le sue dipendenze `cose-base` e `layout-base`). Il
server passa alla pagina i dati del grafo in JSON (nodi, sezioni, collegamenti, posizioni salvate per la
visualizzazione scelta). Uno script del progetto, `dashboard/static/grafo.js`, li disegna e manda al server
ogni modifica: spostamenti, nuove frecce, cambi di sezione. Pannelli, form e bottoni attorno alla tela
restano HTML del server con htmx.

Le due visualizzazioni sono due modi di disegnare gli stessi dati in Cytoscape:
- **a riquadri**: le sezioni sono nodi composti (il riquadro contiene i figli) e la radice è il riquadro
  più esterno;
- **a nodi**: radice e sezioni sono nodi normali, e l'appartenenza diventa una freccia tratteggiata generata
  dalla pagina, che non si salva come collegamento.

La regola di `GRA-06` si ottiene con l'opzione `fixedNodeConstraint` di fCoSE: i nodi spostati a mano
restano fermi e il calcolo dispone solo gli altri. "Riordina" lancia il calcolo senza vincoli. Il vincolo
vale per i nodi semplici: nella visualizzazione a riquadri la posizione di una sezione segue quella dei suoi
figli. Verificato nella preview della fase 3 (25 nov): un nodo spostato a mano resta alla stessa
coordinata dopo l'aggiunta di una notizia.

Le guide e la griglia (`GRA-13`) vengono dall'estensione **cytoscape-grid-guide** (MIT), che aggancia i nodi
durante il trascinamento alle linee di allineamento oppure alla griglia. Le frecce spezzate (`GRA-12`) invece
sono codice del progetto: Cytoscape disegna una freccia a segmenti dati i punti di passaggio, e i punti di piega
sono piccoli nodi trascinabili che compaiono con la freccia selezionata. Ogni piega si salva come coppia di
numeri relativi alla retta tra i due nodi, così segue la freccia quando i nodi si spostano. Con l'opzione degli
angoli retti, fra due punti consecutivi si aggiunge l'angolo, prima in orizzontale e poi in verticale.

Decisione dell'utente del 25 nov 2026, tra le due proposte basate su Cytoscape.js; guide e frecce spezzate
aggiunte lo stesso giorno, dopo la prima preview.

## Opzioni considerate

- **Cytoscape.js con ELK** (disposizione a livelli nel verso delle frecce): scartata. Ordina bene le catene
  di collegamenti, ma non tiene fermi i nodi spostati a mano, quindi `GRA-06` andrebbe ottenuta a mano.
  Inoltre pesa circa 1,7 MB in più ed è più lenta.
- **vis-network**: scartata, non ha nodi composti, quindi niente visualizzazione a riquadri.
- **SVG disegnato a mano o con D3**: scartata. Trascinamento, riquadri che si allargano, frecce che
  seguono i nodi e disposizione automatica andrebbero scritti da capo.
- **cytoscape-edge-editing per le pieghe**: scartata. Richiede Konva, circa 330 KB in più, per una funzione
  che nel progetto sono poche decine di righe.
- **Frecce ad angolo retto di Cytoscape (`taxi`)**: scartata. Non passano per punti scelti dall'utente, quindi
  non si combinano con le pieghe.
- **React Flow**: scartata, richiede React e un passo di compilazione (ADR 0003).

## Conseguenze

- Cinque file JavaScript salvati nella repository in `dashboard/static/`, come htmx: `cytoscape.min.js`
  (3.35.0), `cytoscape-fcose.js` (2.2.0), `cose-base.js` (2.2.0), `layout-base.js` (2.0.1) e
  `cytoscape-grid-guide.js` (2.3.3), circa 860 KB in tutto. L'ultima versione di grid-guide è del 2022: se
  smettesse di funzionare con una Cytoscape nuova, la si sostituisce con codice del progetto. Si caricano
  solo nella pagina del grafo e si aggiornano a mano. Niente Node né compilazione.
- La pagina del grafo è l'unica con uno script del progetto non banale (`grafo.js`), da tenere piccolo:
  disegno, trascinamento, scelta dei nodi e invio delle modifiche. Le regole (cosa si può togliere da fuori
  casa, conservazione delle notizie) restano nel server.
- Le rotte che salvano le modifiche del grafo rispondono in JSON alla tela; quelle che tolgono qualcosa
  controllano che la richiesta venga dal PC (`GRA-09`, `AMB-02`), come le altre azioni "solo dal PC".
- Le posizioni dei nodi si salvano nel database per grafo e per visualizzazione.
- Sul telefono la tela si usa con le dita (Cytoscape gestisce il tocco), ma non è garantito che lo spazio
  basti per grafi grandi.
