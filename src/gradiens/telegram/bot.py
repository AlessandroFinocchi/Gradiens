"""Bot Telegram (PRD sezione 7): comandi, messaggio di fine esecuzione e cuore.

Riceve i messaggi con il polling dentro il processo del servizio, quindi il PC non apre porte (AMB-02).
Risponde solo alla chat autorizzata (TG-02). Il token sta nel .env e non finisce nei log (PER-04).
"""

import asyncio
import contextlib
import logging
import re
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker
from telegram import Bot, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.error import InvalidToken, TelegramError
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, TypeHandler, filters

from gradiens.app.configurazione import Configurazione
from gradiens.dati import esecuzioni, impostazioni, notizie
from gradiens.dati.modelli import Esecuzione, Notizia
from gradiens.esecuzione.esecutore import Esecutore, GiaInCorso
from gradiens.telegram import messaggi

log = logging.getLogger(__name__)

FORMATO_TOKEN = re.compile(r"^\d{5,}:[\w-]{30,}$")
RIPROVA = 60  # secondi tra due tentativi di avvio, se Telegram non era raggiungibile
SENZA_ANTEPRIMA = LinkPreviewOptions(is_disabled=True)


RIFIUTATO = "Telegram rifiuta questo token: ricopialo dal messaggio di BotFather."


class ErroreTelegram(Exception):
    """Problema da mostrare all'utente nel tutorial (TG-01)."""


def _errore(errore: TelegramError) -> ErroreTelegram:
    # Il testo di InvalidToken contiene il token stesso: non va mostrato (PER-04).
    return ErroreTelegram(RIFIUTATO if isinstance(errore, InvalidToken) else f"Telegram non risponde: {errore}")


# ---------- Tutorial (TG-01): chiamate dirette, con il bot fermo ----------

async def verifica_token(token: str) -> str:
    """Username del bot, se il token funziona."""
    if not FORMATO_TOKEN.match(token):
        raise ErroreTelegram("Non sembra un token: è la stringa che BotFather manda dopo /newbot, del tipo 123456789:AAF…")
    try:
        async with Bot(token) as bot:
            return (await bot.get_me()).username
    except TelegramError as errore:
        raise _errore(errore) from None


async def cerca_chat(token: str) -> tuple[int, str] | None:
    """Chat dell'ultimo /start mandato al bot, come (id, nome)."""
    try:
        async with Bot(token) as bot:
            aggiornamenti = await bot.get_updates(timeout=0, allowed_updates=["message"])
    except TelegramError as errore:
        raise _errore(errore) from None
    for u in reversed(aggiornamenti):
        if u.message and (u.message.text or "").startswith("/start"):
            return u.message.chat.id, u.message.chat.effective_name or str(u.message.chat.id)
    return None


async def collega(token: str, chat_id: int) -> None:
    """Fine del tutorial: menu dei comandi presso Telegram e messaggio di benvenuto."""
    try:
        async with Bot(token) as bot:
            await bot.set_my_commands([BotCommand(c, spiegazione) for c, spiegazione in messaggi.COMANDI.items()])
            await bot.send_message(chat_id, "Gradiens è collegato a questa chat.\n\n" + messaggi.aiuto())
    except TelegramError as errore:
        raise _errore(errore) from None


# ---------- Il bot in funzione ----------

