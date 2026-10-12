"""Configurar la clave de Groq sin ponerla en archivos ni mostrarla en consola."""
from __future__ import annotations
import argparse
import getpass
import os
from .secrets import read_groq_key, save_groq_key, delete_groq_key


def main(argv=None):
    parser = argparse.ArgumentParser(description='CorePulse AI V463: credencial Groq de pruebas')
    parser.add_argument('action', choices=('configure', 'status', 'delete'))
    args = parser.parse_args(argv)
    if os.name != 'nt':
        print('Credential Manager disponible sólo en Windows. En servidor Linux usa GROQ_API_KEY en un gestor de secretos.')
        return 2
    if args.action == 'status':
        print('Clave Groq configurada.' if read_groq_key() else 'Clave Groq NO configurada.')
        return 0
    if args.action == 'delete':
        delete_groq_key()
        print('Se solicitó quitar la clave de Groq.')
        return 0
    print('Se guardará la clave únicamente en Windows Credential Manager de este usuario.')
    value = getpass.getpass('Groq API Key (entrada oculta): ').strip()
    if not value or len(value) > 4096 or not value.startswith('gsk_'):
        print('Clave no válida: debe tener formato gsk_... y longitud permitida.')
        return 1
    if not save_groq_key(value):
        print('No fue posible guardar la clave en Windows Credential Manager.')
        return 1
    print('Clave guardada. No se escribió en archivos de CorePulse.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
