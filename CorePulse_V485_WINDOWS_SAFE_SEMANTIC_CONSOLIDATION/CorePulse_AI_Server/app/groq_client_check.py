"""Revisión local del agente HTTP; no accede a secretos ni a Internet."""
from . import model_gateway


def main():
    print('[CorePulse V466] Verificación LOCAL del cliente HTTPS de Groq.')
    # No consultar MODEL_API_KEY ni imprimir ninguna cabecera Authorization.
    user_agent = model_gateway._headers().get('User-Agent', '')
    if model_gateway.MODEL_PROVIDER != 'groq':
        print('Resultado: GROQ_MODE_DISABLED')
        return 2
    if not user_agent.startswith('CorePulse-AI/'):
        print('Resultado: GROQ_CLIENT_HEADER_MISSING')
        return 3
    print('Resultado: GROQ_CLIENT_HEADER_READY')
    print('Cliente:', user_agent)
    print('Sin solicitudes de red y sin mostrar ni transmitir credenciales.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
