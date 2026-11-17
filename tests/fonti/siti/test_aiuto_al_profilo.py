"""Funzioni senza LLM per l'aiuto al profilo (ADR 0012): albero dei link ridotto e convalida della risposta."""

import httpx

from gradiens.fonti.siti import Profilo
from gradiens.fonti.siti.aiuto import Gruppo, convalida, leggi_albero

REDHOTCYBER = Profilo(
    url="https://www.redhotcyber.com/",
    perimetro="redhotcyber.com",
    sezioni=["https://www.redhotcyber.com/categoria/cybercrime/"],
    esclusi=["https://www.redhotcyber.com/offerte/"],
)
CYBERCRIME = "https://www.redhotcyber.com/categoria/cybercrime/"
VULNERABILITA = "https://www.redhotcyber.com/categoria/vulnerabilita/"


def _albero(sito, profilo=REDHOTCYBER, home="wordpress_home.html"):
    s = sito({profilo.url: sito.fixture(home)})
    return s.esegui(leggi_albero, profilo), s


def test_albero_dei_link_raggruppati_per_forma_dell_indirizzo(sito):
    gruppi, s = _albero(sito)
    # Solo link interni: niente social, siti esterni, pagine di servizio (feed, privacy), esclusi o la pagina stessa.
    assert [(g.forma, len(g.link), g.nel_menu) for g in gruppi] == [("/categoria/*", 2, 2), ("/post/*", 3, 0)]
    assert gruppi[0].link == [(CYBERCRIME, "Cybercrime"), (VULNERABILITA, "Vulnerabilità")]
    # Per il prompt: tutti i link del menu, degli altri solo due esempi.
    assert gruppi[0].come_dict()["esempi"] == [[CYBERCRIME, "Cybercrime"], [VULNERABILITA, "Vulnerabilità"]]
    post = gruppi[1].come_dict()
    assert (post["forma"], post["link"], post["nel_menu"], len(post["esempi"])) == ("/post/*", 3, 0, 2)
    assert s.richieste == ["https://www.redhotcyber.com/robots.txt", "https://www.redhotcyber.com/"]  # una pagina sola


def test_albero_con_file_sottodomini_e_slug_in_cima_al_percorso(sito):
    profilo = Profilo(url="https://www.hwupgrade.it/", perimetro="hwupgrade.it")
    home = sito.fixture("hwupgrade_home.html").replace(
        b"</body>",
        (
            b'<a href="https://blog.hwupgrade.it/un-articolo-con-un-titolo-lungo/">Blog</a>'
            b'<a href="/primo-articolo-senza-sezione/">Uno</a><a href="/secondo-articolo-senza-sezione/">Due</a>'
            b'<a href="/allegato.pdf">PDF</a></body>'
        ),
    )
    s = sito({profilo.url: httpx.Response(200, content=home, headers={"content-type": "text/html"})})
    gruppi = s.esegui(leggi_albero, profilo)
    # Prima i gruppi con link del menu, poi gli altri dal più numeroso; il feed e il PDF sono file, non pagine.
    assert [(g.forma, len(g.link), g.nel_menu) for g in gruppi] == [
        ("/news", 1, 1),
        ("/offerte", 1, 1),
        ("/*", 2, 0),
        ("/news/*/*", 1, 0),
        ("blog.hwupgrade.it/*", 1, 0),
    ]


def test_albero_di_una_home_che_fa_un_redirect(sito):
    profilo = Profilo(url="https://redhotcyber.com/", perimetro="redhotcyber.com")  # come l'ha scritto l'utente
    s = sito(
        {
            "https://redhotcyber.com/": sito.redirect("https://www.redhotcyber.com/"),
            "https://www.redhotcyber.com/": sito.fixture("wordpress_home.html"),
        }
    )
    gruppi = s.esegui(leggi_albero, profilo)
    assert gruppi and gruppi[0].forma == "/categoria/*"


def test_albero_di_una_pagina_che_non_risponde(sito):
    assert sito({}).esegui(leggi_albero, REDHOTCYBER) is None  # 404: niente da mostrare all'LLM


def test_convalida_tiene_solo_indirizzi_dell_albero_e_del_perimetro(sito):
    gruppi, _ = _albero(sito)
    proposta = convalida(
        {
            "sezioni": [
                VULNERABILITA.rstrip("/"),  # senza la barra finale: è comunque un link dell'albero
                "https://www.redhotcyber.com/categoria/inventata/",  # non è nell'albero
                "https://academy.redhotcyber-partner.org/",  # fuori dal perimetro
                "javascript:alert(1)",
                42,
                None,
            ],
            "esclusi": [
                "https://www.redhotcyber.com/post/",  # copre dei link dell'albero
                "https://www.redhotcyber.com/offerte/",  # già escluso
                "https://www.redhotcyber.com/",  # escluderebbe tutto il sito
                "https://www.redhotcyber.com/eventi/",  # nessun link dell'albero
                "https://altro.example/post/",
            ],
            "nota": "  Le categorie   elencano articoli.  ",
        },
        gruppi,
        REDHOTCYBER,
    )
    assert proposta.sezioni_aggiunte == [VULNERABILITA]
    assert proposta.sezioni_tolte == [CYBERCRIME]  # l'LLM non l'ha tenuta
    assert proposta.esclusi_nuovi == ["https://www.redhotcyber.com/post/"]
    assert proposta.nota == "Le categorie elencano articoli."
    assert proposta.cambia_qualcosa


def test_convalida_non_propone_di_togliere_le_sezioni_che_l_llm_non_ha_visto(sito):
    # Una sezione che la pagina iniziale non collega (o che sta in un gruppo tolto per il tetto) non è tra i link dati
    # all'LLM: la sua assenza dalla risposta non è un giudizio, quindi non si propone di toglierla.
    gruppi, _ = _albero(sito)
    nascosta = "https://www.redhotcyber.com/rubriche/sicurezza/"
    profilo = Profilo(url=REDHOTCYBER.url, perimetro=REDHOTCYBER.perimetro, sezioni=[CYBERCRIME, nascosta])
    assert convalida({"sezioni": [CYBERCRIME], "esclusi": []}, gruppi, profilo).sezioni_tolte == []
    assert convalida({"sezioni": [], "esclusi": []}, gruppi, profilo).sezioni_tolte == [CYBERCRIME]


def test_convalida_di_una_risposta_che_non_cambia_niente(sito):
    gruppi, _ = _albero(sito)
    proposta = convalida({"sezioni": [CYBERCRIME], "esclusi": [], "nota": "x" * 1000}, gruppi, REDHOTCYBER)
    assert not proposta.cambia_qualcosa
    assert len(proposta.nota) == 600  # la prova vera ne ha scritti circa 560


def test_convalida_al_massimo_otto_sezioni():
    profilo = Profilo(url="https://sito.it/", perimetro="sito.it")
    link = [(f"https://sito.it/sezione-{i}/", f"Sezione {i}") for i in range(12)]
    gruppi = [Gruppo(forma="/*", link=link, nel_menu=12)]
    proposta = convalida({"sezioni": [u for u, _ in link], "esclusi": []}, gruppi, profilo)
    assert proposta.sezioni_aggiunte == [u for u, _ in link[:8]]


def test_togliere_una_sezione_e_una_modifica_manuale():
    profilo = Profilo(url="https://sito.it/", sezioni=["https://sito.it/a/", "https://sito.it/b/"])
    profilo.togli_sezione("https://sito.it/a/")
    assert (profilo.sezioni, profilo.modificati) == (["https://sito.it/b/"], ["sezioni"])
