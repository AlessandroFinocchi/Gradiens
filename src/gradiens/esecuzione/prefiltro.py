"""Pre-filtro a blocchi (ESE-04) e tetto arXiv (ARX-02, ARX-03, ADR 0010)."""

import logging

from sqlalchemy.orm import Session

from gradiens.dati import notizie
from gradiens.esecuzione import prompt
from gradiens.esecuzione.chiamata import chiedi
from gradiens.esecuzione.metriche import Avanzamento, Metriche
from gradiens.esecuzione.parallelo import in_parallelo
from gradiens.fonti import Candidata
from gradiens.llm.base import ErroreBloccante, ErroreLLM, Provider

log = logging.getLogger("gradiens.esecuzione.esecutore")  # i messaggi restano quelli dell'esecutore nel log

BLOCCO_PREFILTRO = 30  # notizie per chiamata di pre-filtro (ADR 0006)
GIRO_PREFILTRO = 3  # blocchi di paper lanciati insieme in un giro del pre-filtro (ADR 0010)


async def prefiltra(
    s: Session,
    nuove: list[Candidata],
    prefiltro: Provider,
    sistema: str,
    modello: str,
    tetto: int,
    m: Metriche,
    avanzamento: Avanzamento,
) -> tuple[list[Candidata], list[Candidata]]:
    """Pre-filtro a blocchi (ESE-04); le notizie scartate entrano nel registro delle viste.
    Siti e video passano tutti. I paper (ARX-02, ADR 0010) passano dal più recente, a giri, finché i
    promossi riempiono il tetto. Restituisce le promosse e i paper rimasti senza pre-filtro."""
    paper = sorted((c for c in nuove if c.tipo == "arxiv"), key=lambda c: c.pubblicata_il, reverse=True)
    altre = [c for c in nuove if c.tipo != "arxiv"]
    avanzamento.inizia_fase("pre-filtro", 0)  # il totale cresce a ogni giro: all'inizio non si sa quanti giri servono

    async def filtra_blocchi(notizie_: list[Candidata]) -> list[list[Candidata] | None]:
        blocchi = [notizie_[i : i + BLOCCO_PREFILTRO] for i in range(0, len(notizie_), BLOCCO_PREFILTRO)]
        avanzamento.totale += len(blocchi)
        return await in_parallelo(filtra(b) for b in blocchi)

    async def filtra_paper() -> tuple[list[Candidata], list[Candidata]]:
        promossi, resto = [], paper
        while resto and len(promossi) < tetto:
            giro = min(GIRO_PREFILTRO, -(-(tetto - len(promossi)) // BLOCCO_PREFILTRO)) * BLOCCO_PREFILTRO
            esiti = await filtra_blocchi(resto[:giro])
            resto = resto[giro:]
            promossi += [c for esito in esiti if esito for c in esito]
            if None in esiti:  # un blocco fallito: niente giri nuovi, il resto si riprende la volta dopo
                for c in resto:
                    m.di(c.tipo).errori += 1
                return promossi, []
        return promossi, resto

    async def filtra(blocco: list[Candidata]) -> list[Candidata] | None:
        try:
            risposta = await chiedi(
                prefiltro,
                sistema=sistema,
                messaggio=prompt.messaggio_prefiltro(blocco),
                schema=prompt.SCHEMA_PREFILTRO,
                modello=modello,
            )
        except ErroreBloccante:
            raise
        except ErroreLLM as errore:  # il blocco non si segna come visto: ci si riprova la volta dopo
            log.warning("Pre-filtro fallito per un blocco di %s notizie: %s", len(blocco), errore)
            for c in blocco:
                m.di(c.tipo).errori += 1
            return None
        finally:
            avanzamento.fatti += 1
        m.conta_token("prefiltro", risposta)

        def validi(chiave: str) -> set[int]:
            return {i for i in risposta.dati.get(chiave, []) if isinstance(i, int) and 0 <= i < len(blocco)}

        indici = validi("pertinenti")
        sponsorizzate = validi("sponsorizzate") - indici  # WEB-23, solo con l'esclusione attiva
        video = {n for n in sponsorizzate if blocco[n].tipo in ("video", "short")}
        indici, sponsorizzate = indici | video, sponsorizzate - video  # decisione 36: i video si valutano comunque
        scartate = [c for n, c in enumerate(blocco) if n not in indici]
        notizie.segna_viste(s, [c.url for c in scartate])
        s.commit()
        for n, c in enumerate(blocco):
            if n in sponsorizzate:
                m.escludi(c, "sponsorizzato o offerta")
            elif n not in indici:
                m.di(c.tipo).scartate_prefiltro += 1
        return [blocco[i] for i in sorted(indici)]

    esiti_altre, (promossi, non_prefiltrati) = await in_parallelo([filtra_blocchi(altre), filtra_paper()])
    return [c for esito in esiti_altre if esito for c in esito] + promossi, non_prefiltrati


def applica_tetto(
    s: Session, passate: list[Candidata], non_prefiltrati: list[Candidata], tetto: int, m: Metriche
) -> list[Candidata]:
    """Tetto arXiv (ARX-03): si elaborano i paper più recenti; gli altri, compresi quelli mai
    pre-filtrati (ARX-02), si considerano visti. Restituisce le notizie da valutare."""
    paper = sorted((c for c in passate if c.tipo == "arxiv"), key=lambda c: c.pubblicata_il, reverse=True)
    oltre = paper[tetto:] + non_prefiltrati
    passate = [c for c in passate if c.tipo != "arxiv"] + paper[:tetto]
    if oltre:
        m.di("arxiv").oltre_tetto = len(oltre)
    notizie.segna_viste(s, [c.url for c in oltre])
    s.commit()
    return passate
