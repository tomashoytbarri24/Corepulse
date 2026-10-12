"""Configurar un proveedor externo de API de chat compatible. Nunca imprime API keys."""
from __future__ import annotations
import argparse
import getpass
import os
from .provider_independence import (
    load_provider_settings, save_provider_settings, validate_upstream_url,
    validate_model_id, save_compatible_key, read_compatible_key,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description='CorePulse V472 - proveedor alternativo')
    parser.add_argument('action', choices=('configure', 'status'))
    args = parser.parse_args(argv)
    if args.action == 'status':
        cfg = load_provider_settings()
        print('Endpoint HTTPS:', cfg.get('base_url') or 'SIN CONFIGURAR')
        print('Modelo:', cfg.get('model') or 'SIN CONFIGURAR')
        print('Clave para ESTE endpoint:', 'PRESENTE' if read_compatible_key() else 'AUSENTE')
        return 0 if cfg else 1
    if os.name != 'nt':
        print('El asistente de credenciales requiere Windows Credential Manager.')
        return 2
    print('Introduce SOLO un endpoint de inferencia HTTPS confiable con sufijo /v1.')
    print('Esto NO despliega ni contrata un servidor. No uses el endpoint de chat CorePulse /v1/status.')
    endpoint = validate_upstream_url(input('URL (https://servidor.example/v1): '))
    model = validate_model_id(input('Identificador exacto del modelo: '))
    if not endpoint or not model:
        print('URL o modelo inválidos. No se guardaron datos.')
        return 1
    print('La clave se guarda en Credential Manager; deja vacío si el servidor no requiere clave.')
    key = getpass.getpass('API key (oculta, opcional): ').strip()
    if len(key) > 4096 or '\r' in key or '\n' in key:
        print('Formato de clave inválido.')
        return 1
    # No reemplazar la config si no se pudo proteger la credencial solicitada.
    if key and not save_compatible_key(key, endpoint):
        print('No fue posible guardar la clave de forma segura.')
        return 1
    if not save_provider_settings(endpoint, model):
        print('No fue posible guardar el servidor.')
        return 1
    print('Servidor compatible configurado. Ningún secreto se escribió en el archivo JSON.')
    print('IMPORTANTE: el próximo inicio del puente tendrá que ser manual y consentido.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
