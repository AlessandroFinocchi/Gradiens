"""Un'esecuzione: raccolta, pre-filtro, tetto, contenuto, valutazione, salvataggio, metriche (PRD sezione 5).

Gira dentro il processo del servizio, una sola alla volta (ESE-02). Ogni notizia si salva appena
valutata, così un'interruzione (spegnimento, quota esaurita) non perde il lavoro già fatto (ESE-12, LLM-06).
"""

import asyncio
import contextlib
import json
import logging
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from gradiens.dati import argomenti, esecuzioni, impostazioni, interessi, notizie, proposte
from gradiens.dati import siti as dati_siti
from gradiens.dati.modelli import Notizia, Pertinenza
from gradiens.esecuzione import prompt
from gradiens.fonti import Candidata, ContenutoAssente, NonAncoraDisponibile, arxiv, siti, youtube
from gradiens.llm import crea_provider
from gradiens.llm.base import ErroreLLM, Provider, QuotaEsaurita

log = logging.getLogger(__name__)

BLOCCO_PREFILTRO = 30  # notizie per chiamata di pre-filtro (ADR 0006)
BLOCCO_ARGOMENTI = 40  # notizie per chiamata del passo degli argomenti (ADR 0008)
MAX_CONTENUTO = 60_000  # caratteri (~15.000 token): oltre, la notizia è "contenuto parziale"
FONTE_DI_TIPO = {"arxiv": "arxiv", "video": "youtube", "short": "youtube", "sito": "siti"}


SPENTO = "Gradiens è stato spento durante l'esecuzione."


class GiaInCorso(Exception):
    """ESE-02: un'altra esecuzione è in corso."""


@dataclass
class Avanzamento:
    esecuzione_id: int
    fase: str = "raccolta"
    fatti: int = 0
    totale: int = 0


@dataclass
class Contatori:
    """ESE-11 per un tipo di fonte, per il resoconto (UI-03). `stati`: un elemento per sito, canale o
    arXiv; `problemi`: notizie senza contenuto (es. "trascrizione assente", YT-05); `notizie_escluse`:
    notizie scartate per WEB-23, con il motivo."""

    raccolta_s: float = 0  # le fonti di un tipo si leggono in parallelo: conta la più lenta
    esaminate: int = 0
    scartate_prefiltro: int = 0
    oltre_tetto: int = 0
    escluse: int = 0  # es. articoli a pagamento con l'esclusione attiva (WEB-23)
    senza_contenuto: int = 0
    scartate_valutazione: int = 0
    mostrate: int = 0
    errori: int = 0
    stati: list[dict] = field(default_factory=list)
    problemi: list[dict] = field(default_factory=list)
    notizie_escluse: list[dict] = field(default_factory=list)


@dataclass
class Metriche:
    fonti: dict[str, Contatori] = field(default_factory=dict)
    token: dict = field(default_factory=lambda: {r: {"ingresso": 0, "uscita": 0} for r in ("prefiltro", "elaborazione")})

    def escludi(self, c: Candidata, motivo: str) -> None:
        conta = self.di(c.tipo)
        conta.escluse += 1
        conta.notizie_escluse.append({"fonte": c.fonte, "titolo": c.titolo, "url": c.url, "motivo": motivo})

    def di(self, tipo: str) -> Contatori:
        """Contatori della fonte di un tipo di notizia (video e short sono entrambi "youtube")."""
        return self.fonti.setdefault(FONTE_DI_TIPO.get(tipo, tipo), Contatori())

    def conta_token(self, ruolo: str, risposta) -> None:
        self.token[ruolo]["ingresso"] += risposta.token_ingresso
        self.token[ruolo]["uscita"] += risposta.token_uscita


