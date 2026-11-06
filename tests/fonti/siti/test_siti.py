import json
from datetime import datetime

import httpx
import pytest

from gradiens.fonti import ContenutoAssente
from gradiens.fonti.siti import Profilo, analizza, completa, raccogli, rigenera

DAL = datetime(2026, 11, 1)


def test_redhotcyber_feed_che_risponde_html_e_feed_tra_i_link(sito):
    home = sito.fixture("wordpress_home.html")
    s = sito({
        "https://www.redhotcyber.com/": home,
        "https://www.redhotcyber.com/feed/": sito.redirect("https://www.redhotcyber.com/"),  # 301 verso la home HTML
        "https://www.redhotcyber.com/feed/gn": sito.fixture("rss_gn.xml"),
        "https://www.redhotcyber.com/wp-json/wp/v2/posts?per_page=1&_fields=link": '[{"link": "https://www.redhotcyber.com/x"}]',
    })
    profilo = s.esegui(analizza, "https://www.redhotcyber.com/")
    assert profilo.feed == ["https://www.redhotcyber.com/feed/gn"]  # il feed rel=alternate non è un feed
    assert profilo.piattaforma == "wordpress"
    assert profilo.strategie[:1] == ["feed"] and "wordpress" in profilo.strategie
    assert profilo.esclusi == ["https://www.redhotcyber.com/offerte/"]  # WEB-21: proposta già esclusa
    assert "https://www.redhotcyber.com/categoria/cybercrime/" in profilo.sezioni
    assert profilo.siti_collegati == {"academy.redhotcyber-partner.org": False}  # WEB-07, social esclusi
    assert all("comments" not in u for u in s.richieste)

    esito = s.esegui(raccogli, profilo, DAL)
    assert esito.stato == "ok" and not esito.guasto
    assert [c.url for c in esito.candidate] == [
        "https://www.redhotcyber.com/post/attacco-ransomware-alla-asl-di-esempio/",  # senza utm_*
        "https://www.redhotcyber.com/post/nuova-vulnerabilita-critica-nel-kernel/",
    ]
    prima = esito.candidate[0]
    assert (prima.tipo, prima.fonte, prima.pubblicata_il) == ("sito", "redhotcyber.com", datetime(2026, 11, 5, 8, 0))
    assert prima.sommario == "Un attacco ransomware ha colpito la ASL."  # niente HTML
    assert prima.contenuto == ""


def test_robots_che_vieta_l_api_non_viene_mai_chiamata(sito):
    s = sito({
        "https://www.ilsoftware.it/robots.txt": "User-agent: *\nDisallow: /wp-json/\n"
                                                "Sitemap: https://www.ilsoftware.it/news-sitemap.xml\n",
        "https://www.ilsoftware.it/": sito.fixture("ilsoftware_home.html"),
        "https://www.ilsoftware.it/feed/": sito.fixture("feed_ilsoftware.xml"),
        "https://www.ilsoftware.it/news-sitemap.xml": sito.fixture("news_sitemap.xml"),
    })
    profilo = s.esegui(analizza, "www.ilsoftware.it")  # anche senza protocollo
    assert profilo.piattaforma == "wordpress"
    assert profilo.feed == ["https://www.ilsoftware.it/feed/"]  # dal percorso comune: manca rel=alternate
    assert profilo.sitemap == ["https://www.ilsoftware.it/news-sitemap.xml"]
    assert "wordpress" not in profilo.strategie
    assert s.richieste[0] == "https://www.ilsoftware.it/robots.txt"  # robots.txt prima di tutto (WEB-17)

    esito = s.esegui(raccogli, profilo, DAL)
    assert not any("/wp-json/" in u for u in s.richieste)
    # il feed copre la finestra ma non c'è altro da aggiungere; la sitemap non serve
    assert [c.titolo for c in esito.candidate] == ["Come proteggere il router di casa"]
    assert esito.stato == "ok"


