"""L'unico codice che dipende dal sistema operativo (PRD AMB-03, ADR 0005 per Windows, ADR 0007 per Linux).

Oggi: lanciare Gradiens staccato dal terminale. Nella fetta 7: registrare l'avvio all'accensione (AMB-04).
"""

import os
import subprocess
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
