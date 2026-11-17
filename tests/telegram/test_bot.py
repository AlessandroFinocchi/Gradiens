import asyncio
import os
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from telegram import InlineKeyboardMarkup

from gradiens.app.configurazione import salva_segreto
from gradiens.dati import esecuzioni, impostazioni, interessi
from gradiens.dati.modelli import Notizia, Pertinenza
from gradiens.dati.notizie import adesso
from gradiens.esecuzione.esecutore import GiaInCorso
from gradiens.telegram import bot as telegram
from gradiens.telegram import messaggi

HTMX = {"HX-Request": "true"}
TOKEN = "123456789:" + "A" * 35
CHAT = 4242


class Risposte:
    """Finto `effective_message`: registra i testi delle risposte."""

    def __init__(self):
        self.testi = []

    async def reply_text(self, testo, **_):
        self.testi.append(testo)


class EsecutoreFinto:
    avanzamento = None

    def __init__(self, occupato=False):
        self.occupato, self.avviate = occupato, []

    def avvia(self, da):
        if self.occupato:
            raise GiaInCorso("Esecuzione già in corso.")
        self.avviate.append(da)


@pytest.fixture
def ambiente(client):
    """Un'esecuzione conclusa con 4 notizie: 3 siti (uno con un titolo pericoloso) e un video; YouTube e arXiv."""
    with client.app.state.sessioni() as s:
        a = interessi.aggiungi(s, "Sicurezza", "attacchi")
        e = esecuzioni.inizia(s, "programmazione")
        for n, (tipo, titolo, punteggio) in enumerate([("sito", "Patch <urgente>", 95), ("sito", "Secondo", 80),
                                                        ("sito", "Terzo", 70), ("sito", "Quarto", 65), ("video", "Video", 90)]):
            s.add(Notizia(tipo=tipo, url=f"https://e.org/{n}", fonte="e.org", titolo=titolo, riassunto="Prima frase. Seconda frase. Terza frase.",
                          pubblicata_il=adesso() - timedelta(hours=1), scoperta_il=adesso(), esecuzione_id=e.id,
                          pertinenze=[Pertinenza(interesse_id=a.id, punteggio=punteggio)]))
        s.commit()
        esecuzioni.termina(s, e.id, "completata", {"durata_s": 75, "fonti": {"siti": {"esaminate": 10, "mostrate": 4, "errori": 1}},
                                                   "token": {"prefiltro": {"ingresso": 1500, "uscita": 500}}})
        impostazioni.leggi(s).telegram_chat_id = CHAT
        s.commit()
    client.app.state.conf.telegram_token = "presente"  # per problema(): il bot risulta configurato
    return client, e.id


def bot_di(client, esecutore=None):
    b = telegram.BotGradiens(client.app.state.conf, client.app.state.sessioni, esecutore or EsecutoreFinto(), lambda: None)
    inviati = []

    async def send_message(chat, testo, **opzioni):
        inviati.append((chat, testo, opzioni.get("reply_markup")))

    b._app = SimpleNamespace(bot=SimpleNamespace(send_message=send_message))
    return b, inviati


def aggiornamento(chat=CHAT):
    return SimpleNamespace(effective_message=Risposte(), effective_chat=SimpleNamespace(id=chat))


def test_messaggio_di_fine_esecuzione(ambiente):
    client, id = ambiente
    b, inviati = bot_di(client)
    asyncio.run(b.invia_esecuzione(id))
    [(chat, testo, tastiera)] = inviati
    assert chat == CHAT
    assert "Patch &lt;urgente&gt;" in testo and "<urgente>" not in testo  # testo delle fonti escapato
    assert "1. " in testo and "3. " in testo and "Quarto" not in testo  # al massimo 3 per fonte (TG-03)
    assert "Prima frase. Seconda frase." in testo and "Terza" not in testo  # una o due frasi
    assert testo.count("nessuna notizia nuova") == 1  # arXiv (TG-04); YouTube ha il video
    assert "10 esaminate · 4 mostrate · 1 min 15 s · 1 errore · 2 mila token" in testo
    assert [r[0].text for r in tastiera.inline_keyboard][0].startswith("🤍 1. Patch")  # TG-09
    assert len(tastiera.inline_keyboard) == 4