def test_hwupgrade_iso_8859_1_feed_su_altro_sottodominio_ed_esclusioni(sito):
    s = sito({
        "https://www.hwupgrade.it/": httpx.Response(200, content=sito.fixture("hwupgrade_home.html"),
                                                     headers={"content-type": "text/html"}),
        "https://feeds.hwupgrade.it/rss_news.xml": sito.fixture("hwupgrade_feed.xml"),
    })
    profilo = s.esegui(analizza, "https://www.hwupgrade.it/")
    assert profilo.feed == ["https://feeds.hwupgrade.it/rss_news.xml"]
    assert "https://www.hwupgrade.it/offerte/" in profilo.esclusi
    assert profilo.siti_collegati == {"fotografidigitali.it": False}
    assert "https://feeds.hwupgrade.it/robots.txt" in s.richieste  # robots anche per il sottodominio del feed

    esito = s.esegui(raccogli, profilo, DAL)
    assert [c.titolo for c in esito.candidate] == ["Le novità dei processori di novembre"]  # l'offerta è esclusa
    assert esito.candidate[0].sommario == "Perché è più veloce."


def test_pagina_iso_8859_1_senza_charset_nell_intestazione(sito):
    from gradiens.fonti.siti.rete import Pagina

    pagina = Pagina("https://www.hwupgrade.it/", 200, sito.fixture("hwupgrade_home.html"), "text/html")
    assert "Hardware Upgrade - Novità" in pagina.testo


def test_sezione_con_articoli_fuori_dal_prefisso_e_nessun_articolo_nuovo(sito):
    s = sito({
        "https://e3rehab.com/articles/": sito.fixture("e3rehab_articles.html"),
        "https://e3rehab.com/feed/": sito.fixture("e3rehab_feed.xml"),
    })
    profilo = s.esegui(analizza, "https://e3rehab.com/articles/")
    assert profilo.perimetro == "e3rehab.com/articles"
    # Il feed è di tutto il sito, ma i suoi articoli sono quelli elencati dalla sezione (WEB-09): si tiene.
    assert profilo.feed == ["https://e3rehab.com/feed/"]
    assert "wordpress" not in profilo.strategie  # in una sezione l'API darebbe tutto il sito
    assert profilo.sitemap == []  # una sitemap di tutto il sito non vale per la sezione
    assert profilo.sezioni == ["https://e3rehab.com/articles/training/"]

    esito = s.esegui(raccogli, profilo, DAL)
    assert esito.candidate == []
    assert esito.stato == "nessun articolo nuovo"
    assert esito.guasto is False  # zero articoli nuovi non è un guasto (WEB-24)

    esito = s.esegui(raccogli, profilo, datetime(2026, 9, 1))
    assert [c.url for c in esito.candidate] == ["https://e3rehab.com/how-to-fix-knee-pain-when-squatting/"]


def test_acn_accesso_bloccato_poi_feed_aggiunto_a_mano_non_ordinato(sito):
    s = sito({
        "https://www.acn.gov.it/robots.txt": httpx.Response(403, text="Access Denied"),
        "https://www.acn.gov.it/portale/csirt-italia/": httpx.Response(403, text="Access Denied"),
        "https://www.acn.gov.it/portale/feedrss/-/journal/rss/20119/723192": sito.fixture("acn_feed.xml"),
    })
    profilo = s.esegui(analizza, "https://www.acn.gov.it/portale/csirt-italia/")
    assert profilo.diagnosi == "accesso bloccato"
    esito = s.esegui(raccogli, profilo, DAL)
    assert (esito.stato, esito.guasto) == ("accesso bloccato", True)
    assert "feed" in esito.dettaglio

    profilo.aggiungi_feed("https://www.acn.gov.it/portale/feedrss/-/journal/rss/20119/723192")
    esito = s.esegui(raccogli, profilo, DAL)
    assert esito.stato == "ok"
    # elementi non in ordine di data e fuori dal prefisso della sezione: valgono tutti quelli recenti
    assert [c.titolo for c in esito.candidate] == ["Aggiornamenti di sicurezza mensili", "Vulnerabilità in un prodotto di rete"]


