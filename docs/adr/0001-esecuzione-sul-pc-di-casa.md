# Gradiens gira sul PC di casa, raggiungibile da fuori tramite Tailscale

Gradiens (dashboard, CLI, database, scraping) gira sul PC di casa (Windows 11, RTX 3070 8 GB). Da fuori casa ci si collega tramite la VPN personale Tailscale, per usare la dashboard o la CLI via SSH. È l'unica opzione che tiene insieme i modelli LLM locali (servono la GPU), il costo zero e una sola macchina da gestire. Il prezzo da pagare è che il PC deve essere acceso, o riattivabile, quando serve un'esecuzione.

## Opzioni considerate

- **Server o VPS sempre acceso**: scartato. Non ha GPU, quindi niente modelli locali, ha un costo mensile e alcuni siti (ad es. il portale ACN) bloccano gli IP dei datacenter.
- **Ibrido (app su server, modello locale sul PC)**: scartato perché somma la complessità delle due opzioni.

## Conseguenze

- Il codice resta portabile (niente dipendenze specifiche di Windows), così un futuro spostamento su server costa poco.
- L'app non va esposta su internet: è raggiungibile solo dalla rete locale e da Tailscale.

## Aggiornamento (15 novembre 2026)

L'installazione usata ogni giorno è oggi un portatile Linux (Debian 13), senza GPU dedicata; il PC Windows
resta supportato e provato (decisioni 2 e 57 di [decisioni.md](../miglioramenti/decisioni.md)). La scelta di
fondo non cambia: un solo computer dell'utente, nessun server. Per l'accesso da fuori casa vedi
[ADR 0013](0013-dashboard-da-fuori-casa-con-tailscale-serve.md).

