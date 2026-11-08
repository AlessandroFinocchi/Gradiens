"""L'unico codice che dipende dal sistema operativo (PRD AMB-03, ADR 0005 per Windows, ADR 0007 per Linux).

Lanciare Gradiens staccato dal terminale, trovare l'eseguibile nativo di Claude Code e registrare
l'avvio all'accensione (AMB-04): servizio utente di systemd su Linux, attività pianificata su Windows.
"""

import base64
import getpass
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


def lancia_staccato(comando: list[str], file_errori: Path) -> None:
    """Processo indipendente dal terminale e dalla sessione SSH; gli errori di avvio finiscono in `file_errori`."""
    with open(file_errori, "ab") as errori:
        opzioni = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=errori, close_fds=True)
        if os.name != "nt":  # Linux: una nuova sessione non riceve il SIGHUP alla chiusura del terminale
            subprocess.Popen(comando, start_new_session=True, **opzioni)
            return
        base = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            # Esce dal "job" della sessione SSH di Windows, che altrimenti chiuderebbe Gradiens all'uscita.
            subprocess.Popen(comando, creationflags=base | subprocess.CREATE_BREAKAWAY_FROM_JOB, **opzioni)
        except OSError:
            subprocess.Popen(comando, creationflags=base, **opzioni)


def eseguibile_claude(percorso: Path) -> Path:
    """Su Windows lo script npm `claude.cmd` passerebbe gli argomenti a cmd.exe, che reinterpreta
    virgolette, % e &: per sicurezza si lancia l'eseguibile nativo. Su Linux `claude` è già lanciabile."""
    if os.name == "nt" and percorso.suffix.lower() in (".cmd", ".bat"):
        return percorso.parent / "node_modules" / "@anthropic-ai" / "claude-code" / "bin" / "claude.exe"
    return percorso


# ---- Avvio all'accensione (AMB-04) ----

ARGOMENTI = ["-m", "gradiens", "avvia", "--primo-piano"]  # anche per `gradiens avvia` staccato dal terminale
NOME = "Gradiens"  # attività pianificata di Windows
SERVIZIO = "gradiens.service"  # servizio utente di systemd
DURATA_CACHE = 60  # secondi: lo stato serve a ogni pagina (segnali) e su Windows interrogarlo è lento


@dataclass
class StatoAvvio:
    attivo: bool  # la registrazione nel sistema operativo esiste
    problema: str | None = None  # registrazione da rifare o incompleta
    comando: str | None = None  # da lanciare a mano per risolvere il problema


class ErroreAvvio(Exception):
    """Registrazione non riuscita; `comando` è il ripiego da lanciare a mano, se c'è."""

    def __init__(self, messaggio: str, comando: str | None = None):
        super().__init__(messaggio)
        self.comando = comando


_cache: tuple[float, StatoAvvio] | None = None


def su_windows() -> bool:
    """Per i testi della dashboard, che cambiano tra Windows e Linux."""
    return os.name == "nt"


def stato_avvio(radice: Path) -> StatoAvvio:
    global _cache
    if _cache is None or time.monotonic() - _cache[0] > DURATA_CACHE:
        try:
            stato = _stato_windows(radice) if os.name == "nt" else _stato_linux(radice)
        except (ErroreAvvio, ET.ParseError) as errore:  # serve a ogni pagina: un errore non deve romperle
            stato = StatoAvvio(True, f"Non riesco a leggere la registrazione dell'avvio: {errore}")
        _cache = time.monotonic(), stato
    return _cache[1]


def attiva_avvio(radice: Path) -> StatoAvvio:
    global _cache
    _cache = None
    if os.name == "nt":
        _come_amministratore(script_windows(radice, sys.executable, _utente_windows()))
    else:
        _attiva_linux(radice)
    return stato_avvio(radice)


def disattiva_avvio(radice: Path) -> None:
    global _cache
    _cache = None
    if os.name == "nt":
        _come_amministratore(f"Unregister-ScheduledTask -TaskName '{NOME}' -Confirm:$false")
    else:
        _disattiva_linux()


