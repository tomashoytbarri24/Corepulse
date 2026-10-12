"""Estado local de credenciales Groq: cero solicitudes y cero secretos impresos."""
from __future__ import annotations
from .config import GROQ_KEY_SOURCE, GROQ_KEY_CONFLICT, GROQ_KEY_PRESENT_ENV, GROQ_KEY_PRESENT_MANAGER


def main() -> int:
    print('[CorePulse V465] Diagnóstico LOCAL de la clave Groq. SIN conexión a Internet.')
    print('Clave en Credential Manager:', 'PRESENTE' if GROQ_KEY_PRESENT_MANAGER else 'AUSENTE')
    print('GROQ_API_KEY en entorno:', 'PRESENTE' if GROQ_KEY_PRESENT_ENV else 'AUSENTE')
    print('Clave que utiliza CorePulse:', GROQ_KEY_SOURCE)
    if GROQ_KEY_CONFLICT:
        print('ATENCIÓN: Las dos claves son diferentes; prevalece Credential Manager en V465.')
    print('No se muestran ni transmiten credenciales, ni siquiera parcialmente.')
    return 0 if GROQ_KEY_SOURCE != 'NONE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
