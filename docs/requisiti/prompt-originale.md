Voglio scrivere una applicazione per fare scraping di informazioni dal web in base ai miei interessi, riassumerle e poterle leggere con velocità e già filtrate in base a cosa mi interessa appunto.

Effettua tutto il lavoro in una nuova directory chiamata "Gradiens" che sarà il nome dell'applicazione (dal latino di "Gradiente", per indicare la direzione dei propri interessi), e lavora solo dentro di essa.

Tra le prime informazioni per la costruzione dei requisi ci sono le seguenti:

- FONTI
Le fonti da cui estrapolare le informazioni sono video di youtube dotati di trascrizione, pagine di siti web e articoli di arxiv

- INTERESSI
Gli interessi nelle impostazioni voglio che siano definiti come una coppia (nome, descrizione), devono poter essere aggiunti, modificati e cancellati. Il nome verrà usato per i filtri, la descrizione per il matching LLM-based con le notizie.

- LLM
Il filtraggio di ciascuna notizia in base agli interessi definiti, e il riassunto delle notizie, devono essere configurabili per essere fatti tramite claude API (tramite modelli a basso consumo di token).  Le claude API sono il default, ma progetta l'applicazione affinchè sia semplice estenderla in futuro per usare anche altri API come quelle di ChatGPT o Gemini. Non serve ancora realizzare anche la loro configurabilità, ma considera che in futuro il meccanismo debba essere esteso con altre API.
Inoltre, mi piacerebbe usare anche modelli locali anziche le API di un piano a pagamento, anche se ora il computer non mi permette di usare buoni modelli avendo solo una NVIDIA RTX 3070 con 8 GB di vRAM, quindi valuta se è possibile avere a disposizione anche questa scelta, e costruisci comunque questo lato delll'applicazione in modo che sia estendibile anche tramite modelli locali.

- MECCANISMO DI SCRAPING
Si devono estrapolare le informazioni nuove degli ultimi giorni, per al massimo 7 giorni. L'estrapolazione deve essere avviata, e voglio una notifica su telegram con le top 3 notizie che hai estrapolato per ciascuna delle 3 tipologie di fonte (arxiv, youtube e siti web)

- DASHBOARD
Ler quanto riguarda le pagine della web dashboard, ci devono sicuramente essere
    1. La homepage, la pagina principale con una summary degli ultimi aggiornamenti
    2. La pagina delle notizie, in cui deve essere possibile fare l'aggiornamento con un bottone sugli ultimi 7 giorno, aggiungere una notizia ai preferiti (cliccando su una stella), mettere mi piace ad una notizia (cliccando su un cuore) e diversi filtri anche paralleli, sia per tipologia, che per interesse, che per data.
    3. Una pagina archivio con tutte le notizie salvate, e quindi persistenti nel tempo, che non devono essere cancellate. Tutte le notizie non salvate nell'archivio e più vecchie di 7 giorni devono essere cancellate.
    4. Una pagina timeline che aggrega le informazioni provenienti da uno stesso argomento (es. guerra in ucraina, elezioni presidenziali USA, pubblicazioni su argomento X, etc...) in una timeline per poter vedere il progresso di quell'argomento nel tempo. Le informazioni in questo caso devono essere presenti, quindi quelle degli ultimi 7 giorni o quelle nell'archivio.
    5. Impostazioni, con stile simile a quella di claude code, con la possibilità di inserire le informazioni necessarie per far funzionare l'applicazione, e che deve essere compilata all'avvio dell'applicazione se le informazioni necessarie sono assenti. In particolare ci deve essere almeno un canale youtube, almeno un sito web, almeno un interesse, e tutto il resto della configurazione necessaria, come quello che serve per le claude API.
Le pagine devono essere esplorabili con una sidebar che mostra sempre le icone di ciascuna pagina, ed eventualmente espandibile per viasuallizzarne anche il nome.

- DETTAGLI FUNZIONAMENTO
L'applicazione deve funzionare completamente dalla dashboard, ma voglio anche poter lanciare l'aggiornamento da CLI, così da lanciarlo anche se non sono a casa e poter leggere gli aggiornamenti la sera.
Per ogni scaping voglio anche sapere le metriche, quindi il tempo impiegato, il numero di articoli esaminati, quelli filtrati e quelli mostrati.

