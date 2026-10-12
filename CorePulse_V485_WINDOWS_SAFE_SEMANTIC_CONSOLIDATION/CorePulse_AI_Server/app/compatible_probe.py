"""Prueba sintética de un proveedor ya configurado; no usa telemetría real."""
from __future__ import annotations
from .model_gateway import generate, model_ready
from .guardrails import validate_model_response


def main():
    if not model_ready():
        print('MODEL_NOT_CONFIGURED: prepara un servidor HTTPS real con BAT 18.')
        return 2
    print('Enviando una consulta sintética al proveedor elegido.')
    context = {'cpu': {'name': None, 'temperature_c': None}, 'decision': {'attention_areas': []}}
    try:
        output = generate(context, '¿Cuál es la temperatura medida de CPU? Si falta, responde N/A.')
        checked = validate_model_response(context, output)
        if not checked.get('allowed'):
            print('Respuesta del modelo rechazada por el Safety Gate. No se muestran datos del proveedor.')
            return 1
        print('Respuesta aceptada por filtros automáticos (no prueba de diagnóstico):', output[:220])
        return 0
    except Exception:
        print('ERROR_MODELO: consulta no completada. Revisa el servidor y sus permisos.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