class Esecutore:
    def __init__(
        self,
        sessioni: sessionmaker[Session],
        fabbrica_provider: Callable[[str], Provider] = crea_provider,
        fonti: dict | None = None,
    ):
        self._sessioni = sessioni
        self._fabbrica_provider = fabbrica_provider
        self._fonti = fonti or {"arxiv": arxiv, "youtube": youtube, "siti": siti}  # moduli con raccogli (e completa)
        self.avanzamento: Avanzamento | None = None
        self._compito: asyncio.Task | None = None
        self.al_termine: Callable[[int], Awaitable[None]] | None = None  # es. messaggio Telegram (TG-03)

    def avvia(self, avviata_da: str) -> int:
        """Crea l'esecuzione e la fa partire in sottofondo. Nessun `await` prima del controllo:
        nel ciclo asyncio controllo e prenotazione sono quindi atomici."""
        if self.avanzamento is not None:
            raise GiaInCorso("Esecuzione già in corso.")
        with self._sessioni() as s:
            id = esecuzioni.inizia(s, avviata_da).id
        self.avanzamento = Avanzamento(esecuzione_id=id)
        self._compito = asyncio.create_task(self._esegui(id))
        return id

    async def attendi(self) -> None:
        if self._compito is not None:
            await self._compito

    async def ferma(self) -> None:
        """Allo spegnimento: interrompe l'esecuzione in corso e la registra come interrotta (ESE-12)."""
        if self._compito is not None and not self._compito.done():
            self._compito.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._compito

    async def _esegui(self, id: int) -> None:
        inizio = time.monotonic()
        metriche = Metriche()
        stato, motivo = "completata", None
        try:
            with self._sessioni() as s:
                await self._pipeline(s, metriche)
        except QuotaEsaurita as errore:
            stato, motivo = "interrotta", str(errore)
        except asyncio.CancelledError:
            stato, motivo = "interrotta", SPENTO
            raise
        except Exception as errore:  # l'esecuzione fallisce, ma va sempre chiusa con il suo motivo (ESE-13)
            log.exception("Esecuzione %s fallita", id)
            stato, motivo = "fallita", str(errore) or type(errore).__name__
        finally:
            dati = {
                "durata_s": round(time.monotonic() - inizio, 1),
                "fonti": {nome: asdict(c) for nome, c in metriche.fonti.items()},
                "token": metriche.token,
            }
            with self._sessioni() as s:
                esecuzioni.termina(s, id, stato, dati, motivo)
            self.avanzamento = None
            log.info("Esecuzione %s %s %s", id, stato, motivo or "")
            if self.al_termine is not None and motivo != SPENTO:  # allo spegnimento non si manda niente
                await self.al_termine(id)

    async def _raccogli(self, client: httpx.AsyncClient, s: Session, dal, m: Metriche) -> list[Candidata]:
        """Tutte le fonti in parallelo: una fonte irraggiungibile non ferma le altre."""
        compiti = []  # (tipo, nome per il resoconto, coroutine)
        if categorie := impostazioni.categorie_arxiv(s):
            compiti.append(("arxiv", "arXiv", self._fonti["arxiv"].raccogli(client, categorie, dal)))
        for canale in impostazioni.canali_youtube(s):
            compiti.append(("video", canale.nome,
                            self._fonti["youtube"].raccogli(client, youtube.Canale(canale.id, canale.nome), dal)))
        for sito in dati_siti.elenca(s):
            compiti.append(("sito", sito.url, self._raccogli_sito(client, s, sito.id, sito.profilo, dal, m)))
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
        for (tipo, nome, _), risultato in zip(compiti, risultati):
            if isinstance(risultato, Exception):
                log.warning("Raccolta da %s fallita: %s", nome, risultato)
                m.di(tipo).errori += 1
                m.di(tipo).stati.append({"fonte": nome, "stato": "non raggiungibile", "dettaglio": str(risultato)})
            elif isinstance(risultato, BaseException):
                raise risultato
            else:
                trovate += risultato
                if tipo != "sito":  # lo stato di un sito lo registra `_raccogli_sito`
                    m.di(tipo).stati.append({"fonte": nome, "stato": "ok"})
        if all(isinstance(r, BaseException) for r in risultati):
            raise RuntimeError("Nessuna fonte raggiungibile.")
        return trovate

    async def _raccogli_sito(self, client: httpx.AsyncClient, s: Session, id: int, profilo_json: str, dal,
                             m: Metriche) -> list[Candidata]:
        """Un sito: raccolta, stato (WEB-26), guasti consecutivi e rigenerazione del profilo dopo 3 (WEB-24)."""
        fonte = self._fonti["siti"]
        profilo = siti.Profilo.da_dict(json.loads(profilo_json))
        try:
            esito = await fonte.raccogli(client, profilo, dal)
        except Exception as errore:  # un sito con un errore imprevisto non ferma gli altri
            log.warning("Raccolta da %s fallita: %s", profilo.url, errore)
            esito = siti.EsitoSito([], "errore di lettura", True, str(errore))
        guasti = dati_siti.registra_esito(s, id, esito.stato, esito.dettaglio, esito.guasto)
        conta = m.di("sito")
        if esito.guasto:
            conta.errori += 1
        stato = {"fonte": profilo.dominio, "stato": esito.stato, "dettaglio": esito.dettaglio}
        conta.stati.append(stato)
        if guasti >= dati_siti.GUASTI_PER_RIGENERARE:
            try:
                nuovo = await fonte.rigenera(client, profilo)
            except Exception as errore:
                log.warning("Rigenerazione del profilo di %s fallita: %s", profilo.url, errore)
            else:
                dati_siti.salva_rigenerato(s, id, nuovo.come_dict())
                stato.update(stato="profilo rigenerato",
                             dettaglio=f"{esito.dettaglio or esito.stato}. Dopo 3 guasti di fila il profilo è stato ricreato; le tue modifiche restano.")
        return esito.candidate

    async def _pipeline(self, s: Session, m: Metriche) -> None:
        if cancellate := notizie.cancella_scadute(s):  # ESE-09: all'inizio di ogni esecuzione
            log.info("%s notizie più vecchie di 7 giorni cancellate", cancellate)
        imp = impostazioni.leggi(s)
        elenco_interessi = interessi.elenca(s)
        if not elenco_interessi:
            raise ValueError("Serve almeno un interesse (Impostazioni).")
        prefiltro = self._fabbrica_provider(imp.provider_prefiltro)
        elaborazione = self._fabbrica_provider(imp.provider_elaborazione)
        for provider in (prefiltro, elaborazione):  # ACC-15: es. Claude Code non collegato, l'esecuzione non parte
            await provider.pronto()
        dal = notizie.adesso() - timedelta(days=imp.finestra_giorni)
        m.token["prefiltro"].update(provider=imp.provider_prefiltro, modello=imp.modello_prefiltro)
        m.token["elaborazione"].update(provider=imp.provider_elaborazione, modello=imp.modello_elaborazione)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Raccolta (ESE-03): solo la finestra, senza le notizie già viste (ESE-07) né i doppioni.
            trovate = await self._raccogli(client, s, dal, m)
            viste = notizie.gia_viste(s, [c.url for c in trovate])
            nuove = list({c.url: c for c in trovate if c.url not in viste}.values())
            for c in nuove:
                m.di(c.tipo).esaminate += 1
            # Notizie nuove per sito, canale o arXiv. Si riconoscono dal nome della fonte: due siti
            # dello stesso dominio (es. /blog e /news) mostrano il totale di entrambi.
            per_fonte = Counter((FONTE_DI_TIPO[c.tipo], "arXiv" if c.tipo == "arxiv" else c.fonte) for c in nuove)
            for nome, conta in m.fonti.items():
                for stato in conta.stati:
                    stato["nuove"] = per_fonte[(nome, stato["fonte"])]

            passate = await self._prefiltra(s, nuove, prefiltro, prompt.sistema_prefiltro(elenco_interessi, imp.escludi_sponsorizzati),
                                            imp.modello_prefiltro, m)

            # Tetto arXiv (ARX-03): si elaborano i paper più recenti; gli altri si considerano visti.
            paper = sorted((c for c in passate if c.tipo == "arxiv"), key=lambda c: c.pubblicata_il, reverse=True)
            oltre = paper[imp.tetto_arxiv:]
            passate = [c for c in passate if c.tipo != "arxiv"] + paper[:imp.tetto_arxiv]
            if paper:
                m.di("arxiv").oltre_tetto = len(oltre)
            notizie.segna_viste(s, [c.url for c in oltre])
            s.commit()

            # Contenuto e valutazione completa (ESE-05): ogni notizia si salva appena valutata.
            self._fase("valutazione", len(passate))
            sistema = prompt.sistema_valutazione(elenco_interessi)
            ids_validi = {i.id for i in elenco_interessi}

            async def elabora(c: Candidata) -> None:
                try:
                    c = await self._completa(client, c)
                    if imp.escludi_pagamento and c.stato and "paywall" in c.stato:  # WEB-23: niente quota sprecata
                        notizie.segna_viste(s, [c.url])
                        s.commit()
                        m.escludi(c, "a pagamento")
                        return
                    risposta = await elaborazione.chiedi(sistema=sistema, messaggio=prompt.messaggio_valutazione(c),
                                                         schema=prompt.SCHEMA_VALUTAZIONE,
                                                         modello=imp.modello_elaborazione)
                except QuotaEsaurita:
                    raise
                except ContenutoAssente as stato:  # YT-05: non diventa notizia, compare nel resoconto
                    notizie.segna_viste(s, [c.url])
                    s.commit()
                    m.di(c.tipo).senza_contenuto += 1
                    m.di(c.tipo).problemi.append({"fonte": c.fonte, "titolo": c.titolo, "url": c.url, "stato": str(stato)})
                    return
                except NonAncoraDisponibile:  # YT-04: si riprende alla prossima esecuzione
                    return
                except Exception as errore:  # rete o LLM: non si segna come vista, si riprova la volta dopo
                    log.warning("Elaborazione fallita per %s: %s", c.url, errore)
                    m.di(c.tipo).errori += 1
                    return
                finally:
                    self.avanzamento.fatti += 1
                m.conta_token("elaborazione", risposta)
                self._salva(s, c, risposta.dati, ids_validi, imp.soglia, m, self.avanzamento.esecuzione_id)

            await _tutti(elabora(c) for c in passate)
            await self._argomenti(s, elaborazione, imp.modello_elaborazione, m)
            await self._proposte(s, elaborazione, imp.modello_elaborazione, imp.soglia, m)

    async def _argomenti(self, s: Session, elaborazione: Provider, modello: str, m: Metriche) -> None:
        """ESE-08, ADR 0008: le notizie mostrate dall'esecuzione, a blocchi in fila, così ogni blocco
        vede gli argomenti creati dal precedente. Se Claude non risponde restano senza argomento."""
        mostrate = list(s.scalars(select(Notizia).where(Notizia.esecuzione_id == self.avanzamento.esecuzione_id)))
        blocchi = [mostrate[i:i + BLOCCO_ARGOMENTI] for i in range(0, len(mostrate), BLOCCO_ARGOMENTI)]
        self._fase("argomenti", len(blocchi))
        for blocco in blocchi:
            esistenti = argomenti.per_prompt(s)
            try:
                risposta = await elaborazione.chiedi(
                    sistema=prompt.sistema_argomenti(esistenti), messaggio=prompt.messaggio_argomenti(blocco),
                    schema=prompt.SCHEMA_ARGOMENTI, modello=modello)
            except QuotaEsaurita:
                raise
            except Exception as errore:  # un argomento mancante non fa fallire l'esecuzione (ADR 0008)
                log.warning("Passo degli argomenti non riuscito: %s", errore)
                return
            m.conta_token("elaborazione", risposta)
            # Un "nuovo" con il nome di un argomento esistente non deve creare un doppione.
            validi, nuovi = {a.id for a in esistenti}, {a.nome.casefold(): a for a in esistenti}
            for voce in risposta.dati.get("assegnazioni", []):  # dato esterno: si controlla tutto
                i = voce.get("notizia") if isinstance(voce, dict) else None
                if not isinstance(i, int) or not 0 <= i < len(blocco):
                    continue
                if voce.get("argomento") in validi:
                    blocco[i].argomento_id = voce["argomento"]
                elif isinstance(voce.get("nuovo"), str) and (nome := voce["nuovo"].strip()):
                    blocco[i].argomento = nuovi.get(nome.casefold()) or nuovi.setdefault(nome.casefold(), argomenti.crea(s, nome))
            s.commit()
            self.avanzamento.fatti += 1

    async def _proposte(self, s: Session, elaborazione: Provider, modello: str, soglia: int, m: Metriche) -> None:
        """INT-04, INT-06: proposte dai cuori nuovi. Se Claude non risponde si riprova alla prossima esecuzione."""
        compiti = [(prompt.sistema_raffinamento(i), prompt.messaggio_proposta(notizie_[:proposte.MASSIMO_NOTIZIE]),
                    prompt.SCHEMA_RAFFINAMENTO,
                    lambda dati, i=i, n=len(notizie_): proposte.registra_raffinamento(s, i, str(dati.get("raffinamento", "")), n))
                   for i, notizie_ in proposte.da_raffinare(s, soglia)]
        if cuori := proposte.per_interesse_nuovo(s):
            compiti.append((prompt.sistema_nuovo_interesse(interessi.elenca(s)),
                            prompt.messaggio_nuovo_interesse(cuori[:proposte.MASSIMO_NOTIZIE]), prompt.SCHEMA_NUOVO_INTERESSE,
                            lambda dati, n=len(cuori): proposte.registra_interesse(
                                s, str(dati.get("nome", "")), str(dati.get("descrizione", "")), n)))
        self._fase("proposte", len(compiti))
        for sistema, messaggio, schema, registra in compiti:
            try:
                risposta = await elaborazione.chiedi(sistema=sistema, schema=schema, modello=modello, messaggio=messaggio)
                registra(risposta.dati)
            except QuotaEsaurita:
                raise
            except Exception as errore:  # una proposta mancata non fa fallire l'esecuzione
                s.rollback()
                log.warning("Proposta non generata: %s", errore)
                continue
            m.conta_token("elaborazione", risposta)
            self.avanzamento.fatti += 1

    async def _prefiltra(self, s: Session, nuove: list[Candidata], prefiltro: Provider, sistema: str,
                         modello: str, m: Metriche) -> list[Candidata]:
        """Pre-filtro a blocchi (ESE-04, ARX-02); le notizie scartate entrano nel registro delle viste."""
        blocchi = [nuove[i:i + BLOCCO_PREFILTRO] for i in range(0, len(nuove), BLOCCO_PREFILTRO)]
        self._fase("pre-filtro", len(blocchi))

        async def filtra(blocco: list[Candidata]) -> list[Candidata]:
            try:
                risposta = await prefiltro.chiedi(sistema=sistema, messaggio=prompt.messaggio_prefiltro(blocco),
                                                  schema=prompt.SCHEMA_PREFILTRO, modello=modello)
            except QuotaEsaurita:
                raise
            except ErroreLLM as errore:  # il blocco non si segna come visto: ci si riprova la volta dopo
                log.warning("Pre-filtro fallito per un blocco di %s notizie: %s", len(blocco), errore)
                for c in blocco:
                    m.di(c.tipo).errori += 1
                return []
            finally:
                self.avanzamento.fatti += 1
            m.conta_token("prefiltro", risposta)
            def validi(chiave: str) -> set[int]:
                return {i for i in risposta.dati.get(chiave, []) if isinstance(i, int) and 0 <= i < len(blocco)}

            indici = validi("pertinenti")
            sponsorizzate = validi("sponsorizzate") - indici  # WEB-23, solo con l'esclusione attiva
            scartate = [c for n, c in enumerate(blocco) if n not in indici]
            notizie.segna_viste(s, [c.url for c in scartate])
            s.commit()
            for n, c in enumerate(blocco):
                if n in sponsorizzate:
                    m.escludi(c, "sponsorizzato o offerta")
                elif n not in indici:
                    m.di(c.tipo).scartate_prefiltro += 1
            return [blocco[i] for i in sorted(indici)]

        return [c for blocco in await _tutti(filtra(b) for b in blocchi) for c in blocco]

    async def _completa(self, client: httpx.AsyncClient, c: Candidata) -> Candidata:
        fonte = self._fonti.get(FONTE_DI_TIPO[c.tipo])
        if hasattr(fonte, "completa"):
            c = await fonte.completa(client, c)
        if len(c.contenuto) > MAX_CONTENUTO:  # es. trascrizione di un video di due ore
            c.contenuto, c.stato = c.contenuto[:MAX_CONTENUTO], c.stato or "contenuto parziale"
        return c

    def _fase(self, fase: str, totale: int) -> None:
        self.avanzamento.fase, self.avanzamento.fatti, self.avanzamento.totale = fase, 0, totale

    @staticmethod
    def _salva(s: Session, c: Candidata, dati: dict, ids_validi: set[int], soglia: int, m: Metriche,
               esecuzione_id: int) -> None:
        # La risposta dell'LLM è dato esterno: si tengono solo interessi esistenti e punteggi 0-100.
        punteggi: dict[int, int] = {}
        for p in dati.get("punteggi", []):
            interesse, valore = p.get("interesse"), p.get("pertinenza")
            if interesse in ids_validi and isinstance(valore, int):
                punteggi[interesse] = max(0, min(100, valore))
        notizie.segna_viste(s, [c.url])
        if not punteggi or max(punteggi.values()) < soglia:  # ESE-06
            m.di(c.tipo).scartate_valutazione += 1
            s.commit()
            return
        titolo_it = (dati.get("titolo_it") or "").strip()
        if not titolo_it.strip("\"'“”«» "):  # l'LLM a volte scrive la stringa vuota come '""'
            titolo_it = ""
        s.add(Notizia(
            tipo=c.tipo, url=c.url, fonte=c.fonte, titolo=c.titolo,
            titolo_it=titolo_it if titolo_it and titolo_it != c.titolo else None,
            sommario=c.sommario, riassunto=str(dati.get("riassunto", "")).strip(),
            pubblicata_il=c.pubblicata_il, data_incerta=c.data_incerta, scoperta_il=notizie.adesso(), stato=c.stato,
            esecuzione_id=esecuzione_id,
            pertinenze=[Pertinenza(interesse_id=i, punteggio=v) for i, v in punteggi.items() if v > 0],
        ))
        s.commit()
        m.di(c.tipo).mostrate += 1


async def _tutti(coroutine) -> list:
    """Esegue in parallelo; al primo errore ferma le altre (la sessione del database è condivisa).
    La quota esaurita esce come tale, non dentro un gruppo di eccezioni."""
    try:
        async with asyncio.TaskGroup() as gruppo:
            compiti = [gruppo.create_task(c) for c in coroutine]
    except* QuotaEsaurita as gruppo:
        raise gruppo.exceptions[0] from None
    return [c.result() for c in compiti]
