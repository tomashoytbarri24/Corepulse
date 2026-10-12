"""Utilidades de administración (uso exclusivo en el servidor; sin API pública)."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from .store import issue_pairing_code, revoke_installation, list_installations


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog='python -m app.admin', description='Administrar CorePulse AI Cloud')
    cmds = parser.add_subparsers(dest='action', required=True)
    issue = cmds.add_parser('issue', help='Emitir código de vinculación de un solo uso')
    issue.add_argument('--minutes', type=int, default=30, help='Validez de 1 a 1440 minutos (default: 30)')
    revoke = cmds.add_parser('revoke', help='Revocar un dispositivo por su ID')
    revoke.add_argument('installation_id')
    cmds.add_parser('list', help='Listar dispositivos sin mostrar tokens')
    args = parser.parse_args(argv)
    if args.action == 'issue':
        if not 1 <= args.minutes <= 1440:
            parser.error('--minutes debe estar entre 1 y 1440')
        code, expiry = issue_pairing_code(args.minutes)
        print('Código (mostrar UNA sola vez):', code)
        print('Expira (UTC):', datetime.fromtimestamp(expiry, timezone.utc).isoformat())
        return 0
    if args.action == 'revoke':
        removed = revoke_installation(args.installation_id)
        print('Revocado.' if removed else 'Instalación no encontrada.')
        return 0 if removed else 1
    for installation_id, date, version in list_installations():
        print(f'{installation_id}  {date}  V{version}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
