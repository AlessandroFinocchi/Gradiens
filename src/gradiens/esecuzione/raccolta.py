"""Raccolta da tutte le fonti (ESE-03) e politica dei siti: stato, guasti, rigenerazione (WEB-24, WEB-26, ADR 0011)."""

import asyncio
import json
import logging
import time

import httpx
from sqlalchemy.orm import Session

from gradiens.dati import impostazioni, notizie
from gradiens.dati import siti as dati_siti
from gradiens.dati.modelli import Sito
from gradiens.esecuzione.metriche import Metriche
from gradiens.fonti import Candidata, siti, youtube

log = logging.getLogger("gradiens.esecuzione.esecutore")  # i messaggi restano quelli dell'esecutore nel log


async def raccogli(
    client: httpx.AsyncClient,
    s: Session,
    fonti: dict,
    dal,
    finestra_giorni: int,
    m: Metriche,
    coperture: dict[int, dati_siti.Copertura],
) -> list[Candidata]:
    """Tutte le fonti in parallelo: una fonte irraggiungibile non ferma le altre."""
    compiti = []  # (tipo, nome per il resoconto, coroutine)
    if categorie := impostazioni.categorie_arxiv(s):
        compiti.append(("arxiv", "arXiv", fonti["arxiv"].raccogli(client, categorie, dal)))
    for canale in impostazioni.canali_youtube(s):
        compiti.append(
            ("video", canale.nome, fonti["youtube"].raccogli(client, youtube.Canale(canale.id, canale.nome), dal))
        )
    for sito in dati_siti.elenca(s):
        compiti.append(("sito", sito.url, raccogli_sito(client, s, fonti, sito, dal, finestra_giorni, m, coperture)))
    if not compiti:
        raise ValueError("Serve almeno una fonte: un sito, un canale YouTube o una categoria arXiv (Impostazioni).")

    async def cronometra(tipo: str, coroutine):
        inizio = time.monotonic()
        try:
            return await coroutine
        finally:
            conta = m.di(tipo)
            conta.raccolta_s = max(conta.raccolta_s, round(time.monotonic() - inizio, 1))

    trovate: list[Candidata] = []
    risultati = await asyncio.gather(*(cronometra(t, c) for t, _, c in compiti), return_exceptions=True)
    for (tipo, nome, _), risultato in zip(compiti, risultati, strict=True):
        if isinstance(risultato, Exception):
            log.warning("Raccolta da %s fallita: %s", nome, risultato)
            m.di(tipo).errori += 1
            m.di(tipo).stati.append({"fonte": nome, "stato": "non raggiungibile", "dettaglio": str(risultato)})
        elif isinstance(risultato, BaseException):
            raise risultato
        else:
            trovate += risultato
            if tipo != "sito":  # lo stato di un sito lo registra `raccogli_sito`
                m.di(tipo).stati.append({"fonte": nome, "stato": "ok"})
    if all(isinstance(r, BaseException) for r in risultati):
        raise RuntimeError("Nessuna fonte raggiungibile.")
    return trovate


async def raccogli_sito(
    client: httpx.AsyncClient,
    s: Session,
    fonti: dict,
    sito: Sito,
    dal,
    finestra_giorni: int,
    m: Metriche,
    coperture: dict[int, dati_siti.Copertura],
) -> list[Candidata]:
    """Un sito: raccolta da "coperto fino a" (ADR 0011), stato (WEB-26), guasti consecutivi e rigenerazione
    del profilo dopo 3 (WEB-24). Lo stato si salva subito; "coperto fino a" solo a fine esecuzione."""
    fonte = fonti["siti"]
    id, profilo = sito.id, siti.Profilo.da_dict(json.loads(sito.profilo))
    ora, impronta = notizie.adesso(), dati_siti.impronta(finestra_giorni, sito.profilo)
    try:
        esito = await fonte.raccogli(
            client, profilo, dati_siti.partenza(sito, dal, finestra_giorni), inizio_finestra=dal
        )
    except Exception as errore:  # un sito con un errore imprevisto non ferma gli altri
        log.warning("Raccolta da %s fallita: %s", profilo.url, errore)
        esito = siti.EsitoSito([], "errore di lettura", True, str(errore))
    coperture[id] = dati_siti.Copertura(
        ora, None if esito.guasto else impronta, {c.url: c.pubblicata_il for c in esito.candidate}
    )
    guasti = dati_siti.registra_esito(s, id, esito.stato, esito.dettaglio, esito.guasto)
    conta = m.di("sito")
    if esito.guasto:
        conta.errori += 1
    stato = {"fonte": profilo.dominio, "stato": esito.stato, "dettaglio": esito.dettaglio}
    conta.stati.append(stato)
    if guasti % dati_siti.GUASTI_PER_RIGENERARE == 0 and guasti:  # al 3°, 6°, 9°… guasto di fila (WEB-24)
        try:
            nuovo = await fonte.rigenera(client, profilo)
        except Exception as errore:
            log.warning("Rigenerazione del profilo di %s fallita: %s", profilo.url, errore)
        else:
            if nuovo is None:  # decisione 21: profilo e guasti restano, così il sito resta tra gli avvisi della Home
                stato["dettaglio"] = (
                    f"{esito.dettaglio or esito.stato} {siti.PROFILO_TENUTO} Riprovo dopo altri 3 guasti di fila."
                )
                dati_siti.aggiorna_dettaglio(s, id, stato["dettaglio"])
                return esito.candidate
            dati_siti.salva_rigenerato(s, id, nuovo.come_dict())
            stato.update(
                stato="profilo rigenerato",
                dettaglio=f"{esito.dettaglio or esito.stato}. Dopo 3 guasti di fila il profilo è stato ricreato; "
                "le tue modifiche restano.",
            )
    return esito.candidate