def test_sezione_solo_html_con_date_testuali_e_pagine_successive(sito):
    s = sito({
        "https://projectdiscovery.io/research": sito.fixture("research_1.html"),
        "https://projectdiscovery.io/research?page=2": sito.fixture("research_2.html"),
    })
    profilo = s.esegui(analizza, "https://projectdiscovery.io/research")
    assert profilo.strategie == ["html"]
    assert profilo.data_da == "elenco della pagina"

    esito = s.esegui(raccogli, profilo, DAL)
    assert [(c.titolo, c.pubblicata_il) for c in esito.candidate] == [
        ("Novel template injection in cloud apps", datetime(2026, 11, 4)),
        ("PHP2Shell", datetime(2026, 11, 4)),  # indirizzo corto, ma con una data accanto: è un articolo
        ("Release notes for nuclei v4", datetime(2026, 11, 3)),  # elencato dalla sezione, fuori dal prefisso
        ("Scheda intera", datetime(2026, 11, 3)),  # la data sta dentro il link
        ("Abusing OAuth redirects at scale", datetime(2026, 11, 2)),
        ("Fuzzing GraphQL endpoints for fun", datetime(2026, 11, 1)),
    ]
    # la seconda pagina ha un articolo più vecchio della finestra: la terza non si legge
    assert "https://projectdiscovery.io/research?page=3" not in s.richieste


def test_sito_che_richiede_javascript(sito):
    s = sito({"https://app.esempio.it/": sito.fixture("js.html")})
    profilo = s.esegui(analizza, "https://app.esempio.it/")
    esito = s.esegui(raccogli, profilo, DAL)
    assert (esito.stato, esito.guasto) == ("richiede JavaScript", True)
    assert "feed" in esito.dettaglio


def test_feed_che_risponde_html_o_404_e_un_guasto(sito):
    profilo = Profilo(url="https://sito.it/", perimetro="sito.it", feed=["https://sito.it/feed/"],
                      sitemap=["https://sito.it/sitemap.xml"], strategie=["feed", "sitemap"])
    s = sito({"https://sito.it/feed/": "<html><body>home</body></html>"})
    esito = s.esegui(raccogli, profilo, DAL)
    assert esito.guasto and "HTML" in esito.dettaglio
    assert esito.stato == "nessuna strategia funzionante"  # anche la sitemap risponde 404

    s = sito({"https://sito.it/feed/": httpx.Response(404)})
    esito = s.esegui(raccogli, profilo, DAL)
    assert esito.guasto and "404" in esito.dettaglio


def test_feed_fermo_mentre_la_sitemap_ha_articoli_recenti(sito):
    s = sito({
        "https://www.chipsandcheese.com/feed": sito.fixture("feed_fermo.xml"),
        "https://www.chipsandcheese.com/sitemap_index.xml": sito.fixture("sitemap_index.xml"),
        "https://www.chipsandcheese.com/post-sitemap.xml": sito.fixture("post_sitemap.xml"),
    })
    profilo = Profilo(url="https://www.chipsandcheese.com/", perimetro="chipsandcheese.com",
                      feed=["https://www.chipsandcheese.com/feed"],
                      sitemap=["https://www.chipsandcheese.com/sitemap_index.xml"], strategie=["feed", "sitemap"])
    esito = s.esegui(raccogli, profilo, DAL)
    assert [c.url for c in esito.candidate] == ["https://www.chipsandcheese.com/p/a-look-at-the-new-gpu-memory-subsystem"]
    assert esito.candidate[0].titolo == "A look at the new gpu memory subsystem"  # dallo slug, finché `completa` non lo legge
    assert esito.guasto and "fermo" in esito.dettaglio
    # sitemap figlie di pagine e quelle più vecchie della finestra non si leggono
    assert "https://www.chipsandcheese.com/page-sitemap.xml" not in s.richieste
    assert "https://www.chipsandcheese.com/post-sitemap-vecchia.xml" not in s.richieste


def test_data_incerta_dai_metadati_della_pagina_o_resta_incerta(sito):
    feed = """<rss version="2.0"><channel><title>t</title>
      <item><title>Con metadati</title><link>https://sito.it/articolo-con-metadati-della-pagina</link></item>
      <item><title>Senza data</title><link>https://sito.it/articolo-senza-alcuna-data</link></item>
    </channel></rss>"""
    s = sito({
        "https://sito.it/feed": feed,
        "https://sito.it/articolo-con-metadati-della-pagina": sito.fixture("articolo_paywall.html"),
        "https://sito.it/articolo-senza-alcuna-data": "<html><body><p>Nessuna data.</p></body></html>",
    })
    profilo = Profilo(url="https://sito.it/", perimetro="sito.it", feed=["https://sito.it/feed"], strategie=["feed"])
    esito = s.esegui(raccogli, profilo, DAL)
    date = {c.titolo: (c.pubblicata_il, c.data_incerta) for c in esito.candidate}
    assert date["Con metadati"] == (datetime(2026, 11, 3, 16, 0), False)
    assert date["Senza data"][1] is True


