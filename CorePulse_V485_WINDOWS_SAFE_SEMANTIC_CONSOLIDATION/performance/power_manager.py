"""Control seguro de los planes de energía EXISTENTES de Windows.

V394:
- CorePulse NO crea, duplica ni renombra planes de energía, y no elimina planes nativos/OEM/del usuario.
- Sólo enumera los planes que Windows ya expone y activa el elegido con
  ``powercfg /setactive``.
- Tampoco modifica los parámetros internos (CPU/Boost/EPP) de esos planes.
- Si un modo no está instalado/expuesto por Windows, CorePulse lo informa como
  no disponible en lugar de fabricar una copia propia.
- Corrige la detección localizada de powercfg (incluidos acentos dañados por la
  página de códigos de Windows) y limpia únicamente planes legado con identidad
  CorePulse inequívoca, preservando todos los planes nativos/OEM/del usuario.
"""
from __future__ import annotations

import logging
import json
import uuid
from pathlib import Path
from core.runtime_paths import data_path
import difflib
import os
import re
import unicodedata
from typing import Any, Dict, Optional

from core.windows_commands import CommandResult, friendly_failure, run_hidden

logger = logging.getLogger('CorePulse.Power')

PROCESSOR_SUBGROUP = '54533251-82be-4824-96c1-47b60b740d00'
MAX_PROCESSOR_STATE = 'bc5038f7-23e0-4960-96da-33abaf5935ec'
BOOST_MODE = 'be337238-0d82-4146-a960-4f3749d470c7'
PERF_EPP = '36687f9e-e3a5-4dbf-b1dc-15eb381c6863'

BALANCED_GUID = '381b4222-f694-41f0-9685-ff5bb260df2e'
HIGH_PERFORMANCE_GUID = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
POWER_SAVER_GUID = 'a1841308-3541-4fab-bc81-f71556f20b4a'
ULTIMATE_PERFORMANCE_GUID = 'e9a42b02-d5df-448d-aa00-03f14749eb61'
BALANCED_ALIAS = 'SCHEME_BALANCED'

WINDOWS_MODE_SCHEMES = {
    'BALANCED': BALANCED_GUID,
    'HIGH_PERFORMANCE': HIGH_PERFORMANCE_GUID,
    'MAXIMUM_PERFORMANCE': ULTIMATE_PERFORMANCE_GUID,
    'POWER_SAVER': POWER_SAVER_GUID,
}
WINDOWS_MODE_LABELS = {
    'BALANCED': 'Equilibrado',
    'HIGH_PERFORMANCE': 'Alto rendimiento',
    'MAXIMUM_PERFORMANCE': 'Máximo rendimiento',
    'POWER_SAVER': 'Ahorro de energía',
}
# Nombres que Windows/OEM puede mostrar para los modos nativos.  Se usan sólo
# para ENCONTRAR planes ya existentes cuando el GUID no es el canónico.
WINDOWS_MODE_NAME_ALIASES = {
    'BALANCED': {
        'balanced', 'equilibrado', 'balanceado',
    },
    'HIGH_PERFORMANCE': {
        'high performance', 'alto rendimiento', 'rendimiento alto',
    },
    'MAXIMUM_PERFORMANCE': {
        'ultimate performance', 'maximum performance', 'maximo rendimiento',
        'rendimiento maximo', 'maximo desempeno', 'rendimiento definitivo',
    },
    'POWER_SAVER': {
        'power saver', 'ahorro de energia', 'economizador', 'energy saver',
        'bajo rendimiento',
    },
}

# Compatibilidad de imports históricos. Ya NO representan perfiles que
# CorePulse pueda crear.
COREPULSE_FALLBACK_NAMES = dict(WINDOWS_MODE_LABELS)
COREPULSE_PROFILE_NAMES = dict(WINDOWS_MODE_LABELS)
COREPULSE_PROFILE_ALIASES = {mode: set() for mode in WINDOWS_MODE_SCHEMES}

# Nombres exactos usados por versiones antiguas que sí creaban copias.  Esta
# lista es deliberadamente cerrada: nunca se borra un plan sólo por contener la
# palabra CorePulse ni por parecerse a un plan de Windows.
LEGACY_COREPULSE_PLAN_NAMES = {
    'BALANCED': {'CorePulse - Equilibrado'},
    'HIGH_PERFORMANCE': {'CorePulse - Alto rendimiento', 'CorePulse Game'},
    'MAXIMUM_PERFORMANCE': {'CorePulse - Máximo rendimiento', 'CorePulse Turbo Performance'},
    'POWER_SAVER': {'CorePulse - Ahorro de energía'},
}
LEGACY_COREPULSE_MARKER_PREFIX = 'CorePulse.ManagedPowerPlan/v1;mode='

