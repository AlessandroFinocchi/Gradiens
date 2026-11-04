# Gradiens è scritto in Python

Il backend di Gradiens (raccolta, filtro LLM, esecuzioni, bot Telegram, CLI) è scritto in Python. La parte più rischiosa del progetto è estrarre in modo affidabile testo, date e trascrizioni da fonti eterogenee, e per questo Python offre le librerie più mature:
- `trafilatura` per testo e data degli articoli;
- `feedparser` per i feed, anche malformati;
- `youtube-transcript-api` e `yt-dlp` per le trascrizioni (anche quelle generate automaticamente) e per distinguere video, short e dirette;
- SDK ufficiali di Anthropic e OpenAI;
- `python-telegram-bot`.

## Opzioni considerate

- **TypeScript con Node**: scartato. Avrebbe un solo linguaggio anche per la dashboard, ma l'estrazione degli articoli è più debole (soprattutto sulle date) e le librerie per le trascrizioni YouTube sono meno curate. Parte di quello che in Python esiste già andrebbe riscritto a mano.
- **Misto (Python per la raccolta, TypeScript per dashboard e API)**: scartato. Due processi, due gestori di pacchetti e un formato dati da tenere allineato sono troppo per un'app personale.

## Conseguenze

- La dashboard richiede comunque HTML, CSS e un po' di JavaScript nel browser. Come costruirla è una decisione separata.
- Sul PC è installato Python 3.14: le dipendenze scelte devono supportarlo.
