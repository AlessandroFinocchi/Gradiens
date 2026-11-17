"""Un'esecuzione: raccolta, pre-filtro, tetto, contenuto, valutazione, salvataggio, metriche (PRD sezione 5).

Gira dentro il processo del servizio, una sola alla volta (ESE-02). Ogni notizia si salva appena
valutata, così un'interruzione (spegnimento, quota esaurita) non perde il lavoro già fatto (ESE-12, LLM-06).
"""

import asyncio
import contextlib
import json
import logging
import math
import socket
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
from gradiens.dati.esecuzioni import NESSUNA_RETE, SPENTO
from gradiens.dati.modelli import FONTE_DI_TIPO, Notizia, Pertinenza, Sito
from gradiens.esecuzione import prompt
from gradiens.fonti import Candidata, ContenutoAssente, NonAncoraDisponibile, arxiv, siti, youtube
from gradiens.llm import crea_provider, nome_provider
from gradiens.llm.base import ErroreBloccante, ErroreLLM, Provider, QuotaEsaurita, Risposta

log = logging.getLogger(__name__)

BLOCCO_PREFILTRO = 30  # notizie per chiamata di pre-filtro (ADR 0006)
GIRO_PREFILTRO = 3  # blocchi di paper lanciati insieme in un giro del pre-filtro (ADR 0010)
BLOCCO_ARGOMENTI = 40  # notizie per chiamata del passo degli argomenti (ADR 0008)
MAX_CONTENUTO = 60_000  # caratteri (~15.000 token): oltre, la notizia è "contenuto parziale"
TENTATIVI_CHIUSURA, PAUSA_CHIUSURA = 3, 0.5  # registrazione della fine con il database bloccato (S-06)


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
    versione_llm: dict | None = None  # decisione 45: provider, versione, precedente (se è cambiata), provata

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


# Secondi: all'accensione del PC la rete arriva di solito dopo pochi secondi, ma è arrivata anche dopo 5-10 minuti (I-4).
ATTESA_RETE, PAUSA_RETE = 900, 5
HOST_DI_PROVA = ("one.one.one.one", 443)  # un nome che si risolve in ogni rete collegata a internet