- DETTAGLI FONTI
Per i video youtube, voglio poter fornire una lista di canali youtube da cui estrapolare i nuovi video, ma solo i video dotati di trascrizione devono essere riassunti, quelli senza trascrizioni sono segnalati come "trascrizione assente" o altro problema se diverso. I video voglio che siano filtrati in funzione degli interessi definiti nelle impostazioni.
Per i paper su arxiv, voglio che siano filtrati in funzione degli interessi definiti nelle impostazioni.
Per i siti web, voglio che siano filtrati gli articoli in funzione degli interessi definiti nelle impostazioni. I siti che voglio poter inserire sono molto eterogenei: riviste scientifiche, testate di notizie su tecnologia e cybersecurity, blog tecnici personali, blog aziendali, portali istituzionali, siti divulgativi e di formazione. Hanno in comune il fatto di mostrare degli articoli sulla pagina principale, ma sono anche organizzati in sezioni e categorie esplorabili, quindi la pagina principale non contiene necessariamente tutti gli articoli recenti. L'indirizzo che inserisco può essere la home page oppure una sezione specifica del sito (ad esempio una pagina "articles", "news" o "research"). Per "articolo" intendo qualunque contenuto con una data di pubblicazione: notizia, post, paper, approfondimento, lezione, alert o bollettino di sicurezza. Questi sono i siti di esempio, da usare anche come casi di test durante lo sviluppo:
    - https://www.nature.com/
    - https://www.hwupgrade.it/
    - https://www.ilsoftware.it/
    - https://www.redhotcyber.com/
    - https://e3rehab.com/articles/
    - https://chipsandcheese.com/
    - https://projectdiscovery.io/research
    - https://gamesbeat.com/
    - https://www.freecodecamp.org/news
    - https://www.acn.gov.it/portale/csirt-italia/
    - https://thehackernews.com/
    - https://www.3blue1brown.com/
    - https://www.evilsocket.net/

  Requisito: per aggiungere un sito deve bastare il suo indirizzo, senza configurazioni scritte apposta per quel sito. L'applicazione non deve limitarsi alla pagina indicata: deve trovare gli articoli pubblicati nella finestra temporale (al massimo 7 giorni) anche quando non compaiono in quella pagina, esplorando il sito in modo automatico e controllato. Se l'indirizzo è una sezione, l'esplorazione resta circoscritta a quella sezione (le sue pagine successive e sottosezioni), anche se gli articoli che elenca hanno indirizzi esterni al suo percorso.

  Una prima verifica su questi siti (novembre 2026) ha fatto emergere casi concreti che la soluzione deve gestire:
    - feed RSS/Atom e sitemap in percorsi non standard o su altri domini: redhotcyber.com/feed/gn e redhotcyber.com/rhc-sitemap.xml, il feed di The Hacker News su feeds.feedburner.com, quello di Hardware Upgrade su feeds.hwupgrade.it, 3Blue1Brown che rimanda al feed Substack della sua newsletter. I feed vanno quindi cercati tra i link della pagina, non solo negli indirizzi più comuni;
    - articoli su sottodomini o siti collegati (Hardware Upgrade rimanda a gaming.hwupgrade.it, edge9.hwupgrade.it, greenmove.hwupgrade.it e fotografidigitali.it: va deciso se rientrano nel perimetro del sito) e sezioni i cui articoli stanno fuori dal percorso della sezione (e3rehab.com/articles/ elenca articoli che si trovano nella radice del sito);
    - contenuti non visibili a un client automatico: la home di Chips and Cheese (su Substack) mostra solo la pagina di iscrizione, 3Blue1Brown carica via script l'elenco delle lezioni, la home di GamesBeat restituisce un elenco senza link né date;
    - date assenti o relative negli elenchi (la home di ilsoftware.it non mostra date, freeCodeCamp scrive "2 days ago"), date contenute nell'URL (evilsocket.net/2026/04/02/...), paginazione con pulsante "carica altri" (freeCodeCamp);
    - blocco dei client automatici: il portale ACN/CSIRT Italia rifiuta le richieste che non arrivano da un browser, ma esiste un feed RSS ufficiale degli alert (indirizzo segnalato da un aggregatore, da verificare: https://www.acn.gov.it/portale/feedrss/-/journal/rss/20119/723192). Le protezioni non vanno aggirate: si cerca un canale ufficiale alternativo oppure si segnala il problema;
    - contenuti a pagamento (molti articoli di ricerca di Nature), sezioni di offerte commerciali (Hardware Upgrade, ilsoftware.it) e contenuti sponsorizzati mescolati agli articoli (The Hacker News), che devo poter escludere;
    - frequenze di pubblicazione molto diverse: da decine di articoli al giorno (Hardware Upgrade) o diversi al giorno (Nature, freeCodeCamp) a pochi al mese o all'anno (projectdiscovery.io/research, e3rehab.com, evilsocket.net), quindi "nessun articolo nuovo" è un esito normale e non un errore;
    - lingue e codifiche diverse: siti in italiano e in inglese, versioni multilingua (redhotcyber.com/en/, le edizioni di freeCodeCamp), pagine in ISO-8859-1 (Hardware Upgrade). Il filtraggio deve funzionare a prescindere dalla lingua dell'articolo e da quella in cui ho scritto gli interessi.

  Proposta di soluzione, da valutare e raffinare insieme durante la definizione dei requisiti:
    1. Profilo del sito: quando aggiungo un sito, l'applicazione lo analizza una volta e salva un profilo con i feed trovati, le sitemap, le sezioni, la piattaforma riconosciuta (WordPress, Substack, Blogger, ecc.), l'eventuale necessità di un browser, dove si trova la data degli articoli e la strategia scelta, mostrandomi un'anteprima degli articoli che troverebbe. Il profilo è visibile e modificabile nelle impostazioni: posso includere o escludere sezioni e feed (es. le offerte), aggiungere a mano l'indirizzo di un feed o di una sezione, impostare dei limiti. Siccome i siti cambiano struttura, il profilo viene rigenerato quando smette di funzionare (es. zero articoli per più esecuzioni di fila o errori ripetuti).
    2. Scoperta degli articoli a cascata, dalla strategia più affidabile ed economica alla più costosa, combinando i risultati (un feed contiene spesso solo gli ultimi 10-50 articoli, che sui siti ad alto volume non coprono 7 giorni):
       a. feed RSS/Atom, generali e di sezione, trovati dai tag <link rel="alternate"> e dai link nella pagina, oltre che nei percorsi comuni;
       b. sitemap, trovate tramite robots.txt e nei percorsi comuni (comprese le news sitemap), usando le date di pubblicazione o di modifica per prendere solo gli ultimi giorni;
       c. API o feed nativi della piattaforma riconosciuta (es. l'API REST di WordPress), che permettono di filtrare per data;
       d. esplorazione controllata dell'HTML: dalla pagina di partenza si seguono menu, sezioni, categorie e paginazione con profondità limitata, fermandosi quando gli articoli diventano più vecchi della finestra temporale; gli articoli si riconoscono dai metadati strutturati (JSON-LD di tipo Article/NewsArticle/BlogPosting, og:type=article, article:published_time, tag <time>) e dagli schemi ricorrenti negli indirizzi;
       e. browser headless (es. Playwright) solo come ultima risorsa, per i siti che mostrano i contenuti solo tramite JavaScript.
    3. LLM una tantum, codice deterministico a ogni esecuzione: l'LLM può intervenire nella creazione del profilo (es. scegliere quali sezioni sono pertinenti ai miei interessi, o capire come riconoscere l'elenco degli articoli quando le euristiche falliscono), ma le esecuzioni periodiche usano le regole salvate senza consumare token. Lo scraping è sempre fatto dal codice dell'applicazione e mai delegato a strumenti di navigazione offerti da un provider LLM, così funziona allo stesso modo con le Claude API e con un modello locale.
    4. Estrazione: testo principale con una libreria di tipo readability (es. trafilatura); titolo, autore, data e sezione dai metadati della pagina. La data si prende, in ordine, da feed o sitemap, metadati della pagina, URL, data relativa nell'elenco; se non è determinabile, l'articolo viene marcato "data incerta".
    5. Filtraggio in due fasi per contenere costi e richieste: un primo filtro economico, a blocchi di più articoli, su titolo e sommario (presi dal feed o dalla meta description); solo gli articoli che lo superano vengono scaricati per intero, valutati e riassunti.
    6. Deduplicazione e memoria: URL normalizzati (canonical, senza parametri di tracciamento) e registro degli articoli già visti, perché lo stesso articolo compare in home, in più sezioni, nel feed e nella sitemap e non va rielaborato a ogni esecuzione; quando possibile si riconoscono anche i duplicati tra fonti diverse (es. una lezione di 3Blue1Brown e il video corrispondente sul suo canale YouTube).
    7. Scraping rispettoso e robusto: rispetto di robots.txt, limite di richieste per dominio con pause tra una e l'altra, User-Agent identificabile, timeout e nuovi tentativi, cache HTTP (ETag/Last-Modified), tetto di pagine e di articoli per sito a ogni esecuzione. Paywall, captcha e protezioni anti-bot non si aggirano: si usa ciò che è pubblico (es. l'abstract) e si segnala il limite.
    8. Stati espliciti, come per i video senza trascrizione: ogni sito e ogni articolo ha uno stato visibile nell'interfaccia, ad esempio "ok", "nessun articolo nuovo", "contenuto parziale (paywall)", "accesso bloccato", "richiede JavaScript", "data incerta", "nessuna strategia funzionante", "errore di estrazione".
    9. Estendibilità: le strategie di scoperta e di estrazione sono moduli intercambiabili, come i provider LLM, così si possono aggiungere nuove piattaforme o, solo per i casi più ostici, adattatori dedicati a un singolo sito, senza toccare il resto.

  Criterio di accettazione: per ciascuno dei siti di esempio l'applicazione trova gli articoli degli ultimi 7 giorni anche fuori dalla pagina indicata, oppure segnala in modo chiaro perché non ci riesce e cosa posso fare (es. inserire a mano l'indirizzo di un feed).


Il piano di lavoro è il seguente:
1. Iniziare prima dalla documentazione dei requisiti dell'applicazione
2. Stack tecnologico, come il sistema di storage e il resto di cui avrai bisogno
3. Preview delle schermate, possibilmente in html così che posso visualizzarle e proporre delle modifiche
4. Iniziare a scrivere codice.

Ad ogni step, voglio che mi fai delle domande e delle proposte per raffinare ogni punto.


















