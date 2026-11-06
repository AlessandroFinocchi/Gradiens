"""Il risultato di una strategia in una raccolta."""

from dataclasses import dataclass, field

from gradiens.fonti import Candidata
from gradiens.fonti.siti.rete import TETTO, VIETATA, Pagina


@dataclass
class Raccolta:
    candidate: list[Candidata] = field(default_factory=list)
    copre: bool = False  # ha visto articoli più vecchi di `dal`: l'elenco copre tutta la finestra
    riuscita: bool = False  # almeno una risorsa ha risposto come previsto
    bloccata: bool = False  # il sito rifiuta i client automatici
    guasti: list[str] = field(default_factory=list)  # guasti veri (WEB-24), in frasi per l'utente

    def errore(self, pagina: Pagina, cosa: str) -> None:
        if pagina.codice == TETTO:
            return  # tetto di pagine raggiunto: non è un guasto del sito
        if pagina.bloccata:
            self.bloccata = True
        elif pagina.codice == VIETATA:
            self.guasti.append(f"robots.txt ora vieta {cosa} {pagina.url}")
        else:
            self.guasti.append(f"{cosa} {pagina.url} non si legge ({pagina.codice or 'errore di rete'})")