def rete_disponibile() -> bool:
    """C'è internet? Basta risolvere un nome: stamattina, all'accensione, falliva proprio la risoluzione dei nomi."""
    try:
        socket.getaddrinfo(*HOST_DI_PROVA)
    except OSError:
        return False
    return True


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
        coperture: dict[int, dati_siti.Copertura] = {}  # per sito, riempite dalla raccolta (ADR 0011)
        stato, motivo = "completata", None
        try:
            with self._sessioni() as s:
                await self._pipeline(s, metriche, coperture)
        except QuotaEsaurita as errore:
            stato, motivo = "interrotta", str(errore)
        except ErroreBloccante as errore:  # es. login rifiutato: niente notizia per notizia
            stato, motivo = "fallita", str(errore)
        except asyncio.CancelledError:
            stato, motivo = "interrotta", SPENTO
            raise
        except Exception as errore:  # l'esecuzione fallisce, ma va sempre chiusa con il suo motivo (ESE-13)
            log.exception("Esecuzione %s fallita", id)
            stato, motivo = "fallita", "; ".join(dict.fromkeys(str(e) or type(e).__name__ for e in _foglie(errore)))  # S-07
        finally:
            if coperture:  # a fine esecuzione, anche interrotta o fallita: le notizie senza esito trattengono il sito
                try:
                    with self._sessioni() as s:
                        dati_siti.salva_coperture(s, coperture)
                except Exception:  # resta "coperto fino a" di prima: la prossima raccolta rilegge di più, non perde
                    log.exception("Copertura dei siti non salvata")
            dati = {
                "durata_s": round(time.monotonic() - inizio, 1),
                "fonti": {nome: asdict(c) for nome, c in metriche.fonti.items()},
                "token": metriche.token,
            }
            if metriche.versione_llm:
                dati["versione_llm"] = metriche.versione_llm
            registrata = await self._termina(id, stato, dati, motivo)
            log.info("Esecuzione %s %s %s", id, stato, motivo or "")
            if registrata and self.al_termine is not None and motivo != SPENTO:  # allo spegnimento non si manda niente
                await self.al_termine(id)

    async def _termina(self, id: int, stato: str, dati: dict, motivo: str | None) -> bool:
        """Registra la fine; con il database bloccato (S-06) si riprova. Comunque vada, l'esecuzione non
        resta "in corso" in memoria (S-08): altrimenti ogni nuovo avvio darebbe GiaInCorso fino al riavvio."""
        try:
            for tentativo in range(1, TENTATIVI_CHIUSURA + 1):
                try:
                    with self._sessioni() as s:
                        esecuzioni.termina(s, id, stato, dati, motivo)
                    return True
                except Exception:
                    if tentativo == TENTATIVI_CHIUSURA:  # la riga resta "in corso" fino a `segna_interrotte`
                        log.exception("Esecuzione %s non registrata come %s", id, stato)
                        return False
                    await asyncio.sleep(PAUSA_CHIUSURA)
        finally:
            self.avanzamento = None

    async def _attendi_rete(self) -> None:
        """L'esecuzione recuperata all'accensione partiva prima della rete e falliva su tutte le fonti,
        segnando i siti come guasti. Si aspetta la rete per qualche minuto; poi l'esecuzione fallisce con il motivo."""
        fine = time.monotonic() + ATTESA_RETE
        while not await asyncio.to_thread(rete_disponibile):
            if time.monotonic() > fine:
                raise RuntimeError(NESSUNA_RETE)  # non conta per il recupero (`esecuzioni.avviate_dal`)
            self._fase("attesa della rete", 0)
            await asyncio.sleep(PAUSA_RETE)

    async def _raccogli(self, client: httpx.AsyncClient, s: Session, dal, finestra_giorni: int, m: Metriche,
                        coperture: dict[int, dati_siti.Copertura]) -> list[Candidata]:
        """Tutte le fonti in parallelo: una fonte irraggiungibile non ferma le altre."""
        compiti = []  # (tipo, nome per il resoconto, coroutine)
        if categorie := impostazioni.categorie_arxiv(s):
            compiti.append(("arxiv", "arXiv", self._fonti["arxiv"].raccogli(client, categorie, dal)))
        for canale in impostazioni.canali_youtube(s):
            compiti.append(("video", canale.nome,
                            self._fonti["youtube"].raccogli(client, youtube.Canale(canale.id, canale.nome), dal)))
        for sito in dati_siti.elenca(s):
            compiti.append(("sito", sito.url, self._raccogli_sito(client, s, sito, dal, finestra_giorni, m, coperture)))
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
                if tipo != "sito":  # lo stato di un sito lo registra `_raccogli_sito`
                    m.di(tipo).stati.append({"fonte": nome, "stato": "ok"})
        if all(isinstance(r, BaseException) for r in risultati):
            raise RuntimeError("Nessuna fonte raggiungibile.")
        return trovate

    async def _raccogli_sito(self, client: httpx.AsyncClient, s: Session, sito: Sito, dal, finestra_giorni: int,
                             m: Metriche, coperture: dict[int, dati_siti.Copertura]) -> list[Candidata]:
        """Un sito: raccolta da "coperto fino a" (ADR 0011), stato (WEB-26), guasti consecutivi e rigenerazione
        del profilo dopo 3 (WEB-24). Lo stato si salva subito; "coperto fino a" solo a fine esecuzione."""
        fonte = self._fonti["siti"]
        id, profilo = sito.id, siti.Profilo.da_dict(json.loads(sito.profilo))
        ora, impronta = notizie.adesso(), dati_siti.impronta(finestra_giorni, sito.profilo)
        try:
            esito = await fonte.raccogli(client, profilo, dati_siti.partenza(sito, dal, finestra_giorni), inizio_finestra=dal)
        except Exception as errore:  # un sito con un errore imprevisto non ferma gli altri
            log.warning("Raccolta da %s fallita: %s", profilo.url, errore)
            esito = siti.EsitoSito([], "errore di lettura", True, str(errore))
        coperture[id] = dati_siti.Copertura(ora, None if esito.guasto else impronta,
                                            {c.url: c.pubblicata_il for c in esito.candidate})
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
                    stato["dettaglio"] = f"{esito.dettaglio or esito.stato} {siti.PROFILO_TENUTO} Riprovo dopo altri 3 guasti di fila."
                    dati_siti.aggiorna_dettaglio(s, id, stato["dettaglio"])
                    return esito.candidate
                dati_siti.salva_rigenerato(s, id, nuovo.come_dict())
                stato.update(stato="profilo rigenerato",
                             dettaglio=f"{esito.dettaglio or esito.stato}. Dopo 3 guasti di fila il profilo è stato ricreato; le tue modifiche restano.")
        return esito.candidate

    async def _pipeline(self, s: Session, m: Metriche, coperture: dict[int, dati_siti.Copertura]) -> None:
        if cancellate := notizie.cancella_scadute(s):  # ESE-09: all'inizio di ogni esecuzione
            log.info("%s notizie più vecchie di 7 giorni cancellate", cancellate)
        imp = impostazioni.leggi(s)
        elenco_interessi = interessi.elenca(s)
        if not elenco_interessi:
            raise ValueError("Serve almeno un interesse (Impostazioni).")
        prefiltro = self._fabbrica_provider(imp.provider_prefiltro)
        elaborazione = self._fabbrica_provider(imp.provider_elaborazione)
        versioni = []
        for provider, modello in ((prefiltro, imp.modello_prefiltro), (elaborazione, imp.modello_elaborazione)):
            versioni.append((provider, modello, await provider.pronto()))  # ACC-15: es. Claude Code non collegato
        await self._attendi_rete()
        if con_versione := next((v for v in versioni if v[2]), None):
            await self._prova_se_cambiato(s, m, *con_versione, prompt.sistema_prefiltro(elenco_interessi, imp.escludi_sponsorizzati))
        dal = notizie.adesso() - timedelta(days=imp.finestra_giorni)
        m.token["prefiltro"].update(provider=imp.provider_prefiltro, modello=imp.modello_prefiltro)
        m.token["elaborazione"].update(provider=imp.provider_elaborazione, modello=imp.modello_elaborazione)

        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Raccolta (ESE-03): solo la finestra, senza le notizie già viste (ESE-07) né i doppioni.
            trovate = await self._raccogli(client, s, dal, imp.finestra_giorni, m, coperture)
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

            passate, non_prefiltrati = await self._prefiltra(
                s, nuove, prefiltro, prompt.sistema_prefiltro(elenco_interessi, imp.escludi_sponsorizzati),
                imp.modello_prefiltro, imp.tetto_arxiv, m)

            # Tetto arXiv (ARX-03): si elaborano i paper più recenti; gli altri, compresi quelli mai
            # pre-filtrati (ARX-02), si considerano visti.
            paper = sorted((c for c in passate if c.tipo == "arxiv"), key=lambda c: c.pubblicata_il, reverse=True)
            oltre = paper[imp.tetto_arxiv:] + non_prefiltrati
            passate = [c for c in passate if c.tipo != "arxiv"] + paper[:imp.tetto_arxiv]
            if oltre:
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
                    risposta = await chiedi(elaborazione, sistema=sistema, messaggio=prompt.messaggio_valutazione(c),
                                            schema=prompt.SCHEMA_VALUTAZIONE, modello=imp.modello_elaborazione)
                except ErroreBloccante:
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

    async def _prova_se_cambiato(self, s: Session, m: Metriche, provider: Provider, modello: str, versione: str,
                                 sistema: str) -> None:
        """Decisione 45: se la versione del provider (es. Claude Code, che si aggiorna da solo) non è quella già
        provata, una chiamata breve con lo schema del pre-filtro prima di usarlo. Se fallisce l'esecuzione si
        ferma, e la prova si ripete alla prossima."""
        precedente = esecuzioni.versione_provata(s, provider.nome)
        m.versione_llm = {"provider": provider.nome, "versione": versione,
                          "precedente": precedente if versione != precedente else None, "provata": versione == precedente}
        if versione == precedente:
            return
        log.info("%s passato da %s a %s: prova di funzionamento", provider.nome, precedente, versione)
        self._fase(f"prova di {nome_provider(provider.nome)}", 0)
        try:
            risposta = await chiedi(provider, sistema=sistema, messaggio=prompt.messaggio_prefiltro([]),
                                    schema=prompt.SCHEMA_PREFILTRO, modello=modello)
            if risposta.token_ingresso <= 0:
                raise ErroreLLM("la risposta non dice quanti token ha usato.")
        except QuotaEsaurita:
            raise
        except ErroreLLM as errore:
            raise ErroreBloccante(f"{nome_provider(provider.nome)} {versione}: la prova di funzionamento non è riuscita, "
                                  f"esecuzione fermata. {errore}") from errore
        m.conta_token("prefiltro", risposta)
        m.versione_llm["provata"] = True

    async def _argomenti(self, s: Session, elaborazione: Provider, modello: str, m: Metriche) -> None:
        """ESE-08, ADR 0008: le notizie mostrate dall'esecuzione, a blocchi in fila, così ogni blocco
        vede gli argomenti creati dal precedente. Se Claude non risponde restano senza argomento."""
        mostrate = list(s.scalars(select(Notizia).where(Notizia.esecuzione_id == self.avanzamento.esecuzione_id)))
        blocchi = [mostrate[i:i + BLOCCO_ARGOMENTI] for i in range(0, len(mostrate), BLOCCO_ARGOMENTI)]
        self._fase("argomenti", len(blocchi))
        for blocco in blocchi:
            esistenti = argomenti.per_prompt(s)
            try:
                risposta = await chiedi(
                    elaborazione, sistema=prompt.sistema_argomenti(esistenti), messaggio=prompt.messaggio_argomenti(blocco),
                    schema=prompt.SCHEMA_ARGOMENTI, modello=modello)
            except ErroreBloccante:
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
                    lambda dati, i=i, n=len(notizie_): proposte.registra_raffinamento(s, i, str(dati.get("raffinamento", "")), n))  # noqa: B008 (valori fissati alla creazione della lambda)
                   for i, notizie_ in proposte.da_raffinare(s, soglia)]
        if cuori := proposte.per_interesse_nuovo(s):
            compiti.append((prompt.sistema_nuovo_interesse(interessi.elenca(s)),
                            prompt.messaggio_nuovo_interesse(cuori[:proposte.MASSIMO_NOTIZIE]), prompt.SCHEMA_NUOVO_INTERESSE,
                            lambda dati, n=len(cuori): proposte.registra_interesse(  # noqa: B008 (valore fissato alla creazione della lambda)
                                s, str(dati.get("nome", "")), str(dati.get("descrizione", "")), n)))
        self._fase("proposte", len(compiti))
        for sistema, messaggio, schema, registra in compiti:
            try:
                risposta = await chiedi(elaborazione, sistema=sistema, schema=schema, modello=modello, messaggio=messaggio)
                registra(risposta.dati)
            except ErroreBloccante:
                raise
            except Exception as errore:  # una proposta mancata non fa fallire l'esecuzione
                s.rollback()
                log.warning("Proposta non generata: %s", errore)
                continue
            m.conta_token("elaborazione", risposta)
            self.avanzamento.fatti += 1

    async def _prefiltra(self, s: Session, nuove: list[Candidata], prefiltro: Provider, sistema: str,
                         modello: str, tetto: int, m: Metriche) -> tuple[list[Candidata], list[Candidata]]:
        """Pre-filtro a blocchi (ESE-04); le notizie scartate entrano nel registro delle viste.
        Siti e video passano tutti. I paper (ARX-02, ADR 0010) passano dal più recente, a giri, finché i
        promossi riempiono il tetto. Restituisce le promosse e i paper rimasti senza pre-filtro."""
        paper = sorted((c for c in nuove if c.tipo == "arxiv"), key=lambda c: c.pubblicata_il, reverse=True)
        altre = [c for c in nuove if c.tipo != "arxiv"]
        self._fase("pre-filtro", 0)  # il totale cresce a ogni giro: all'inizio non si sa quanti giri servono

        async def filtra_blocchi(notizie_: list[Candidata]) -> list[list[Candidata] | None]:
            blocchi = [notizie_[i:i + BLOCCO_PREFILTRO] for i in range(0, len(notizie_), BLOCCO_PREFILTRO)]
            self.avanzamento.totale += len(blocchi)
            return await _tutti(filtra(b) for b in blocchi)

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
                risposta = await chiedi(prefiltro, sistema=sistema, messaggio=prompt.messaggio_prefiltro(blocco),
                                        schema=prompt.SCHEMA_PREFILTRO, modello=modello)
            except ErroreBloccante:
                raise
            except ErroreLLM as errore:  # il blocco non si segna come visto: ci si riprova la volta dopo
                log.warning("Pre-filtro fallito per un blocco di %s notizie: %s", len(blocco), errore)
                for c in blocco:
                    m.di(c.tipo).errori += 1
                return None
            finally:
                self.avanzamento.fatti += 1
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

        esiti_altre, (promossi, non_prefiltrati) = await _tutti([filtra_blocchi(altre), filtra_paper()])
        return [c for esito in esiti_altre if esito for c in esito] + promossi, non_prefiltrati

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
            if interesse in ids_validi and isinstance(valore, (int, float)) and math.isfinite(valore):
                punteggi[interesse] = max(0, min(100, round(valore)))  # 85.5 si arrotonda (scheda 4 b)
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
    Un errore bloccante (quota esaurita, login rifiutato) esce come tale anche insieme ad altri errori (S-02);
    un errore solo esce da solo."""
    try:
        async with asyncio.TaskGroup() as gruppo:
            compiti = [gruppo.create_task(c) for c in coroutine]
    except ExceptionGroup as gruppo:
        errori = _foglie(gruppo)
        bloccanti = [e for e in errori if isinstance(e, ErroreBloccante)]
        if bloccanti or len(errori) == 1:
            raise (bloccanti or errori)[0] from None
        raise
    return [c.result() for c in compiti]


async def chiedi(provider: Provider, *, sistema: str, messaggio: str, schema: dict, modello: str) -> Risposta:
    """Chiama il provider e controlla la forma della risposta, uguale per ogni provider (ADR 0006, S-05):
    una forma inattesa è un ErroreLLM, quindi il blocco o la notizia si riprova invece di perdersi."""
    risposta = await provider.chiedi(sistema=sistema, messaggio=messaggio, schema=schema, modello=modello)
    _controlla_forma(risposta.dati, schema, "risposta")
    return risposta


SEMPLICI = {"string": str, "integer": (int, float)}  # un 85.5 si arrotonda dopo


def _controlla_forma(dati, schema: dict, dove: str) -> None:
    """Severo su chiavi obbligatorie, contenitori (oggetti e liste) e tipo dei campi semplici, tollerante sui
    valori: si ripuliscono dopo, e un controllo severo farebbe ripetere la valutazione a ogni esecuzione (S-36).
    Le liste di numeri (es. `pertinenti`) si ripuliscono voce per voce, quindi le loro voci non si controllano."""
    tipo = schema.get("type")
    if tipo == "object":
        if not isinstance(dati, dict):
            raise ErroreLLM(f"Risposta dell'LLM di forma inattesa: «{dove}» non è un oggetto.")
        for chiave in schema.get("required", []):
            if dati.get(chiave) is None:
                raise ErroreLLM(f"Risposta dell'LLM di forma inattesa: manca «{chiave}».")
        for chiave, sotto in schema.get("properties", {}).items():
            if chiave not in dati:
                continue
            semplice = SEMPLICI.get(sotto.get("type"))
            if semplice and dati[chiave] is not None and not isinstance(dati[chiave], semplice):
                raise ErroreLLM(f"Risposta dell'LLM di forma inattesa: «{chiave}» non è del tipo atteso.")
            _controlla_forma(dati[chiave], sotto, chiave)
    elif tipo == "array":
        if not isinstance(dati, list):
            raise ErroreLLM(f"Risposta dell'LLM di forma inattesa: «{dove}» non è una lista.")
        for voce in dati:
            _controlla_forma(voce, schema.get("items", {}), dove)


def _foglie(errore: BaseException) -> list[BaseException]:
    """Gli errori veri dentro un gruppo di eccezioni, anche annidato."""
    if isinstance(errore, BaseExceptionGroup):
        return [f for e in errore.exceptions for f in _foglie(e)]
    return [errore]
