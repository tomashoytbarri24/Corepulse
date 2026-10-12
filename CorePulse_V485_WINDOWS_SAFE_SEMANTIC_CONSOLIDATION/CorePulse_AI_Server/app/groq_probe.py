"""Solicitud sintética única al modelo Groq; nunca usa sensores del PC."""
from __future__ import annotations
from .model_gateway import model_ready, generate
from .guardrails import validate_model_response
from .evidence import sanitize_context
from .groq_diagnostics import classify_error, print_credential_source


def main():
    print_credential_source()
    if not model_ready():
        print('Falta la clave Groq o la configuración del servidor. Usa 10_CONFIGURAR_GROQ_V463.bat.')
        return 2
    context = sanitize_context({'cpu': {'name': 'Procesador sintético', 'temperature_c': None}})
    try:
        answer = generate(context, '¿Cuál es la temperatura medida de CPU de esta prueba sintética?')
    except Exception as exc:
        # Identificar el problema sin mostrar cuerpos HTTP, prompts, URLs ni secretos.
        code, message = classify_error(exc)
        print('Consulta de prueba fallida:', code)
        print('Qué hacer:', message)
        print('Ejecuta 15_DIAGNOSTICAR_GROQ_V464.bat para verificar la conexión sin enviar una pregunta.')
        return 3
    result = validate_model_response(context, answer)
    if not result['allowed']:
        print('El modelo respondió, pero CorePulse rechazó su salida por las reglas de seguridad.')
        print('Códigos:', ', '.join(result['codes']))
        return 4
    print('Prueba realizada con datos sintéticos y salida aceptada por la política.')
    print('Respuesta:', answer[:900])
    print('Esta prueba no valida el rendimiento ni la precisión diagnóstica del modelo.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