class BotGradiens:
    def __init__(self, conf: Configurazione, sessioni: sessionmaker[Session], esecutore: Esecutore,
                 prossima: Callable[[], datetime | None]):
        self._conf = conf
        self._sessioni = sessioni
        self._esecutore = esecutore
        self._prossima = prossima
        self._app: Application | None = None
        self.errore: str | None = None  # es. token non più valido (segnale di UI-14)

    def _chat(self) -> int | None:
        with self._sessioni() as s:
            return impostazioni.leggi(s).telegram_chat_id

    def problema(self) -> str | None:
        """Motivo del segnale sulla sezione Telegram, oppure None se il bot è a posto."""
        if self._conf.telegram_token is None or self._chat() is None:
            return "Bot Telegram non collegato"
        return self.errore

    async def avvia(self) -> None:
        await self.ferma()
        token, chat = self._conf.telegram_token, self._chat()
        if token is None or chat is None:
            return
        app = Application.builder().token(token.get_secret_value()).build()
        solo_chat = filters.Chat(chat_id=chat)  # TG-02: le altre chat si ignorano
        comandi = {"aggiorna": self._aggiorna, "stato": self._stato, "ultima": self._ultima,
                   "pausa": self._pausa, "riprendi": self._riprendi, "help": self._aiuto, "start": self._aiuto}
        for nome, gestore in comandi.items():
            app.add_handler(CommandHandler(nome, gestore, filters=solo_chat))
        app.add_handler(CallbackQueryHandler(self._cuore, pattern=r"^cuore:\d+$"))
        app.add_handler(TypeHandler(Update, self._registra), group=-1)  # prima degli altri gestori
        try:
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])
        except TelegramError as errore:
            # La libreria apre i client HTTP prima di chiamare Telegram: senza chiuderli, ogni tentativo li lascerebbe aperti.
            with contextlib.suppress(Exception):
                await app.bot.shutdown()
            if isinstance(errore, InvalidToken):  # il suo testo contiene il token: non va nei log (PER-04)
                self.errore = "Il token del bot non è più valido: rifai il collegamento"
            else:
                self.errore = f"Telegram non raggiungibile: {errore}"
                log.warning("Avvio del bot Telegram non riuscito: %s", errore)
            return
        self._app, self.errore = app, None
        log.info("Bot Telegram in ascolto")

    async def ferma(self) -> None:
        if self._app is None:
            return
        app, self._app = self._app, None
        with contextlib.suppress(Exception):  # allo spegnimento non deve bloccare il resto
            await app.updater.stop()
            await app.stop()
            await app.shutdown()

    async def gira(self) -> None:
        """Avvia il bot e riprova se Telegram non era raggiungibile (es. PC acceso senza rete)."""
        while True:
            await asyncio.sleep(RIPROVA)  # il primo tentativo lo fa il servizio all'avvio
            token_rifiutato = self.errore and "token" in self.errore
            if self._app is None and not token_rifiutato:
                await self.avvia()

    # ---- Messaggio di fine esecuzione (TG-03, TG-04, TG-09) ----

    def _messaggio_esecuzione(self, s: Session, id: int) -> tuple[str, InlineKeyboardMarkup | None]:
        e = s.get_one(Esecuzione, id)
        gruppi = notizie.in_evidenza(s, impostazioni.leggi(s).soglia, esecuzione_id=id)
        testo, numerate = messaggi.fine_esecuzione(e, esecuzioni.riepilogo(e), gruppi, impostazioni.nomi_categorie(s))
        return testo, _tastiera(numerate)

    async def invia_esecuzione(self, id: int) -> None:
        """Chiamata dall'esecutore alla fine di ogni esecuzione: un errore di Telegram non la riguarda."""
        chat = self._chat()
        if self._app is None or chat is None:
            return
        try:
            with self._sessioni() as s:
                testo, tastiera = self._messaggio_esecuzione(s, id)
            await self._app.bot.send_message(chat, testo, parse_mode=ParseMode.HTML, reply_markup=tastiera,
                                             link_preview_options=SENZA_ANTEPRIMA)
        except Exception:
            log.exception("Messaggio Telegram dell'esecuzione %s non inviato", id)

    async def invia_prova(self) -> None:
        if self._app is None:
            raise ErroreTelegram(self.problema() or "Il bot non è in funzione.")
        try:
            await self._app.bot.send_message(self._chat(), "Messaggio di prova da Gradiens: il collegamento funziona.")
        except TelegramError as errore:
            raise _errore(errore) from None

    # ---- Comandi (TG-05..TG-10) ----

    async def _registra(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """Nel log ogni comando o bottone ricevuto, e da quale chat: serve a capire cosa arriva al bot."""
        chat = update.effective_chat.id if update.effective_chat else None
        cosa = update.callback_query.data if update.callback_query else (update.effective_message and update.effective_message.text)
        autorizzata = "" if chat == self._chat() else " (chat non autorizzata: ignorato)"
        log.info("Telegram: %s%s", (cosa or "?")[:40], autorizzata)

    async def _rispondi(self, update: Update, testo: str) -> None:
        await update.effective_message.reply_text(testo, parse_mode=ParseMode.HTML, link_preview_options=SENZA_ANTEPRIMA)

    async def _aggiorna(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            self._esecutore.avvia("telegram")
        except GiaInCorso:
            await self._rispondi(update, "Esecuzione già in corso.")
            return
        await self._rispondi(update, "Esecuzione avviata. Alla fine ti mando le notizie migliori.")

    def _ultima_conclusa(self, s: Session):
        return next((e for e in esecuzioni.storico(s, 2) if e.stato != "in_corso"), None)

    async def _stato(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        with self._sessioni() as s:
            ultima = self._ultima_conclusa(s)
            testo = messaggi.stato(self._esecutore.avanzamento, ultima, ultima and esecuzioni.riepilogo(ultima),
                                   self._prossima())
        await self._rispondi(update, testo)

    async def _ultima(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        with self._sessioni() as s:
            ultima = self._ultima_conclusa(s)
            if ultima is None:
                testo, tastiera = "Nessuna esecuzione ancora.", None
            else:
                testo, tastiera = self._messaggio_esecuzione(s, ultima.id)
        await update.effective_message.reply_text(testo, parse_mode=ParseMode.HTML, reply_markup=tastiera,
                                                  link_preview_options=SENZA_ANTEPRIMA)

    async def _imposta_pausa(self, update: Update, in_pausa: bool) -> None:
        with self._sessioni() as s:
            impostazioni.imposta_pausa(s, in_pausa)
        await self._rispondi(update, "Programmazione in pausa: le esecuzioni a mano funzionano lo stesso."
                             if in_pausa else "Programmazione riattivata.")

    async def _pausa(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._imposta_pausa(update, True)

    async def _riprendi(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._imposta_pausa(update, False)

    async def _aiuto(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        await self._rispondi(update, messaggi.aiuto())

    async def _cuore(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """TG-09: mette o toglie il cuore e aggiorna i bottoni del messaggio."""
        domanda = update.callback_query
        if domanda.message is None or domanda.message.chat.id != self._chat():
            await domanda.answer()
            return
        id = int(domanda.data.removeprefix("cuore:"))
        with self._sessioni() as s:
            if s.get(Notizia, id) is None:
                await domanda.answer("Notizia non più disponibile.")
                return
            n = notizie.imposta_cuore(s, id, not s.get(Notizia, id).cuore)
            ids = [int(b.callback_data.removeprefix("cuore:")) for riga in domanda.message.reply_markup.inline_keyboard
                   for b in riga]
            numerate = [s.get(Notizia, i) for i in ids]
            tastiera = _tastiera(numerate, vecchia=domanda.message.reply_markup)
        await domanda.answer("Cuore messo: la notizia è in archivio." if n.cuore else "Cuore tolto.")
        await domanda.edit_message_reply_markup(tastiera)


def _tastiera(numerate: list[Notizia | None], vecchia: InlineKeyboardMarkup | None = None) -> InlineKeyboardMarkup | None:
    """Un bottone ❤️ per notizia, numerato come nel testo. Una notizia cancellata tiene il bottone di prima."""
    if not numerate:
        return None
    righe = []
    for i, n in enumerate(numerate):
        if n is None and vecchia is not None:
            righe.append(list(vecchia.inline_keyboard[i]))
        elif n is not None:
            righe.append([InlineKeyboardButton(messaggi.etichetta_cuore(i + 1, n), callback_data=f"cuore:{n.id}")])
    return InlineKeyboardMarkup(righe)