def _esegui(comando: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(comando, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    except (OSError, subprocess.TimeoutExpired) as errore:
        raise ErroreAvvio(f"Comando non riuscito ({comando[0]}): {errore}") from None


# Linux: servizio utente di systemd (ADR 0007).

def _file_servizio() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "systemd" / "user" / SERVIZIO


def _claude() -> str | None:
    return os.environ.get("GRADIENS_CLAUDE") or shutil.which("claude")


def _virgolette(valore: str) -> str:
    """Argomento tra virgolette per systemd; % introdurrebbe uno specificatore."""
    return '"' + valore.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def unita_systemd(radice: Path, python: str, claude: str | None) -> str:
    righe = [
        "[Unit]",
        "Description=Gradiens (avvio all'accensione)",
        "",
        "[Service]",
        f"WorkingDirectory={str(radice).replace('%', '%%')}",
        "ExecStart=" + " ".join(_virgolette(a) for a in [python, *ARGOMENTI]),
        # All'accensione senza accesso il servizio non ha il PATH della shell, dove sta `claude`.
        *([f"Environment={_virgolette('GRADIENS_CLAUDE=' + claude)}"] if claude else []),
        "Restart=on-failure",
        "RestartSec=30",
        "",
        "[Install]",
        "WantedBy=default.target",
    ]
    return "\n".join(righe) + "\n"


def _systemctl(*argomenti: str) -> subprocess.CompletedProcess:
    if shutil.which("systemctl") is None:
        raise ErroreAvvio("Questo sistema non usa systemd: l'avvio all'accensione non è disponibile.")
    return _esegui(["systemctl", "--user", *argomenti])


def _linger() -> bool:
    if shutil.which("loginctl") is None:
        return False
    return _esegui(["loginctl", "show-user", getpass.getuser(), "-p", "Linger", "--value"]).stdout.strip() == "yes"


def _attiva_linux(radice: Path) -> None:
    file = _file_servizio()
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(unita_systemd(radice, sys.executable, _claude()), encoding="utf-8")
    for argomenti in (["daemon-reload"], ["enable", SERVIZIO]):
        if (r := _systemctl(*argomenti)).returncode != 0:
            raise ErroreAvvio(f"systemctl {' '.join(argomenti)} non riuscito: {r.stderr.strip()}")
    # Senza lingering il servizio partirebbe solo dopo l'accesso. Se serve la password, lo dice lo stato.
    if not _linger() and shutil.which("loginctl"):
        _esegui(["loginctl", "enable-linger", getpass.getuser()])


def _disattiva_linux() -> None:
    file = _file_servizio()
    if file.exists():
        _systemctl("disable", SERVIZIO)
        file.unlink()
        _systemctl("daemon-reload")


def _stato_linux(radice: Path) -> StatoAvvio:
    file = _file_servizio()
    if not file.exists():
        return StatoAvvio(False)
    rifai = "spegni e riaccendi l'interruttore"
    if file.read_text(encoding="utf-8") != unita_systemd(radice, sys.executable, _claude()):
        return StatoAvvio(True, f"Il servizio punta a un'altra cartella, a un altro Python o a un altro Claude Code: {rifai}.")
    if _systemctl("is-enabled", SERVIZIO).stdout.strip() != "enabled":
        return StatoAvvio(True, f"Il servizio non è abilitato: {rifai}.")
    if not _linger():
        return StatoAvvio(True, "Gradiens partirà solo dopo l'accesso al sistema: per farlo partire all'accensione "
                                "serve il comando qui sotto.", f"sudo loginctl enable-linger {getpass.getuser()}")
    return StatoAvvio(True)


# Windows: attività pianificata con l'utente del PC, senza password salvata (ADR 0005).

def _utente_windows() -> str:
    return f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', getpass.getuser())}".lstrip("\\")


def _ps(valore: str) -> str:
    return "'" + valore.replace("'", "''") + "'"


def script_windows(radice: Path, python: str, utente: str) -> str:
    """Script PowerShell che registra l'attività: si lancia come amministratore, oppure lo incolla l'utente.
    L'utente si legge prima dell'elevazione: con un account standard il PowerShell elevato è dell'amministratore."""
    return "\n".join([
        f"$a = New-ScheduledTaskAction -Execute {_ps(python)} -Argument {_ps(' '.join(ARGOMENTI))} -WorkingDirectory {_ps(str(radice))}",
        "$t = New-ScheduledTaskTrigger -AtStartup",
        f"$p = New-ScheduledTaskPrincipal -UserId {_ps(utente)} -LogonType S4U -RunLevel Limited",
        "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)",
        f"Register-ScheduledTask -TaskName {_ps(NOME)} -Action $a -Trigger $t -Principal $p -Settings $s -Force | Out-Null",
    ])


def _powershell() -> str:
    return str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")


def _sessione_senza_desktop() -> bool:
    """Avviato dall'attività all'accensione, Gradiens gira nella sessione 0, dove la finestra UAC non compare."""
    import ctypes

    sessione = ctypes.c_ulong()
    ctypes.windll.kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(sessione))
    return sessione.value == 0


def _come_amministratore(script: str) -> None:
    if _sessione_senza_desktop():
        raise ErroreAvvio("Gradiens è stato avviato all'accensione e gira senza desktop, quindi non può chiedere "
                          "la conferma di amministratore.", script)
    codificato = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    esterno = ("$p = Start-Process -FilePath powershell -Verb RunAs -Wait -PassThru -WindowStyle Hidden "
               f"-ArgumentList '-NoProfile','-NonInteractive','-EncodedCommand','{codificato}'; exit $p.ExitCode")
    r = _esegui([_powershell(), "-NoProfile", "-NonInteractive", "-Command", esterno])
    if r.returncode != 0:
        raise ErroreAvvio("La conferma di amministratore è stata negata oppure la registrazione non è riuscita.", script)


def stato_da_xml(xml: str, radice: Path, python: str) -> StatoAvvio:
    """Stato dall'esportazione XML dell'attività (`schtasks /Query /XML`)."""
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    radice_xml = ET.fromstring(re.sub(r"^\s*<\?xml[^>]*\?>", "", xml))
    valore = lambda percorso: (radice_xml.findtext(percorso, "", ns) or "").strip()  # noqa: E731
    stesso = lambda a, b: os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))  # noqa: E731
    if not (stesso(valore("t:Actions/t:Exec/t:Command").strip('"'), python)
            and stesso(valore("t:Actions/t:Exec/t:WorkingDirectory"), str(radice))):
        return StatoAvvio(True, "L'attività pianificata punta a un'altra cartella o a un altro Python: "
                                "spegni e riaccendi l'interruttore.")
    if valore("t:Settings/t:Enabled").lower() == "false":
        return StatoAvvio(True, "L'attività pianificata è disabilitata nell'Utilità di pianificazione.")
    return StatoAvvio(True)