GUID_RE = re.compile(r'(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b')
HEX_RE = re.compile(r'(?i)0x([0-9a-f]+)')
PAREN_NAME_RE = re.compile(r'\(([^()]*)\)')


class PowerManager:
    def __init__(self, runner=run_hidden, *, registry_path=None, description_reader=None, scheme_restorer=None):
        self.runner = runner
        self.scheme_restorer = scheme_restorer or (self._restore_default_native if runner is run_hidden else None)
        self.managed_plans = ManagedPowerPlans(self, registry_path, description_reader=description_reader)

    def _run(self, args, timeout=12) -> CommandResult:
        # powercfg.exe escribe texto localizado con la página de códigos OEM.
        # Usar UTF-8 a la fuerza degrada acentos en Windows en algunos equipos y
        # puede convertir "Máximo rendimiento" en "M�ximo rendimiento".
        if self.runner is run_hidden:
            return self.runner(args, timeout=timeout, category='POWER', encoding='oem')
        return self.runner(args, timeout=timeout, category='POWER')

    def available(self) -> bool:
        return os.name == 'nt'

    def active_scheme(self) -> Dict[str, Any]:
        if not self.available():
            return {'success': False, 'guid': None, 'message': 'powercfg sólo está disponible en Windows.'}
        result = self._run(['powercfg', '/getactivescheme'])
        if not result.ok:
            return {'success': False, 'guid': None, 'message': friendly_failure(result, 'consultar el plan de energía'), 'result': result}
        match = GUID_RE.search(result.stdout)
        if not match:
            logger.error('[POWER] No se pudo extraer GUID de /getactivescheme: %s', result.stdout[:1000])
            return {'success': False, 'guid': None, 'message': 'Windows respondió sin un GUID de plan de energía reconocible.'}
        return {'success': True, 'guid': match.group(0).lower(), 'raw': result.stdout}

    def list_schemes(self) -> Dict[str, Any]:
        """Enumera planes existentes sin depender del idioma de Windows."""
        if not self.available():
            return {'success': False, 'schemes': {}, 'message': 'Los planes de energía sólo están disponibles en Windows.'}
        result = self._run(['powercfg', '/list'])
        if not result.ok:
            return {'success': False, 'schemes': {}, 'message': friendly_failure(result, 'listar los planes de energía'), 'result': result}
        schemes: Dict[str, Dict[str, Any]] = {}
        for line in str(result.stdout or '').splitlines():
            match = GUID_RE.search(line)
            if not match:
                continue
            guid = match.group(0).lower()
            tail = line[match.end():]
            name_match = PAREN_NAME_RE.search(tail)
            name = (name_match.group(1).strip() if name_match else '').strip()
            schemes[guid] = {
                'guid': guid,
                'name': name or guid,
                'active': '*' in tail,
                'raw': line.strip(),
            }
        return {'success': True, 'schemes': schemes, 'raw': result.stdout}

    @staticmethod
    def _repair_mojibake(value: object) -> str:
        """Repara mojibake UTF-8/ANSI común sin inventar caracteres perdidos."""
        text = str(value or '').strip()
        # Caso típico: "MÃ¡ximo" por bytes UTF-8 interpretados como cp1252.
        for enc in ('cp1252', 'latin1'):
            try:
                fixed = text.encode(enc).decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError, LookupError):
                continue
            bad_before = text.count('Ã') + text.count('Â') + text.count('�')
            bad_after = fixed.count('Ã') + fixed.count('Â') + fixed.count('�')
            if bad_after < bad_before:
                text = fixed
                break
        return text

    @classmethod
    def _normalise_plan_name(cls, value: object) -> str:
        raw = cls._repair_mojibake(value).casefold()
        raw = unicodedata.normalize('NFKD', raw)
        raw = ''.join(ch for ch in raw if not unicodedata.combining(ch))
        # U+FFFD significa que el byte original ya se perdió. Quitarlo permite
        # comparar de forma tolerante "mximo rendimiento" con "maximo rendimiento".
        raw = raw.replace('\ufffd', '')
        raw = re.sub(r'[^a-z0-9]+', ' ', raw)
        return ' '.join(raw.split())

    @classmethod
    def _legacy_mode_for_name(cls, value: object) -> Optional[str]:
        normalized = cls._normalise_plan_name(value)
        for mode, names in LEGACY_COREPULSE_PLAN_NAMES.items():
            if normalized in {cls._normalise_plan_name(name) for name in names}:
                return mode
        return None

    @classmethod
    def _mode_name_matches(cls, mode: str, value: object) -> bool:
        """Compara nombres nativos soportando acentos/mojibake sin falsos positivos."""
        normalized = cls._normalise_plan_name(value)
        if not normalized or 'corepulse' in normalized.split():
            return False
        aliases = {cls._normalise_plan_name(x) for x in WINDOWS_MODE_NAME_ALIASES[mode]}
        if normalized in aliases:
            return True
        # Si powercfg ya devolvió U+FFFD no podemos recuperar la vocal acentuada.
        # Un umbral alto corrige esa pérdida (mximo/maximo, energ a/energia) sin
        # confundir Alto rendimiento con Máximo rendimiento.
        return any(
            difflib.SequenceMatcher(None, normalized, alias).ratio() >= 0.90
            for alias in aliases if alias
        )

    def _resolve_existing_mode_from_schemes(self, mode: str, schemes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        mode = str(mode or '').strip().upper()
        if mode not in WINDOWS_MODE_SCHEMES:
            return {'success': False, 'message': f'Modo de energía no soportado: {mode}'}

        canonical = WINDOWS_MODE_SCHEMES[mode]
        if canonical in schemes:
            row = schemes[canonical]
            return {
                'success': True, 'guid': canonical, 'mode': mode,
                'name': row.get('name') or WINDOWS_MODE_LABELS[mode],
                'created': False, 'builtin': True, 'existing_only': True,
            }

        matches = []
        for guid, row in schemes.items():
            # Copias creadas por CorePulse en versiones antiguas jamás cuentan
            # como un plan nativo disponible, aunque estén todavía instaladas.
            if self._legacy_mode_for_name(row.get('name')):
                continue
            if self._mode_name_matches(mode, row.get('name')):
                matches.append((guid, row))
        if matches:
            matches.sort(key=lambda item: (not bool(item[1].get('active')), item[0]))
            guid, row = matches[0]
            return {
                'success': True, 'guid': guid, 'mode': mode,
                'name': row.get('name') or WINDOWS_MODE_LABELS[mode],
                'created': False, 'builtin': False, 'existing_only': True,
            }

        return {
            'success': False, 'mode': mode,
            'message': (
                f'Windows no expone actualmente el plan {WINDOWS_MODE_LABELS[mode]}. '
                'CorePulse no crea ni duplica planes de energía; habilítalo desde Windows/OEM si deseas usarlo.'
            ),
            'existing_only': True,
        }

    def resolve_existing_mode_scheme(self, mode: str) -> Dict[str, Any]:
        """Devuelve un plan YA EXISTENTE leído de ``powercfg /list``."""
        mode = str(mode or '').strip().upper()
        if mode not in WINDOWS_MODE_SCHEMES:
            return {'success': False, 'message': f'Modo de energía no soportado: {mode}'}
        listed = self.list_schemes()
        if not listed.get('success'):
            return listed
        return self._resolve_existing_mode_from_schemes(mode, listed.get('schemes') or {})

    def available_native_modes(self, *, schemes: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Devuelve sólo los planes reales Windows/OEM disponibles en el equipo."""
        if schemes is None:
            listed = self.list_schemes()
            if not listed.get('success'):
                return {'success': False, 'modes': [], 'plans': {}, 'message': listed.get('message')}
            schemes = listed.get('schemes') or {}
        plans: Dict[str, Dict[str, Any]] = {}
        for mode in WINDOWS_MODE_SCHEMES:
            found = self._resolve_existing_mode_from_schemes(mode, schemes)
            if found.get('success'):
                plans[mode] = {
                    'mode': mode,
                    'guid': found.get('guid'),
                    'name': found.get('name') or WINDOWS_MODE_LABELS[mode],
                    'active': bool((schemes.get(found.get('guid')) or {}).get('active')),
                }
        return {'success': True, 'modes': list(plans), 'plans': plans}

    def mode_for_scheme(self, guid: Optional[str], schemes: Optional[Dict[str, Any]] = None) -> Optional[str]:
        token = str(guid or '').lower().strip()
        for mode, builtin in WINDOWS_MODE_SCHEMES.items():
            if token == builtin:
                return mode
        rows = schemes or {}
        row = rows.get(token) or {}
        if self._legacy_mode_for_name(row.get('name')):
            return None
        for mode in WINDOWS_MODE_NAME_ALIASES:
            if self._mode_name_matches(mode, row.get('name')):
                return mode
        return None

    def active_windows_plan(self) -> Dict[str, Any]:
        active = self.active_scheme()
        if not active.get('success'):
            return active
        listed = self.list_schemes()
        schemes = listed.get('schemes') if listed.get('success') else {}
        guid = str(active.get('guid') or '').lower()
        row = (schemes or {}).get(guid) or {}
        mode = self.mode_for_scheme(guid, schemes)
        available = self.available_native_modes(schemes=schemes) if listed.get('success') else {'success': False, 'modes': [], 'plans': {}}
        return {
            'success': True,
            'guid': guid,
            'name': row.get('name') or guid,
            'mode': mode,
            'known_mode': bool(mode),
            'list_success': bool(listed.get('success')),
            'available_modes': list(available.get('modes') or []),
            'available_plans': dict(available.get('plans') or {}),
        }

    def cleanup_legacy_corepulse_plans(self) -> Dict[str, Any]:
        """Elimina únicamente copias históricas con nombre CorePulse inequívoco.

        Nunca toca GUID canónicos ni planes OEM/usuario. Si una copia antigua está
        activa, cambia primero a un plan nativo existente y verifica el cambio.
        """
        listed = self.list_schemes()
        if not listed.get('success'):
            return {'success': False, 'changed': False, 'removed': [], 'message': listed.get('message')}
        schemes = dict(listed.get('schemes') or {})
        legacy = {}
        registry = self.managed_plans.read().get('plans') or {}
        for guid, row in schemes.items():
            if guid in WINDOWS_MODE_SCHEMES.values():
                continue
            name_mode = self._legacy_mode_for_name(row.get('name'))
            record = registry.get(guid) if isinstance(registry, dict) else None
            record_mode = (record or {}).get('mode') if isinstance(record, dict) else None
            owned_record = bool(self.managed_plans.owned_record(record or {}))
            description = self.managed_plans.description(guid)
            marker_owned = str(description or '').startswith(LEGACY_COREPULSE_MARKER_PREFIX)
            # Tres pruebas válidas de procedencia: nombre exacto reservado por
            # CorePulse, registro persistente firmado por versiones previas o
            # descripción Windows con nuestro marcador histórico.
            if not (name_mode or owned_record or marker_owned):
                continue
            mode = name_mode or (record_mode if record_mode in WINDOWS_MODE_SCHEMES else None)
            if mode is None and marker_owned:
                marker_mode = str(description).split('mode=', 1)[-1].split(';', 1)[0].strip().upper()
                mode = marker_mode if marker_mode in WINDOWS_MODE_SCHEMES else None
            legacy[guid] = {'mode': mode, 'description': description, **row}
        if not legacy:
            return {'success': True, 'changed': False, 'removed': [], 'message': 'No hay planes legado de CorePulse.'}

        active = self.active_scheme()
        if not active.get('success'):
            return {'success': False, 'changed': False, 'removed': [], 'message': active.get('message')}
        active_guid = str(active.get('guid') or '').lower()
        switched_to = None

        if active_guid in legacy:
            # Preferimos Equilibrado y luego cualquier otro modo nativo reconocido.
            fallback = None
            remaining = {g: row for g, row in schemes.items() if g not in legacy}
            for mode in ('BALANCED', 'MAXIMUM_PERFORMANCE', 'HIGH_PERFORMANCE', 'POWER_SAVER'):
                found = self._resolve_existing_mode_from_schemes(mode, remaining)
                if found.get('success'):
                    fallback = found
                    break
            # Último recurso: conservar cualquier plan no-CorePulse existente.
            if fallback is None and remaining:
                guid, row = sorted(remaining.items(), key=lambda item: item[0])[0]
                fallback = {'success': True, 'guid': guid, 'name': row.get('name') or guid}
            if fallback is None:
                return {
                    'success': False, 'changed': False, 'removed': [],
                    'message': 'La copia antigua de CorePulse está activa y no existe otro plan seguro al que cambiar antes de eliminarla.',
                }
            switched = self.set_active(str(fallback.get('guid') or ''))
            if not switched.get('success'):
                return {
                    'success': False, 'changed': False, 'removed': [],
                    'message': 'No se pudo salir del plan legado activo antes de limpiarlo: ' + str(switched.get('message') or ''),
                }
            switched_to = str(fallback.get('guid') or '').lower()
            active_guid = switched_to

        removed = []
        failures = []
        for guid, row in sorted(legacy.items()):
            if guid == active_guid:
                failures.append(f'{row.get("name")}: seguía activo')
                continue
            result = self._run(['powercfg', '/delete', guid])
            if not result.ok:
                failures.append(f'{row.get("name")}: {friendly_failure(result, "eliminar el plan legado de CorePulse")}')
                continue
            removed.append({'guid': guid, 'name': row.get('name'), 'mode': row.get('mode')})

        verify = self.list_schemes()
        if verify.get('success'):
            still_present = verify.get('schemes') or {}
            for item in list(removed):
                if item['guid'] in still_present:
                    removed.remove(item)
                    failures.append(f'{item.get("name")}: Windows no confirmó la eliminación')

        success = not failures
        if removed:
            logger.info('[POWER] Planes legado CorePulse eliminados: %s', ', '.join(item['name'] for item in removed))
        if failures:
            logger.warning('[POWER] Limpieza legado parcial: %s', ' | '.join(failures))
        return {
            'success': success,
            'partial': bool(failures and removed),
            'changed': bool(removed or switched_to),
            'removed': removed,
            'failures': failures,
            'switched_to': switched_to,
            'message': (
                f'Se eliminaron {len(removed)} plan(es) legado de CorePulse.'
                if success else
                f'Limpieza parcial: {len(removed)} eliminado(s), {len(failures)} pendiente(s).'
            ),
        }

    @staticmethod
    def _restore_default_native(guid):
        import ctypes as c
        import uuid
        dll = c.WinDLL('powrprof')
        token = c.create_string_buffer(uuid.UUID(guid).bytes_le, 16)
        for name in ('PowerCanRestoreIndividualDefaultPowerScheme', 'PowerRestoreIndividualDefaultPowerScheme'):
            fn = getattr(dll, name)
            fn.argtypes = [c.c_void_p]
            fn.restype = c.c_uint32
            code = fn(token)
            if code:
                return {'success': False, 'message': f'Windows no pudo recuperar Equilibrado: {c.FormatError(code).strip()} (código {code}).'}
        return {'success': True}

    def restore_missing_balanced(self):
        # Compatibilidad de API: V393 ya no restaura/crea plantillas.
        return self.resolve_existing_mode_scheme('BALANCED')

    def ensure_mode_scheme(self, mode: str, *, protected_guids=()) -> Dict[str, Any]:
        del protected_guids
        return self.resolve_existing_mode_scheme(mode)

    def ensure_owned_profile(self, profile, *, protected_guids=()):
        # Nombre legado del método. Desde V393 nunca fabrica un perfil propio.
        mode = {
            'GAME': 'HIGH_PERFORMANCE', 'TURBO': 'MAXIMUM_PERFORMANCE',
            'COREPULSE GAME': 'HIGH_PERFORMANCE',
            'COREPULSE TURBO PERFORMANCE': 'MAXIMUM_PERFORMANCE',
        }.get(str(profile).upper(), str(profile).upper())
        return self.ensure_mode_scheme(mode, protected_guids=protected_guids)

    def reconcile_owned_profiles(self, *, protected_guids=()):
        # V394: migración unidireccional. Sólo elimina nombres legado exactos de
        # CorePulse; jamás crea/renombra esquemas ni toca planes Windows/OEM.
        del protected_guids
        return self.cleanup_legacy_corepulse_plans()

    @staticmethod
    def _parse_ac_dc(output: str) -> Optional[Dict[str, int]]:
        values = [int(x, 16) for x in HEX_RE.findall(str(output or ''))]
        if len(values) < 2:
            return None
        return {'ac': values[-2], 'dc': values[-1]}

    @staticmethod
    def _setting_block(output: str, setting: str) -> Optional[str]:
        raw = str(output or '')
        low = raw.lower()
        token = str(setting or '').lower()
        pos = low.find(token)
        if pos < 0:
            return None
        tail = raw[pos + len(token):]
        nxt = GUID_RE.search(tail)
        end = pos + len(token) + (nxt.start() if nxt else len(tail))
        return raw[pos:end]

    def query_setting(self, scheme: str, setting: str) -> Dict[str, Any]:
        attempts = []
        for verb in ('/qh', '/query'):
            result = self._run(['powercfg', verb, str(scheme), PROCESSOR_SUBGROUP])
            attempts.append(result)
            if not result.ok:
                continue
            block = self._setting_block(result.stdout, setting)
            if block is None:
                continue
            parsed = self._parse_ac_dc(block)
            if parsed is not None:
                return {'success': True, **parsed, 'query_mode': verb}
        last = attempts[-1] if attempts else None
        if last is not None and not last.ok:
            message = friendly_failure(last, 'consultar la configuración del procesador')
        else:
            message = 'Windows no expuso este ajuste de energía con valores AC/DC interpretables.'
        return {'success': False, 'message': message, 'attempts': attempts}

    def snapshot_scheme(self, guid: str) -> Dict[str, Any]:
        settings: Dict[str, Any] = {}
        unavailable: Dict[str, str] = {}
        keys = (('max_processor_state', MAX_PROCESSOR_STATE), ('boost_mode', BOOST_MODE),
                ('energy_performance_preference', PERF_EPP))
        for verb in ('/qh', '/query'):
            result = self._run(['powercfg', verb, str(guid), PROCESSOR_SUBGROUP])
            if not result.ok:
                continue
            for name, setting in keys:
                if name in settings:
                    continue
                block = self._setting_block(result.stdout, setting)
                parsed = self._parse_ac_dc(block) if block is not None else None
                if parsed is not None:
                    settings[name] = {'setting_guid': setting, **parsed, 'query_mode': verb}
            if len(settings) == len(keys):
                break
        for name, setting in keys:
            if name not in settings:
                unavailable[name] = 'Windows no expuso valores AC/DC interpretables.'
        capabilities = {
            'max_processor_state': 'max_processor_state' in settings,
            'boost_mode': 'boost_mode' in settings,
            'energy_performance_preference': 'energy_performance_preference' in settings,
        }
        return {
            'success': True,
            'guid': str(guid).lower(),
            'settings': settings,
            'unavailable': unavailable,
            'capabilities': capabilities,
            'partial': not all(capabilities.values()),
        }

    def snapshot(self) -> Dict[str, Any]:
        """Guarda el plan activo exacto y, cuando sea posible, sus ajustes.

        Desde V0.10.2.53w el rollback del PLAN no depende de que el OEM exponga
        PERFBOOSTMODE/EPP: conocer el GUID activo basta para restaurar el plan.
        """
        active = self.active_scheme()
        if not active.get('success'):
            return {'success': False, 'message': active.get('message'), 'original': None}
        guid = active['guid']
        snap = self.snapshot_scheme(guid)
        return {
            'success': True,
            'partial': bool(snap.get('partial')),
            'message': (
                'Plan de energía y ajustes reversibles respaldados.'
                if not snap.get('partial')
                else 'Plan de energía respaldado; algunos ajustes avanzados no son legibles en este equipo/OEM.'
            ),
            'original': {
                'active_scheme_guid': guid,
                'settings': snap.get('settings') or {},
                'unavailable': snap.get('unavailable') or {},
                'capabilities': snap.get('capabilities') or {},
            },
        }

    def _set_value(self, scheme: str, setting: str, ac: Optional[int] = None, dc: Optional[int] = None) -> Dict[str, Any]:
        changes = []
        if ac is not None:
            r = self._run(['powercfg', '/setacvalueindex', scheme, PROCESSOR_SUBGROUP, setting, str(int(ac))])
            changes.append(('AC', r))
            if not r.ok:
                return {'success': False, 'message': friendly_failure(r, 'aplicar la configuración AC del procesador'), 'changes': changes}
        if dc is not None:
            r = self._run(['powercfg', '/setdcvalueindex', scheme, PROCESSOR_SUBGROUP, setting, str(int(dc))])
            changes.append(('DC', r))
            if not r.ok:
                return {'success': False, 'message': friendly_failure(r, 'aplicar la configuración DC del procesador'), 'changes': changes}
        return {'success': True, 'changes': changes}

    def set_active(self, scheme: str, *, verify: bool = True) -> Dict[str, Any]:
        target = str(scheme).lower().strip()
        r = self._run(['powercfg', '/setactive', target])
        if not r.ok:
            return {'success': False, 'message': friendly_failure(r, 'activar el plan de energía'), 'result': r}
        if not verify:
            return {'success': True, 'guid': target}
        current = self.active_scheme()
        if not current.get('success'):
            return {'success': False, 'message': 'Windows aceptó el cambio, pero CorePulse no pudo verificar qué plan quedó activo.'}
        if str(current.get('guid') or '').lower() != target:
            return {
                'success': False,
                'message': 'Windows no dejó activo el plan solicitado. CorePulse no marcará el cambio como aplicado.',
                'requested_guid': target,
                'active_guid': current.get('guid'),
            }
        return {'success': True, 'guid': target, 'verified': True}

    def delete_scheme(self, scheme: str, *, creation_record=None) -> Dict[str, Any]:
        guid = str(scheme or '').lower().strip()
        if not GUID_RE.fullmatch(guid):
            return {'success': False, 'message': 'GUID de plan inválido; no se eliminó nada.'}
        if guid in WINDOWS_MODE_SCHEMES.values():
            return {'success': False, 'message': 'No se eliminan planes estándar de Windows.'}
        listed = self.list_schemes()
        if not listed.get('success'):
            return listed
        if guid not in listed['schemes']:
            return {'success': True, 'guid': guid, 'already_absent': True}
        row = listed['schemes'][guid]
        if not self.managed_plans.owns(guid):
            # Un backup transaccional antiguo también sirve como procedencia,
            # pero sólo si coincide exactamente con uno de nuestros nombres
            # reservados históricos. Un nombre parecido nunca autoriza borrado.
            mode = str((creation_record or {}).get('mode') or '').upper().strip()
            legacy_names = LEGACY_COREPULSE_PLAN_NAMES.get(mode, set())
            row_name = str(row.get('name') or '')
            record_name = str((creation_record or {}).get('name') or '')
            if not (
                row_name == record_name
                and self._normalise_plan_name(row_name) in {self._normalise_plan_name(x) for x in legacy_names}
            ):
                return {'success': False, 'message': 'Procedencia CorePulse no demostrada; plan conservado.'}
        active = self.active_scheme()
        if not active.get('success'):
            return active
        if active.get('guid') == guid:
            return {'success': False, 'message': 'No se elimina el plan activo.'}
        r = self._run(['powercfg', '/delete', guid])
        if not r.ok:
            return {'success': False, 'message': friendly_failure(r, 'eliminar el plan temporal de CorePulse'), 'result': r}
        return {'success': True, 'guid': guid}

    def restore_scheme_settings(self, scheme: str, settings: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        for key in ('max_processor_state', 'boost_mode', 'energy_performance_preference'):
            item = (settings or {}).get(key) or {}
            if item.get('setting_guid') is None:
                continue
            if item.get('ac') is None and item.get('dc') is None:
                continue
            result = self._set_value(scheme, item.get('setting_guid'), item.get('ac'), item.get('dc'))
            if not result.get('success'):
                return result
        return {'success': True}

    def _apply_profile_values(
        self, scheme: str, settings: Optional[Dict[str, Any]], *,
        profile: str, label: str, max_cpu: int, boost_value: Optional[int], epp_value: Optional[int],
    ) -> Dict[str, Any]:
        """Activa un plan existente sin reescribir sus parámetros internos."""
        del settings, max_cpu, boost_value, epp_value
        logger.info('[PROFILE] Activando plan Windows existente %s (%s)', label, scheme)
        active = self.set_active(scheme)
        if not active.get('success'):
            return active
        return {
            'success': True,
            'profile': profile,
            'windows_plan_guid': str(scheme).lower(),
            'windows_plan_verified': True,
            'partial': False,
            'boost_managed': False,
            'epp_managed': False,
            'native_plan_untouched': True,
            'message': f'{label}: plan existente de Windows activo y verificado. CorePulse no modificó sus parámetros.',
        }

    def apply_balanced(self, scheme: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._apply_profile_values(scheme, settings, profile='BALANCED', label='Equilibrado', max_cpu=100, boost_value=1, epp_value=50)

    def apply_high_performance(self, scheme: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._apply_profile_values(scheme, settings, profile='HIGH_PERFORMANCE', label='Alto rendimiento', max_cpu=100, boost_value=1, epp_value=20)

    def apply_maximum_performance(self, scheme: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._apply_profile_values(scheme, settings, profile='MAXIMUM_PERFORMANCE', label='Máximo rendimiento', max_cpu=100, boost_value=1, epp_value=0)

    def apply_power_saver(self, scheme: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._apply_profile_values(scheme, settings, profile='POWER_SAVER', label='Ahorro de energía', max_cpu=80, boost_value=0, epp_value=80)

    def apply_gaming(self, scheme: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.apply_maximum_performance(scheme, settings)

    def apply_cool(self, scheme: str, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.apply_power_saver(scheme, settings)

    def restore(self, backup: Dict[str, Any]) -> Dict[str, Any]:
        original = (backup or {}).get('original') if isinstance(backup, dict) else None
        if not isinstance(original, dict):
            return {'success': False, 'message': 'No existe una copia de configuración válida para restaurar.'}
        original_scheme = str(original.get('active_scheme_guid') or '').lower().strip()
        if not original_scheme:
            return {'success': False, 'message': 'La copia no contiene el plan de energía original.'}

        sync = (backup or {}).get('windows_plan_sync') or {}
        snapshots = sync.get('scheme_snapshots') or {}
        created = sync.get('created_schemes') or {}

        # Restaurar ajustes de cualquier plan existente que CorePulse haya tocado.
        for guid, row in snapshots.items():
            restored = self.restore_scheme_settings(guid, (row or {}).get('settings') or {})
            if not restored.get('success'):
                return {
                    'success': False,
                    'message': f'No se pudieron restaurar los ajustes originales del plan {guid}: {restored.get("message")}',
                }

        # Compatibilidad con backups V0.10.2.53w y anteriores.
        if not snapshots and original.get('settings'):
            restored = self.restore_scheme_settings(original_scheme, original.get('settings') or {})
            if not restored.get('success'):
                return restored

        active = self.set_active(original_scheme)
        if not active.get('success'):
            return active

        # Sólo después de volver al plan original es seguro borrar copias creadas.
        cleanup_errors = []
        for guid, row in created.items():
            guid = str(guid).lower()
            if guid == original_scheme:
                continue
            deleted = self.delete_scheme(guid, creation_record=row)
            if not deleted.get('success'):
                cleanup_errors.append(deleted.get('message') or guid)

        if cleanup_errors:
            return {
                'success': False,
                'partial': True,
                'message': 'El plan original fue restaurado, pero quedó una copia temporal de CorePulse sin eliminar: ' + ' | '.join(cleanup_errors),
            }

        logger.info('[PROFILE] Plan y configuración de energía originales restaurados')
        return {
            'success': True,
            'profile': self.mode_for_scheme(original_scheme),
            'windows_plan_guid': original_scheme,
            'windows_plan_verified': True,
            'message': 'Plan de energía y configuración anterior restaurados.',
        }

    def activate_balanced_default(self) -> Dict[str, Any]:
        ensured = self.ensure_mode_scheme('BALANCED')
        if not ensured.get('success'):
            return ensured
        active = self.set_active(ensured['guid'])
        if active.get('success'):
            return {
                'success': True,
                'profile': 'BALANCED',
                'windows_plan_guid': ensured['guid'],
                'message': 'Plan Equilibrado de Windows activado y verificado.',
            }
        return active


# V480: compatibilidad de registro de planes gestionada por su único consumidor.

class ManagedPowerPlans:
    """Capa de compatibilidad *read-only* para metadatos históricos."""

    def __init__(self, power, path=None, description_reader=None):
        self.power = power
        self.path = Path(path) if path is not None else data_path('managed_power_plans.json')
        self.description_reader = description_reader or self._windows_description

    @staticmethod
    def _windows_description(guid):
        # API pública de Windows: sólo lectura de metadatos del esquema.
        if os.name != 'nt':
            return None
        try:
            import ctypes as c
            reader = c.WinDLL('powrprof').PowerReadDescription
            reader.argtypes = [c.c_void_p] * 5 + [c.POINTER(c.c_uint32)]
            reader.restype = c.c_uint32
            token = c.create_string_buffer(uuid.UUID(str(guid)).bytes_le, 16)
            size = c.c_uint32()
            code = reader(None, token, None, None, None, c.byref(size))
            if code not in (0, 234) or not 2 <= size.value <= 65536:
                return None
            buffer = c.create_string_buffer(size.value)
            if reader(None, token, None, None, buffer, c.byref(size)) != 0:
                return None
            return buffer.raw[:size.value].decode('utf-16-le').rstrip(chr(0))
        except (OSError, ValueError, UnicodeError, AttributeError):
            return None

    def description(self, guid):
        try:
            return self.description_reader(str(guid)) if callable(self.description_reader) else None
        except Exception:
            logger.exception('No se pudo leer la descripción del plan %s', guid)
            return None

    def read(self):
        if not self.path.exists():
            return {'version': 1, 'plans': {}, 'preferred': {}}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
        except Exception:
            logger.exception('No se pudo leer el registro histórico de planes CorePulse')
            return {'version': 1, 'plans': {}, 'preferred': {}}
        if not isinstance(data, dict):
            return {'version': 1, 'plans': {}, 'preferred': {}}
        plans = data.get('plans') if isinstance(data.get('plans'), dict) else {}
        preferred = data.get('preferred') if isinstance(data.get('preferred'), dict) else {}
        return {'version': 1, 'plans': plans, 'preferred': preferred}

    @staticmethod
    def owned_record(row):
        mode = (row or {}).get('mode')
        return (
            mode in WINDOWS_MODE_SCHEMES
            and (row or {}).get('owned') is True
            and (row or {}).get('base') == WINDOWS_MODE_SCHEMES[mode]
        )

    def owns(self, guid):
        try:
            return self.owned_record(self.read()['plans'].get(str(guid or '').lower(), {}))
        except Exception:
            return False

    def ensure(self, mode, *, protected_guids=(), require_owned=False):
        """Compatibilidad de API: resuelve únicamente un plan ya existente."""
        del protected_guids, require_owned
        return self.power.resolve_existing_mode_scheme(mode)

    def reconcile(self, *, protected_guids=()):
        """Compatibilidad: delega la limpieza V394 sin crear ni renombrar planes."""
        del protected_guids
        return self.power.cleanup_legacy_corepulse_plans()
