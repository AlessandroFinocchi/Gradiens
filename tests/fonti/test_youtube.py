import asyncio
from datetime import datetime

import pytest

from gradiens.fonti import Candidata, ContenutoAssente, NonAncoraDisponibile, youtube

CANALE = youtube.Canale(id="UCYO_jab_esuFRV4b17AJtAw", nome="3Blue1Brown")
RSS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns:media="http://search.yahoo.com/mrss/" xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <yt:videoId>V_uq3v6xK-4</yt:videoId>
    <title>The Sphere
      Intersection Puzzle</title>
    <published>2026-10-25T14:30:46+00:00</published>
    <media:group><media:description>Part of a series of monthly puzzles</media:description></media:group>
  </entry>
  <entry>
    <yt:videoId>javascript:alert(1)</yt:videoId>
    <title>Id non valido</title>
    <published>2026-10-25T14:30:46+00:00</published>
  </entry>
</feed>"""


def test_interpreta_il_feed_del_canale():
    (video,) = youtube.interpreta(RSS, CANALE)  # l'id non valido si scarta: finirebbe in un link
    assert video.url == "https://www.youtube.com/watch?v=V_uq3v6xK-4"
    assert (video.tipo, video.fonte, video.titolo) == ("video", "3Blue1Brown", "The Sphere Intersection Puzzle")
    assert video.sommario == "Part of a series of monthly puzzles"
    assert video.pubblicata_il == datetime(2026, 10, 25, 14, 30, 46)


@pytest.mark.parametrize("incollato, atteso", [
    ("@3blue1brown", "https://www.youtube.com/@3blue1brown"),
    ("UCYO_jab_esuFRV4b17AJtAw", "https://www.youtube.com/channel/UCYO_jab_esuFRV4b17AJtAw"),
    ("youtu.be/V_uq3v6xK-4", "https://youtu.be/V_uq3v6xK-4"),
])
def test_indirizzi_accettati(incollato, atteso):
    assert youtube.indirizzo_canale(incollato) == atteso


def test_indirizzi_non_youtube_rifiutati():
    with pytest.raises(ValueError):
        youtube.indirizzo_canale("https://youtube.com.example.org/@x")


def candidata() -> Candidata:
    return Candidata(tipo="video", url="https://www.youtube.com/watch?v=V_uq3v6xK-4", fonte="3Blue1Brown",
                     titolo="t", sommario="s", contenuto="", pubblicata_il=datetime(2026, 11, 1))


def test_completa_riconosce_short_e_dirette(monkeypatch):
    info = {}
    monkeypatch.setattr(youtube, "_info", lambda url, piatta=False: info)
    monkeypatch.setattr(youtube, "_trascrizione", lambda id: f"trascrizione di {id}")

    info.update(media_type="short", live_status="not_live")
    c = asyncio.run(youtube.completa(None, candidata()))
    assert (c.tipo, c.contenuto) == ("short", "trascrizione di V_uq3v6xK-4")

    info.update(media_type="video", live_status="is_upcoming")
    with pytest.raises(NonAncoraDisponibile):
        asyncio.run(youtube.completa(None, candidata()))


def test_trascrizione_assente(monkeypatch):
    class Senza:
        def list(self, id):
            raise youtube.TranscriptsDisabled(id)

    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", Senza)
    with pytest.raises(ContenutoAssente, match="trascrizione assente"):
        youtube._trascrizione("V_uq3v6xK-4")


def test_al_massimo_due_video_completati_alla_volta(monkeypatch):
    import threading
    import time

    contemporanei, massimo, lucchetto = 0, 0, threading.Lock()

    def info_lenta(url, piatta=False):
        nonlocal contemporanei, massimo
        with lucchetto:
            contemporanei += 1
            massimo = max(massimo, contemporanei)
        time.sleep(0.05)
        with lucchetto:
            contemporanei -= 1
        return {"live_status": "not_live"}

    monkeypatch.setattr(youtube, "_info", info_lenta)
    monkeypatch.setattr(youtube, "_trascrizione", lambda id: "testo")

    async def prova():
        await asyncio.gather(*(youtube.completa(None, candidata()) for _ in range(6)))

    asyncio.run(prova())
    asyncio.run(prova())  # un secondo ciclo asyncio, come in un altro test o dopo un riavvio
    assert massimo == 2