def _stato_windows(radice: Path) -> StatoAvvio:
    r = _esegui(["schtasks", "/Query", "/TN", NOME, "/XML"])
    if r.returncode != 0:  # attività inesistente
        return StatoAvvio(False)
    return stato_da_xml(r.stdout, radice, sys.executable)


# ---- Icone del pannello di controllo sul desktop e nel menu (AMB-05, ADR 0009) ----

ICONA = Path(__file__).resolve().parents[1] / "dashboard" / "static" / "gradiens"  # .png e .ico
NOME_ICONA = "Gradiens"


def _pythonw() -> str:
    """Su Windows il pannello si apre con pythonw.exe, senza la finestra nera della console."""
    python = Path(sys.executable)
    senza_console = python.with_name("pythonw.exe")
    return str(senza_console if os.name == "nt" and senza_console.exists() else python)


def icone_presenti() -> bool:
    if os.name == "nt":  # il menu Start dell'utente sta sempre qui: niente PowerShell, che è lento
        menu = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
        return (menu / f"{NOME_ICONA}.lnk").exists()
    return _file_menu().exists()


def crea_icone(radice: Path) -> None:
    if os.name == "nt":
        r = _esegui([_powershell(), "-NoProfile", "-NonInteractive", "-Command", script_icone_windows(radice, _pythonw())])
        if r.returncode != 0:
            raise ErroreAvvio(f"Icone non create: {r.stderr.strip()[:300]}")
        return
    contenuto = voce_desktop(radice, sys.executable)
    _file_menu().parent.mkdir(parents=True, exist_ok=True)
    for file in _file_icone():
        file.write_text(contenuto, encoding="utf-8")
        file.chmod(0o755)  # sul desktop KDE e GNOME avviano solo i file .desktop eseguibili