def test_tetto_di_articoli(sito):
    voci = "".join(f"<item><title>N{i}</title><link>https://sito.it/n-{i}</link>"
                   f"<pubDate>Thu, 05 Nov 2026 {i:02d}:00:00 +0000</pubDate></item>" for i in range(10))
    s = sito({"https://sito.it/feed": f"<rss version='2.0'><channel>{voci}</channel></rss>"})
    profilo = Profilo(url="https://sito.it/", perimetro="sito.it", feed=["https://sito.it/feed"], strategie=["feed"],
                      articoli_massimi=3)
    esito = s.esegui(raccogli, profilo, DAL)
    assert [c.titolo for c in esito.candidate] == ["N9", "N8", "N7"]
    assert "tetto" in esito.dettaglio


def test_profilo_json_e_rigenerazione_che_conserva_le_modifiche_manuali(sito):
    s = sito({"https://e3rehab.com/articles/": sito.fixture("e3rehab_articles.html"),
              "https://e3rehab.com/feed/": sito.fixture("e3rehab_feed.xml")})
    profilo = s.esegui(analizza, "https://e3rehab.com/articles/")
    profilo.aggiungi_feed("https://e3rehab.com/feed-a-mano/")
    profilo.escludi("https://e3rehab.com/articles/training/")
    profilo.articoli_massimi = 5
    profilo.modificati.append("articoli_massimi")

    salvato = Profilo.da_dict(json.loads(json.dumps(profilo.come_dict())))
    assert salvato == profilo

    nuovo = s.esegui(rigenera, salvato)
    assert nuovo.feed == ["https://e3rehab.com/feed/", "https://e3rehab.com/feed-a-mano/"]
    assert nuovo.esclusi == ["https://e3rehab.com/articles/training/"]
    assert nuovo.articoli_massimi == 5
    assert set(nuovo.modificati) == {"feed", "esclusi", "articoli_massimi"}

    esito = s.esegui(raccogli, nuovo, DAL)  # il feed a mano non risponde: segnalato, non rimosso (WEB-25)
    assert esito.guasto and "feed-a-mano" in esito.dettaglio
    assert "https://e3rehab.com/feed-a-mano/" in nuovo.feed


def test_completa_testo_pulito_paywall_e_data(sito):
    from gradiens.fonti import Candidata

    s = sito({"https://www.nature.com/articles/d41586-026-01234-5": sito.fixture("articolo_paywall.html")})
    candidata = Candidata(tipo="sito", url="https://www.nature.com/articles/d41586-026-01234-5", fonte="nature.com",
                          titolo="D41586 026 01234 5", sommario="", contenuto="", pubblicata_il=datetime(2026, 11, 6),
                          data_incerta=True)
    completa_ = s.esegui(completa, candidata)
    assert "temperatura ambiente" in completa_.contenuto and "<" not in completa_.contenuto
    assert completa_.stato == "contenuto parziale (paywall)"
    assert (completa_.pubblicata_il, completa_.data_incerta) == (datetime(2026, 11, 3, 16, 0), False)
    assert completa_.sommario == "Un nuovo tipo di dispositivo quantistico."


def test_completa_senza_testo_solleva_contenuto_assente(sito):
    from gradiens.fonti import Candidata

    s = sito({"https://sito.it/vuoto": "<html><body></body></html>"})
    candidata = Candidata(tipo="sito", url="https://sito.it/vuoto", fonte="sito.it", titolo="t", sommario="",
                          contenuto="", pubblicata_il=datetime(2026, 11, 5))
    with pytest.raises(ContenutoAssente, match="errore di estrazione"):
        s.esegui(completa, candidata)


def test_sitemap_rigenerata_con_lo_stesso_lastmod_non_da_date():
    from gradiens.fonti.siti.rete import Pagina
    from gradiens.fonti.siti.strategie import sitemap

    voci = "".join(f"<url><loc>https://nature.com/nature-index/supplements/indice-numero-{i}</loc>"
                   f"<lastmod>2026-11-06T03:57:00Z</lastmod></url>" for i in range(12))
    xml = f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{voci}</urlset>'.encode()
    tipo, lette = sitemap.interpreta(Pagina("https://nature.com/sitemap.xml", 200, xml, "application/xml"))
    assert tipo == "elenco" and all(data is None for _, data, _, _ in lette)
