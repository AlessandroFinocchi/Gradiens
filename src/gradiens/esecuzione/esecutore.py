"""Un'esecuzione: raccolta, pre-filtro, tetto, contenuto, valutazione, salvataggio, metriche (PRD sezione 5).

Gira dentro il processo del servizio, una sola alla volta (ESE-02). Ogni notizia si salva appena
valutata, così un'interruzione (spegnimento, quota esaurita) non perde il lavoro già fatto (ESE-12, LLM-06).
"""

import asyncio
import contextlib
import logging
import math
import socket
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from datetime import timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from gradiens.dati import argomenti, esecuzioni, impostazioni, interessi, notizie, proposte
from gradiens.dati import siti as dati_siti
from gradiens.dati.esecuzioni import NESSUNA_RETE, SPENTO
from gradiens.dati.modelli import FONTE_DI_TIPO, Notizia, Pertinenza
from gradiens.esecuzione import prompt
from gradiens.esecuzione.chiamata import chiedi
from gradiens.esecuzione.metriche import Avanzamento, Metriche
from gradiens.esecuzione.parallelo import foglie, in_parallelo
from gradiens.esecuzione.prefiltro import applica_tetto, prefiltra
from gradiens.esecuzione.raccolta import raccogli
from gradiens.fonti import Candidata, ContenutoAssente, NonAncoraDisponibile, arxiv, siti, youtube
from gradiens.llm import crea_provider, nome_provider
from gradiens.llm.base import ErroreBloccante, ErroreLLM, Provider, QuotaEsaurita

log = logging.getLogger(__name__)

BLOCCO_ARGOMENTI = 40  # notizie per chiamata del passo degli argomenti (ADR 0008)
MAX_CONTENUTO = 60_000  # caratteri (~15.000 token): oltre, la notizia è "contenuto parziale"
TENTATIVI_CHIUSURA, PAUSA_CHIUSURA = 3, 0.5  # registrazione della fine con il database bloccato (S-06)


class GiaInCorso(Exception):
    """ESE-02: un'altra esecuzione è in corso."""


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
            stato, motivo = "fallita", "; ".join(dict.fromkeys(str(e) or type(e).__name__ for e in foglie(errore)))  # S-07
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
            trovate = await raccogli(client, s, self._fonti, dal, imp.finestra_giorni, m, coperture)
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

            passate, non_prefiltrati = await prefiltra(
                s, nuove, prefiltro, prompt.sistema_prefiltro(elenco_interessi, imp.escludi_sponsorizzati),
                imp.modello_prefiltro, imp.tetto_arxiv, m, self.avanzamento)
            passate = applica_tetto(s, passate, non_prefiltrati, imp.tetto_arxiv, m)

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

            await in_parallelo(elabora(c) for c in passate)
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

    async def _completa(self, client: httpx.AsyncClient, c: Candidata) -> Candidata:
        fonte = self._fonti.get(FONTE_DI_TIPO[c.tipo])
        if hasattr(fonte, "completa"):
            c = await fonte.completa(client, c)
        if len(c.contenuto) > MAX_CONTENUTO:  # es. trascrizione di un video di due ore
            c.contenuto, c.stato = c.contenuto[:MAX_CONTENUTO], c.stato or "contenuto parziale"
        return c

    def _fase(self, fase: str, totale: int) -> None:
        self.avanzamento.inizia_fase(fase, totale)

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
