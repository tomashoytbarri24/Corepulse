"""Resolución diferida de importaciones históricas para módulos fusionados en V481.

No se cargan sensores, Tk ni servicios cuando se importa core/gui: las rutas
antiguas se resuelven únicamente si un consumidor externo las solicita.
"""
from __future__ import annotations
import importlib
import importlib.util
import sys

_ALIASES: dict[str,str] = {}

class _ConsolidatedFinder:
    def find_spec(self, fullname, path=None, target=None):
        replacement = _ALIASES.get(fullname)
        if replacement is None:
            return None
        return importlib.util.spec_from_loader(fullname, self, origin='corepulse-consolidated:' + replacement)

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        replacement = _ALIASES[module.__name__]
        destination = importlib.import_module(replacement)
        for name, value in vars(destination).items():
            if not name.startswith('__'):
                module.__dict__[name] = value
        module.__doc__ = destination.__doc__
        # V485: los helpers privados originales tenían semánticas distintas
        # de los nombres homónimos en los módulos de destino.
        old = module.__name__
        if old in ('core.health_history', 'core.diagnostics.health_history'):
            module.__dict__['_num'] = destination._health_history_num
        elif old in ('core.frozen_selftest', 'core.runtime.frozen_selftest'):
            module.__dict__['_is_admin'] = destination._selftest_is_admin
            module.__dict__['_find_rtss'] = destination._selftest_find_rtss

_FINDER = _ConsolidatedFinder()

def install(aliases: dict[str,str]) -> None:
    _ALIASES.update(aliases)
    if _FINDER not in sys.meta_path:
        sys.meta_path.append(_FINDER)