def test_comandi(ambiente):
    client, _ = ambiente
    esecutore = EsecutoreFinto()
    b, _ = bot_di(client, esecutore)
    for gestore, attesa in [(b._aggiorna, "Esecuzione avviata"), (b._stato, "Ultima esecuzione completata"),
                            (b._pausa, "Programmazione in pausa"), (b._aiuto, "/aggiorna")]:
        u = aggiornamento()
        asyncio.run(gestore(u, None))
        assert attesa in u.effective_message.testi[0]
    assert esecutore.avviate == ["telegram"]
    with client.app.state.sessioni() as s:
        assert impostazioni.leggi(s).programmazione_in_pausa  # TG-10
    u = aggiornamento()
    asyncio.run(b._riprendi(u, None))
    occupato, _ = bot_di(client, EsecutoreFinto(occupato=True))
    u = aggiornamento()
    asyncio.run(occupato._aggiorna(u, None))
    assert u.effective_message.testi == ["Esecuzione già in corso."]  # TG-05


def test_cuore_da_telegram(ambiente):
    client, id = ambiente
    b, inviati = bot_di(client)
    asyncio.run(b.invia_esecuzione(id))
    tastiera: InlineKeyboardMarkup = inviati[0][2]
    risposte, modificate = [], []

    def domanda(dati, chat=CHAT):
        async def answer(testo=None, **_):
            risposte.append(testo)

        async def edit(markup):
            modificate.append(markup)
        return SimpleNamespace(callback_query=SimpleNamespace(
            data=dati, answer=answer, edit_message_reply_markup=edit,
            message=SimpleNamespace(chat=SimpleNamespace(id=chat), reply_markup=tastiera)))

    primo = tastiera.inline_keyboard[0][0].callback_data
    asyncio.run(b._cuore(domanda(primo), None))
    assert risposte[-1].startswith("Cuore messo") and modificate[-1].inline_keyboard[0][0].text.startswith("❤️ 1.")
    asyncio.run(b._cuore(domanda(primo, chat=999), None))  # altra chat: ignorata (TG-02)
    assert len(modificate) == 1
    asyncio.run(b._cuore(domanda("cuore:99999"), None))
    assert risposte[-1] == "Notizia non più disponibile."


def test_ultima_senza_esecuzioni(client):
    b, _ = bot_di(client)
    u = aggiornamento()
    asyncio.run(b._ultima(u, None))
    assert u.effective_message.testi == ["Nessuna esecuzione ancora."]  # TG-08


def test_segreto_nel_file_env(conf):
    conf.file_env.write_text("GRADIENS_PORTA=9000\nGRADIENS_TELEGRAM_TOKEN=vecchio\n", encoding="utf-8")
    salva_segreto(conf, "telegram_token", TOKEN)
    assert conf.file_env.read_text(encoding="utf-8") == f"GRADIENS_PORTA=9000\nGRADIENS_TELEGRAM_TOKEN={TOKEN}\n"
    assert conf.telegram_token.get_secret_value() == TOKEN and TOKEN not in repr(conf)
    with pytest.raises(ValueError):
        salva_segreto(conf, "telegram_token", "x\nGRADIENS_HOST=0.0.0.0")
    if os.name != "nt":  # su Windows i permessi Unix non esistono
        assert conf.file_env.stat().st_mode & 0o777 == 0o600


def test_tutorial_dalle_impostazioni(client, monkeypatch):
    chiamate = []

    async def verifica(token):
        if token != TOKEN:
            raise telegram.ErroreTelegram("Telegram rifiuta questo token.")
        return "mio_gradiens_bot"

    async def cerca(token):
        return CHAT, "Alessandro"

    async def collega(token, chat):
        chiamate.append(("collega", chat))

    async def avvia():
        chiamate.append(("avvia",))

    monkeypatch.setattr(telegram, "verifica_token", verifica)
    monkeypatch.setattr(telegram, "cerca_chat", cerca)
    monkeypatch.setattr(telegram, "collega", collega)
    monkeypatch.setattr(client.app.state.bot, "avvia", avvia)

    assert "Crea il bot con BotFather" in client.get("/impostazioni/telegram", headers=HTMX).text
    assert "rifiuta" in client.post("/impostazioni/telegram/token", data={"token": "sbagliato"}, headers=HTMX).text
    passo3 = client.post("/impostazioni/telegram/token", data={"token": TOKEN}, headers=HTMX).text
    assert "Token valido: bot @mio_gradiens_bot" in passo3 and "Cerca la chat" in passo3
    assert TOKEN in client.app.state.conf.file_env.read_text(encoding="utf-8")  # nel .env, non nel database
    trovata = client.post("/impostazioni/telegram/cerca", headers=HTMX).text
    assert "Chat trovata: Alessandro" in trovata
    collegato = client.post("/impostazioni/telegram/conferma", data={"chat_id": CHAT, "nome": "Alessandro"}, headers=HTMX).text
    assert "collegato" in collegato and "/aggiorna" in collegato and TOKEN not in collegato
    assert chiamate == [("collega", CHAT), ("avvia",)]
    with client.app.state.sessioni() as s:
        assert impostazioni.leggi(s).telegram_chat_id == CHAT


