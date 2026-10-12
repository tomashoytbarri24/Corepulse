"""Cierra la integración visual y contractual de los módulos principales de la interfaz."""
from __future__ import annotations
# Código refactorizado: nombres estables y documentación en español.
import json
import time
from pathlib import Path
from core.runtime_paths import log_dir
from core.version import VERSION_LABEL, STAGE, REAL_DATA_POLICY, FPS_POLICY
VERSION = VERSION_LABEL
DESIGN_ID = 'COREPULSE_RUNTIME_INTEGRATION'

def _exists(widget):
    try:
        return bool(widget is not None and widget.winfo_exists())
    except Exception:
        return False

def _runtime_contract(app):
    checks = {'dashboard_exists': _exists(getattr(app, 'main_content', None)), 'sidebar_exists': _exists(getattr(app, 'sidebar', None)), 'summary_button_exists': _exists(getattr(app, '_btn_summary', None)), 'agent_card_exists': _exists(getattr(app, '_agent_card', None)), 'fast_diagnostic_wired': hasattr(app, 'diagnostic_session'), 'overlay_config_wired': hasattr(app, 'open_overlay_config_window'), 'smart_alerts_wired': hasattr(app, 'open_smart_alert_window'), 'history_wired': hasattr(app, 'open_alert_history_window'), 'trends_wired': hasattr(app, 'open_session_trends_window'), 'tray_wired': hasattr(app, 'tray_service')}
    result = {'version': VERSION_LABEL, 'stage': STAGE, 'timestamp': time.time(), 'real_data_policy': REAL_DATA_POLICY, 'fps_policy': FPS_POLICY, 'checks': checks, 'passed': all(checks.values())}
    return result

def _write_log(app, result):
    try:
        folder = log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / 'runtime_contract.json'
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        app._contract_log_path = str(path)
    except Exception:
        app._contract_log_path = None

def apply_runtime_integration(app):
    if getattr(app, '_integration_active', False):
        return getattr(app, '_integration_contract', None)
    try:
        from gui.ui_consistency import refresh_navigation_state
        refresh_navigation_state(app)
    except Exception:
        pass
    result = _runtime_contract(app)
    app._integration_contract = result
    app._integration_active = True
    app._corepulse_design_id = DESIGN_ID
    _write_log(app, result)
    print('[CorePulse] Integración:', 'PASS' if result['passed'] else 'WARN', '| REAL_OR_NA | REAL_FPS_OR_NA_ONLY')
    return result


# Alias temporal para compatibilidad con instalaciones previas; el código nuevo usa el nombre estable.
apply_stage1_integration = apply_runtime_integration

# V483: fusión conservadora desde gui/components/dialogs.py; importar módulo antiguo sigue funcionando.
from tkinter import filedialog, messagebox

from core.version import VERSION_LABEL

VERSION = VERSION_LABEL

def _title(section):
    section = str(section or '').strip()
    return f'CorePulse · {section}' if section else 'CorePulse'

def info(parent, section, message):
    return messagebox.showinfo(_title(section), str(message), parent=parent)

def warning(parent, section, message):
    return messagebox.showwarning(_title(section), str(message), parent=parent)

def error(parent, section, message):
    return messagebox.showerror(_title(section), str(message), parent=parent)

def ask_yes_no(parent, section, message):
    return messagebox.askyesno(_title(section), str(message), parent=parent)

def ask_pdf_path(parent, initialfile):
    try:
        parent.lift()
        parent.focus_force()
        parent.update_idletasks()
    except Exception:
        pass
    return filedialog.asksaveasfilename(defaultextension='.pdf', filetypes=[('Archivos PDF', '*.pdf')], initialfile=initialfile, title=_title('Guardar informe PDF'), parent=parent)

def ask_pdf_directory(parent):
    """Pide solo la carpeta de destino; CorePulse genera el nombre del informe."""
    try:
        parent.lift()
        parent.focus_force()
        parent.update_idletasks()
    except Exception:
        pass
    return filedialog.askdirectory(title=_title('Seleccionar carpeta para el informe'), mustexist=True, parent=parent)
