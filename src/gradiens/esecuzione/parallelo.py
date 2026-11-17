"""Compiti lanciati in parallelo sulla sessione condivisa dell'esecuzione."""

import asyncio

from gradiens.llm.base import ErroreBloccante


async def in_parallelo(coroutine) -> list:
    """Esegue in parallelo; al primo errore ferma le altre (la sessione del database è condivisa).
    Un errore bloccante (quota esaurita, login rifiutato) esce come tale anche insieme ad altri errori (S-02);
    un errore solo esce da solo."""
    try:
        async with asyncio.TaskGroup() as gruppo:
            compiti = [gruppo.create_task(c) for c in coroutine]
    except ExceptionGroup as gruppo:
        errori = foglie(gruppo)
        bloccanti = [e for e in errori if isinstance(e, ErroreBloccante)]
        if bloccanti or len(errori) == 1:
            raise (bloccanti or errori)[0] from None
        raise
    return [c.result() for c in compiti]


def foglie(errore: BaseException) -> list[BaseException]:
    """Gli errori veri dentro un gruppo di eccezioni, anche annidato."""
    if isinstance(errore, BaseExceptionGroup):
        return [f for e in errore.exceptions for f in foglie(e)]
    return [errore]