def test_gli_errori_di_telegram_non_mostrano_il_token(monkeypatch):
    from telegram.error import InvalidToken

    class BotRifiutato:
        def __init__(self, token):
            self.token = token

        async def __aenter__(self):
            raise InvalidToken(f"The token `{self.token}` was rejected by the server.")

        async def __aexit__(self, *_):
            pass

    monkeypatch.setattr(telegram, "Bot", BotRifiutato)
    for chiamata in (telegram.verifica_token(TOKEN), telegram.cerca_chat(TOKEN), telegram.collega(TOKEN, CHAT)):
        with pytest.raises(telegram.ErroreTelegram) as errore:
            asyncio.run(chiamata)
        assert TOKEN not in str(errore.value) and str(errore.value) == telegram.RIFIUTATO



def test_senza_rete_all_accensione_riprova_presto_e_poi_piu_di_rado(monkeypatch):
    # PC appena acceso: la rete arriva dopo qualche tentativo. Prima si riprovava solo dopo un minuto.
    bot = telegram.BotGradiens(SimpleNamespace(), None, None, lambda: None)
    attese, tentativi = [], []

    async def avvia():
        tentativi.append(1)
        if len(tentativi) == 4:
            bot._app = "in ascolto"

    async def dorme(secondi):
        attese.append(secondi)
        if len(attese) > 6:
            raise asyncio.CancelledError

    monkeypatch.setattr(bot, "_avvia", avvia)
    monkeypatch.setattr(telegram.asyncio, "sleep", dorme)
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(bot.gira())
    assert attese[:5] == [5, 10, 20, 40, 5] and len(tentativi) == 4  # collegato: niente altri tentativi


def test_messaggio_di_prova_prova_prima_a_ricollegare(monkeypatch):
    bot = telegram.BotGradiens(SimpleNamespace(), None, None, lambda: None)
    bot.errore = "Telegram non raggiungibile, riprovo da solo: rete assente"

    async def avvia():
        bot.errore = None
        bot._app = SimpleNamespace(bot=SimpleNamespace(send_message=inviato))

    async def inviato(chat, testo):
        inviati.append(testo)

    inviati = []
    monkeypatch.setattr(bot, "_avvia", avvia)
    monkeypatch.setattr(bot, "_chat", lambda: CHAT)
    asyncio.run(bot.invia_prova())
    assert inviati and "funziona" in inviati[0]


def test_avviso_del_login_in_fondo_al_messaggio_di_fine_esecuzione(ambiente, monkeypatch):
    client, id = ambiente
    monkeypatch.setattr(telegram.claude_code, "avviso_login", lambda: "Il login di Claude Code scade il 10/11: rifallo <subito>")
    b, inviati = bot_di(client)
    asyncio.run(b.invia_esecuzione(id))
    assert inviati[0][1].endswith("⚠️ Il login di Claude Code scade il 10/11: rifallo &lt;subito&gt;")


def test_fonti_con_problemi_nel_messaggio_di_fine_esecuzione(ambiente):
    client, id = ambiente
    stati = [{"fonte": "redhotcyber.com", "stato": "nessuna strategia funzionante"}, {"fonte": "e.org", "stato": "ok"},
             {"fonte": "nature.com", "stato": "nessun articolo nuovo"}]
    stati += [{"fonte": f"Canale <{n}>", "stato": "non raggiungibile"} for n in range(6)]
    with client.app.state.sessioni() as s:
        esecuzioni.termina(s, id, "completata", {"durata_s": 75, "fonti": {"siti": {"esaminate": 10, "stati": stati}}})
    b, inviati = bot_di(client)
    asyncio.run(b.invia_esecuzione(id))
    testo = inviati[0][1]
    assert "⚠️ <b>Fonti con problemi</b>\n• redhotcyber.com: nessuna strategia funzionante" in testo
    assert "e.org" not in testo.split("Fonti con problemi")[1] and "nature.com" not in testo  # gli esiti normali no
    assert "• Canale &lt;3&gt;: non raggiungibile" in testo and "Canale &lt;4&gt;" not in testo  # al massimo 5
    assert "… e altre 2: le trovi nel resoconto, nella dashboard." in testo


