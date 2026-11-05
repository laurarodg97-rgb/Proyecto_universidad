"""Decoradores propios del proyecto."""

from __future__ import annotations

import functools
import logging
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger("simulacion")


def medir_tiempo(funcion: Callable[P, R]) -> Callable[P, R]:
    """Registra en el log cuánto tarda cada llamada."""

    @functools.wraps(funcion)
    def envoltura(*args: P.args, **kwargs: P.kwargs) -> R:
        inicio = time.perf_counter()
        try:
            return funcion(*args, **kwargs)
        finally:
            ms = (time.perf_counter() - inicio) * 1000
            logger.info("%s tardó %.1f ms", funcion.__qualname__, ms)

    return envoltura
