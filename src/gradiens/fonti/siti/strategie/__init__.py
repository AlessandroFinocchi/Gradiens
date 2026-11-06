"""Strategie di scoperta degli articoli, moduli intercambiabili (WEB-10, WEB-12).

Una strategia è un modulo con:
- `async analizza(nav, profilo, pagina) -> str | None`: durante la creazione del profilo cerca le sue
  risorse (feed, sitemap…) e le scrive nel profilo; restituisce dove trova la data degli articoli,
  oppure None se sul sito non funziona. `pagina` è la pagina iniziale già letta;
- `async raccogli(nav, profilo, dal) -> Raccolta`: a ogni esecuzione, solo con le regole del profilo.

Una nuova piattaforma o un adattatore per un singolo sito è un nuovo modulo aggiunto a `STRATEGIE`.
"""

from gradiens.fonti.siti.strategie import feed, html, sitemap, wordpress

# Ordine della cascata: dalla strategia più affidabile ed economica alla più costosa.
STRATEGIE = {"feed": feed, "sitemap": sitemap, "wordpress": wordpress, "html": html}