class ApplicazioneFinta:
    """Finta `Application` di Telegram: ogni passo dell'avvio cede il ciclo di eventi, come le chiamate di rete vere."""

    def __init__(self, create):
        self.in_ascolto = False
        self.updater = SimpleNamespace(start_polling=self._ascolta, stop=self._smetti)
        create.append(self)

    def add_handler(self, *_, **__):
        pass

    async def initialize(self):
        await asyncio.sleep(0)

    async def start(self):
        await asyncio.sleep(0)

    async def _ascolta(self, **_):
        await asyncio.sleep(0)
        self.in_ascolto = True

    async def _smetti(self):
        self.in_ascolto = False

    async def stop(self):
        pass

    async def shutdown(self):
        pass


@pytest.mark.parametrize("secondo", ["avvia", "_riprova"])
def test_due_avvii_insieme_non_lasciano_un_bot_in_ascolto(monkeypatch, secondo):
    # S-12 (scheda 7 del documento 04): durante gli await di avvia un secondo avvio vedeva ancora il bot spento e ne
    # creava un altro; il primo restava in ascolto senza riferimento e ferma() non lo fermava più.
    create = []
    costruttore = SimpleNamespace(token=lambda _: SimpleNamespace(build=lambda: ApplicazioneFinta(create)))
    monkeypatch.setattr(telegram, "Application", SimpleNamespace(builder=lambda: costruttore))
    conf = SimpleNamespace(telegram_token=SimpleNamespace(get_secret_value=lambda: TOKEN))
    bot = telegram.BotGradiens(conf, None, None, lambda: None)
    monkeypatch.setattr(bot, "_chat", lambda: CHAT)

    async def prova():
        await asyncio.gather(bot.avvia(), getattr(bot, secondo)())
        await bot.ferma()

    asyncio.run(prova())
    assert not [app for app in create if app.in_ascolto]
    if secondo == "_riprova":  # il bot era già acceso: niente secondo avvio
        assert len(create) == 1


def test_pausa_e_riprendi_dicono_cosa_non_vale(ambiente):
    # Scheda 11 (I-2 a, b) del documento 04, decisione 41: il comportamento resta, ma lo si dice.
    client, _ = ambiente
    b = telegram.BotGradiens(client.app.state.conf, client.app.state.sessioni, EsecutoreFinto(),
                             lambda: datetime(2026, 11, 18, 7, 0))
    u = aggiornamento()
    asyncio.run(b._pausa(u, None))
    assert "mentre Gradiens è spento va perso" in u.effective_message.testi[0]
    u = aggiornamento()
    asyncio.run(b._riprendi(u, None))
    testo = u.effective_message.testi[0]
    assert "Prossima esecuzione programmata: 18/11 alle 07:00" in testo and "non si recupera" in testo


def test_l_aiuto_dice_cosa_non_valgono_pausa_e_riprendi(client):
    telegram_ = client.get("/aiuto").text.split('id="telegram"')[1]
    assert "mentre Gradiens è spento va perso" in telegram_ and "non recupera" in telegram_


def test_fermare_il_bot_durante_un_avvio_lo_lascia_spento(monkeypatch):
    # S-12, seguito della scheda 7: "Cambia chat" o un token nuovo chiamano ferma() mentre un tentativo di avvio è a
    # metà; ferma() trovava il bot ancora spento e non faceva niente, poi l'avvio finiva e il bot restava acceso.
    create = []
    costruttore = SimpleNamespace(token=lambda _: SimpleNamespace(build=lambda: ApplicazioneFinta(create)))
    monkeypatch.setattr(telegram, "Application", SimpleNamespace(builder=lambda: costruttore))
    conf = SimpleNamespace(telegram_token=SimpleNamespace(get_secret_value=lambda: TOKEN))
    bot = telegram.BotGradiens(conf, None, None, lambda: None)
    monkeypatch.setattr(bot, "_chat", lambda: CHAT)

    async def ferma_subito():
        await asyncio.sleep(0)  # l'avvio è partito e aspetta la rete
        await bot.ferma()

    async def prova():
        await asyncio.gather(bot.avvia(), ferma_subito())

    asyncio.run(prova())
    assert create and not [app for app in create if app.in_ascolto]
