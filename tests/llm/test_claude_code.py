import asyncio
import json
import sys

import pytest

from gradiens.llm.base import ErroreLLM, QuotaEsaurita
from gradiens.llm.claude_code import ClaudeCode, interpreta

# Finto `claude`: salva argomenti, stdin e ambiente, poi risponde secondo la modalità.
FINTO = r'''
import json, os, sys, time
cartella = os.path.dirname(os.path.abspath(__file__))
modalita = open(os.path.join(cartella, "modalita.txt")).read().strip()
chiamate = os.path.join(cartella, "chiamate.txt")
n = (int(open(chiamate).read()) if os.path.exists(chiamate) else 0) + 1
open(chiamate, "w").write(str(n))
json.dump({"argv": sys.argv[1:], "stdin": sys.stdin.buffer.read().decode("utf-8"), "chiave": os.environ.get("ANTHROPIC_API_KEY")},
          open(os.path.join(cartella, "ultima.json"), "w"))
if modalita == "lento":
    time.sleep(5)
if modalita == "lento-poi-scrive":
    time.sleep(2)
    open(os.path.join(cartella, "finito.txt"), "w").write("ancora vivo")
if modalita == "quota":
    print(json.dumps({"is_error": True, "api_error_status": 429, "result": "Claude usage limit reached"}))
elif modalita == "rotto" or (modalita == "rotto-una-volta" and n == 1):
    print("non è json")
else:
    print(json.dumps({"is_error": False, "structured_output": {"ok": True},
                      "usage": {"input_tokens": 2, "cache_read_input_tokens": 700, "output_tokens": 30}}))
'''


@pytest.fixture
def finto(tmp_path):
    (tmp_path / "claude_finto.py").write_text(FINTO, encoding="utf-8")

    def prepara(modalita: str, **opzioni) -> ClaudeCode:
        (tmp_path / "modalita.txt").write_text(modalita)
        return ClaudeCode(comando=[sys.executable, str(tmp_path / "claude_finto.py")], **opzioni)

    prepara.cartella = tmp_path
    return prepara


def chiedi(provider):
    return asyncio.run(provider.chiedi(sistema="istruzioni", messaggio="notizia con è e \"virgolette\"",
                                       schema={"type": "object"}, modello="haiku"))


def test_chiamata_isolata_con_messaggio_da_stdin(finto, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-segreta")
    risposta = chiedi(finto("ok"))
    assert risposta.dati == {"ok": True}
    assert (risposta.token_ingresso, risposta.token_uscita) == (702, 30)
    ultima = json.loads((finto.cartella / "ultima.json").read_text())
    assert ultima["stdin"] == "notizia con è e \"virgolette\""
    assert ultima["chiave"] is None  # mai l'API a pagamento al posto dell'abbonamento
    for opzione in ("--safe-mode", "--strict-mcp-config", "--no-session-persistence", "--disable-slash-commands"):
        assert opzione in ultima["argv"]
    assert ultima["argv"][ultima["argv"].index("--tools") + 1] == ""


def test_quota_esaurita_senza_nuovo_tentativo(finto):
    with pytest.raises(QuotaEsaurita):
        chiedi(finto("quota"))
    assert (finto.cartella / "chiamate.txt").read_text() == "1"


def test_errore_temporaneo_riprovato_una_volta(finto):
    assert chiedi(finto("rotto-una-volta")).dati == {"ok": True}
    with pytest.raises(ErroreLLM):
        chiedi(finto("rotto"))


def test_timeout(finto):
    with pytest.raises(ErroreLLM, match="non ha risposto"):
        chiedi(finto("lento", timeout=1))


def test_risposta_senza_dati_strutturati():
    with pytest.raises(ErroreLLM):
        interpreta(json.dumps({"is_error": False, "result": "testo libero"}))


def test_chiamata_cancellata_chiude_claude(finto):
    async def prova():
        compito = asyncio.create_task(finto("lento-poi-scrive").chiedi(
            sistema="s", messaggio="m", schema={}, modello="haiku"))
        await asyncio.sleep(0.5)
        compito.cancel()
        with pytest.raises(asyncio.CancelledError):
            await compito
        await asyncio.sleep(3)

    asyncio.run(prova())
    assert not (finto.cartella / "finito.txt").exists()  # il processo è stato chiuso prima di finire


@pytest.mark.parametrize("uscita, atteso", [
    ('{"loggedIn": true, "subscriptionType": "pro"}', None),
    ('{"loggedIn": false}', "non è collegato"),
    ("non è JSON", "non risponde"),
])
def test_pronto_controlla_il_collegamento_all_account(uscita, atteso):
    provider = ClaudeCode(comando=[sys.executable, "-c", f"print({uscita!r})"])
    if atteso is None:
        asyncio.run(provider.pronto())
    else:
        with pytest.raises(ErroreLLM, match=atteso):
            asyncio.run(provider.pronto())
