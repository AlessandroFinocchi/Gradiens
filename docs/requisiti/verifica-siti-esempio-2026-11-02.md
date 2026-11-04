# Verifica dei siti di esempio (2 novembre 2026)

Verifica fatta con un client HTTP semplice, senza JavaScript, per capire se nella prima versione serve un browser headless. "Ultimi 7 giorni" vuol dire dal 26/10/2026. **V** = verificato, **D** = dedotto.

| Sito | Feed funzionante | Sitemap con date | API piattaforma | Serve JS? | Note |
|---|---|---|---|---|---|
| nature.com | `/nature.rss` (rel=alternate), con date | `/latest-news/sitemap.xml` (news sitemap) | no | no | V: la home senza cookie reindirizza a `?error=cookies_not_supported`, mentre feed e sitemap rispondono puliti. D: il paywall va gestito come "contenuto parziale". |
| hwupgrade.it | `//feeds.hwupgrade.it/rss_news.xml` (URL senza protocollo, altro sottodominio) | no (`sitemap1.txt` è un elenco senza date) | no | no | V: la sitemap è in ISO-8859-1 e contiene URL di altri sottodomini (`smarthome.`). |
| ilsoftware.it | `/feed/` (solo dal percorso comune, manca rel=alternate) | `news-sitemap.xml` e `sitemap_index.xml` | WordPress, ma `/wp-json/` è **vietato da robots.txt** | no | |
| redhotcyber.com | `/feed/gn` (si trova solo tra i link della pagina) | `news-sitemap.xml` | WordPress, `/wp-json/wp/v2/posts` risponde | no | V: `/feed/`, dichiarato in rel=alternate, fa 301 verso la home HTML. Una risposta "200 con HTML" non è un feed. |
| e3rehab.com/articles/ | `/feed/` | Yoast con lastmod | WordPress | no | V: gli articoli stanno alla radice, fuori dal prefisso `/articles/`. Nessun articolo negli ultimi 7 giorni. |
| chipsandcheese.com | `/feed` | `sitemap.xml` con lastmod | Substack con dominio proprio | no | Nessun articolo negli ultimi 7 giorni. |
| projectdiscovery.io/research | **no** (`/rss.xml` copre solo il blog) | parziale | no (Next.js) | no | V: `/research` è renderizzata lato server e contiene già link e date testuali ("Oct 21, 2026"). Serve il crawling dell'HTML statico. È il sito più fragile. |
| gamesbeat.com | `/feed/` | `sitemap_index.xml` con lastmod | WordPress | no | |
| freecodecamp.org/news | `/news/rss/` | `/news/sitemap.xml` | no (Eleventy) | no | L'HTML contiene 50 link con `datetime`. |
| acn.gov.it/portale/csirt-italia/ | `/portale/feedrss/-/journal/rss/20119/723192`, con 40 elementi negli ultimi 7 giorni | non verificabile (robots.txt in 403, Akamai) | Liferay | no | V: gli elementi del feed **non sono ordinati per data**, e gli articoli (`/portale/w/...`) stanno fuori dal prefisso della sezione. |
| thehackernews.com | `/feeds/posts/default`, che reindirizza a feedburner | `news-sitemap.xml` | Blogger | no | |
| 3blue1brown.com | `3blue1brown.substack.com/feed` (altro dominio, linkato nella pagina) | 207 URL senza lastmod | no | no | V: l'HTML statico contiene l'ultima lezione. D: il contenuto principale sono video, quindi conviene usare il canale YouTube. |
| evilsocket.net | `/atom.xml` | `sitemap.xml` con lastmod | no (Hexo) | no | Ultimo articolo del 01/04/2026. |

## Conclusione

Nessun sito richiede un browser headless: feed, sitemap o HTML statico (ProjectDiscovery) bastano. La cascata di scoperta deve però gestire questi casi:

- un feed che risponde con HTML;
- feed su altri domini o sottodomini, oppure con URL senza protocollo;
- sezioni i cui articoli escono dal prefisso del percorso (e3rehab, ACN);
- elementi del feed non ordinati per data;
- `robots.txt` va controllato **prima** di ogni strategia, compresa l'API della piattaforma (ilsoftware vieta `/wp-json/`).

Non verificato: paginazione, pagina CSIRT dietro consenso, varianti in altre lingue. È stato fatto un solo campionamento, in un solo giorno.