def togli_icone() -> None:
    if os.name == "nt":
        _esegui([_powershell(), "-NoProfile", "-NonInteractive", "-Command",
                 "foreach ($c in 'Desktop', 'Programs') { Remove-Item -Force -ErrorAction SilentlyContinue "
                 f"(Join-Path ([Environment]::GetFolderPath($c)) '{NOME_ICONA}.lnk') }}"])
        return
    for file in _file_icone():
        file.unlink(missing_ok=True)


# Linux: file .desktop nel menu delle applicazioni e sul desktop.

def _file_menu() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / "applications" / "gradiens.desktop"


def _file_icone() -> list[Path]:
    """Il file nel menu e, se c'è un desktop, quello sul desktop."""
    return [_file_menu(), *([desktop / "gradiens.desktop"] if (desktop := _cartella_desktop()) else [])]


def _cartella_desktop() -> Path | None:
    """Il desktop ha il nome nella lingua del sistema (es. ~/Scrivania): lo dice xdg-user-dir. Senza un desktop
    configurato (es. un server) xdg-user-dir risponde con la cartella home: lì l'icona non va."""
    trovata = _esegui(["xdg-user-dir", "DESKTOP"]).stdout.strip() if shutil.which("xdg-user-dir") else ""
    desktop = Path(trovata) if trovata else Path.home() / "Desktop"
    return desktop if desktop.is_dir() and desktop != Path.home() else None


def _argomento_desktop(valore: str) -> str:
    """Argomento di Exec tra virgolette, come chiede la specifica dei file .desktop."""
    for carattere in ("\\", '"', "`", "$"):
        valore = valore.replace(carattere, "\\" + carattere)
    return '"' + valore.replace("%", "%%") + '"'


def voce_desktop(radice: Path, python: str) -> str:
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        f"Name={NOME_ICONA}",
        "Comment=Accendi, spegni e guarda lo stato di Gradiens",
        "Exec=" + " ".join(_argomento_desktop(a) for a in [python, "-m", "gradiens", "pannello"]),
        f"Path={radice}",
        f"Icon={ICONA.with_suffix('.png')}",
        "Terminal=false",
        "Categories=Utility;",
    ]) + "\n"


# Windows: collegamenti .lnk creati con WScript.Shell, che trova anche il desktop spostato su OneDrive.

def script_icone_windows(radice: Path, pythonw: str) -> str:
    return "\n".join([
        "$shell = New-Object -ComObject WScript.Shell",
        "foreach ($cartella in 'Desktop', 'Programs') {",
        f"  $c = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath($cartella)) {_ps(NOME_ICONA + '.lnk')}))",
        f"  $c.TargetPath = {_ps(pythonw)}",
        "  $c.Arguments = '-m gradiens pannello'",
        f"  $c.WorkingDirectory = {_ps(str(radice))}",
        f"  $c.IconLocation = {_ps(str(ICONA.with_suffix('.ico')))}",
        "  $c.Description = 'Accendi, spegni e guarda lo stato di Gradiens'",
        "  $c.Save()",
        "}",
    ])


# ---- Programmi esterni per l'aggiornamento (gradiens aggiorna) ----

def eseguibile(nome: str) -> str | None:
    """`git` o `uv`: dal PATH, oppure da `~/.local/bin`, dove li mettono gli installer ufficiali su Windows e su
    Linux. Il pannello aperto dal menu può avere un PATH senza quella cartella."""
    if trovato := shutil.which(nome):
        return trovato
    locale = Path.home() / ".local" / "bin" / (nome + ".exe" if os.name == "nt" else nome)
    return str(locale) if locale.exists() else None
