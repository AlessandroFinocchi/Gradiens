"""Il profilo del sito (WEB-02, CONTEXT.md): come trovare gli articoli, salvato all'aggiunta e modificabile."""

from dataclasses import asdict, dataclass, field, fields

from gradiens.fonti.siti.indirizzi import chiave, dentro, host, stesso_dominio

# Un campo con delle voci rende attiva la strategia che lo usa, anche se l'analisi non l'aveva scelta.
STRATEGIA_DEL_CAMPO = {"feed": "feed", "sitemap": "sitemap", "sezioni": "html"}


@dataclass
class Profilo:
    """Descrizione salvata di come trovare gli articoli di un sito.

    Modifiche manuali (WEB-25): `modificati` elenca i campi cambiati dall'utente nelle Impostazioni;
    `rigenera` li copia così come sono dal vecchio profilo, quindi un feed aggiunto a mano resta anche
    se smette di funzionare (lo segnala `raccogli`). Per feed, sezioni ed esclusioni usa i metodi qui
    sotto, che tengono allineate anche `strategie` e `modificati`; per gli altri campi (limiti, siti
    collegati, strategie) assegna il valore e aggiungi il nome del campo a `modificati`.
    """

    url: str  # indirizzo inserito dall'utente: home o sezione
    perimetro: str = ""  # "dominio.it" (home: sottodomini compresi) o "dominio.it/sezione" (solo la sezione), WEB-06/09
    piattaforma: str = ""  # es. "wordpress", "substack", "hexo"; vuota se non riconosciuta
    feed: list[str] = field(default_factory=list)  # feed usati: tutti i loro articoli valgono, anche su altri domini (WEB-08)
    sitemap: list[str] = field(default_factory=list)
    sezioni: list[str] = field(default_factory=list)  # pagine elenco da esplorare oltre a `url`
    esclusi: list[str] = field(default_factory=list)  # prefissi di indirizzo esclusi: sezioni, percorsi o feed (WEB-03/21)
    siti_collegati: dict[str, bool] = field(default_factory=dict)  # dominio esterno -> attivo (WEB-07)
    strategie: list[str] = field(default_factory=list)  # strategie attive; la cascata le prova nell'ordine di `strategie.STRATEGIE`
    data_da: str = ""  # dove si trova la data degli articoli
    diagnosi: str = ""  # stato WEB-26 quando nessuna strategia funziona, es. "accesso bloccato"
    pagine_massime: int = 40  # per esecuzione (WEB-19)
    articoli_massimi: int = 100  # per esecuzione (WEB-19)
    modificati: list[str] = field(default_factory=list)

    def come_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def da_dict(cls, d: dict) -> "Profilo":
        noti = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in noti})  # i campi sconosciuti di versioni future si ignorano

    @property
    def dominio(self) -> str:
        return host(self.url)

    @property
    def sezione(self) -> bool:
        return "/" in self.perimetro

    def nel_perimetro(self, url: str) -> bool:
        h = host(url)
        if any(attivo and stesso_dominio(h, d) for d, attivo in self.siti_collegati.items()):
            return True
        if self.sezione:
            return dentro(url, self.perimetro)
        return stesso_dominio(h, self.perimetro)

    def escluso(self, url: str) -> bool:
        return any(dentro(url, e) for e in self.esclusi)

    def aggiungi_feed(self, url: str) -> None:
        self._aggiungi("feed", url)

    def aggiungi_sezione(self, url: str) -> None:
        self._aggiungi("sezioni", url)

    def escludi(self, prefisso: str) -> None:
        if prefisso not in self.esclusi:
            self.esclusi.append(prefisso)
        self._modificato("esclusi")

    def _aggiungi(self, campo: str, url: str) -> None:
        valori = getattr(self, campo)
        if url not in valori:
            valori.append(url)
        self.attiva(STRATEGIA_DEL_CAMPO[campo])
        self._modificato(campo)

    def attiva(self, strategia: str) -> None:
        if strategia not in self.strategie:
            self.strategie.append(strategia)

    def _modificato(self, campo: str) -> None:
        if campo not in self.modificati:
            self.modificati.append(campo)


def perimetro_di(url: str) -> str:
    """Home -> dominio intero; sezione -> host e percorso, senza sottodomini (WEB-06, WEB-09)."""
    k = chiave(url).rstrip("/")
    return k if "/" in k else host(url)
