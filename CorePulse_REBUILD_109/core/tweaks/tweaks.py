"""Puente de Tweaks REBUILD: HKCU propio + motor V485 para otros ajustes.

Los cambios HKLM requieren ejecución con privilegios administrativos.
El Registro sólo se modifica tras confirmación del usuario en QML.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer
# Carga relativa explícita: también funciona en pruebas importlib y ejecución portable.
import importlib.util
_engine_spec = importlib.util.spec_from_file_location("corepulse_rebuild_tweaks_engine", Path(__file__).with_name("tweaks_engine.py"))
legacy_engine = importlib.util.module_from_spec(_engine_spec)
_engine_spec.loader.exec_module(legacy_engine)

try:
    import winreg
except ImportError:  # Windows únicamente: acceso seguro desde la UI.
    winreg = None

# Catálogo de 78 ajustes extraído y auditado del motor V491.
# Solo opciones HKCU/REG_DWORD de riesgo bajo/medio se habilitan aquí.
# Los demás son visibles pero BLOQUEADOS hasta migrar permisos,
# detección de compatibilidad y restauración verificable.
_OPTIONS = [{'id': 'extensions',
  'sourceId': 'show_file_extensions',
  'title': 'Mostrar extensiones de archivo',
  'description': 'Muestra .exe, .txt, .jpg y demás extensiones en el Explorador.',
  'category': 'Explorador',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'HideFileExt', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'hidden',
  'sourceId': 'show_hidden_files',
  'title': 'Mostrar archivos ocultos',
  'description': 'Permite visualizar archivos marcados como ocultos; no muestra archivos protegidos del sistema.',
  'category': 'Explorador',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'Hidden', 1, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'this_pc',
  'sourceId': 'open_this_pc',
  'title': 'Abrir Explorador en Este equipo',
  'description': 'Hace que una nueva ventana del Explorador abra Este equipo en lugar de Inicio.',
  'category': 'Explorador',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'LaunchTo', 1, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'hide_recent_quick_access',
  'sourceId': 'hide_recent_quick_access',
  'title': 'Ocultar archivos recientes en Inicio',
  'description': 'Evita que el Explorador liste archivos usados recientemente en la página Inicio.',
  'category': 'Explorador',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer', 'ShowRecent', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'hide_frequent_quick_access',
  'sourceId': 'hide_frequent_quick_access',
  'title': 'Ocultar carpetas frecuentes en Inicio',
  'description': 'Evita que el Explorador muestre carpetas utilizadas con frecuencia.',
  'category': 'Explorador',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer', 'ShowFrequent', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'show_full_path_title',
  'sourceId': 'show_full_path_title',
  'title': 'Mostrar ruta completa en el título',
  'description': 'Muestra la ruta completa de la carpeta en la barra de título del Explorador.',
  'category': 'Explorador',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\CabinetState', 'FullPath', 1, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'compact',
  'sourceId': 'compact_explorer',
  'title': 'Activar vista compacta del Explorador',
  'description': 'Reduce el espacio vertical entre archivos y carpetas.',
  'category': 'Explorador',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'UseCompactMode', 1, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'classic_context_menu',
  'sourceId': 'classic_context_menu',
  'title': 'Menú contextual clásico',
  'description': 'Restaura el menú contextual clásico en Windows 11. Puede dejar de funcionar en builds futuras.',
  'category': 'Explorador',
  'risk': 'Medio',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Classes\\CLSID\\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\\InprocServer32',
           '',
           '',
           'string']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'end_task_taskbar',
  'sourceId': 'end_task_taskbar',
  'title': 'Finalizar tarea desde la barra de tareas',
  'description': 'Activa “Finalizar tarea” al hacer clic derecho sobre una aplicación en la barra de tareas.',
  'category': 'Explorador',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced\\TaskbarDeveloperSettings',
           'TaskbarEndTask',
           1,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'show_seconds_clock',
  'sourceId': 'show_seconds_clock',
  'title': 'Mostrar segundos en el reloj',
  'description': 'Muestra segundos en el reloj de la bandeja del sistema.',
  'category': 'Explorador',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
           'ShowSecondsInSystemClock',
           1,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'widgets',
  'sourceId': 'disable_widgets',
  'title': 'Ocultar Widgets de la barra de tareas',
  'description': 'Oculta el botón de Widgets sin desinstalar el paquete.',
  'category': 'Barra de tareas',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'TaskbarDa', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_chat',
  'sourceId': 'disable_chat',
  'title': 'Ocultar Chat/Teams de la barra de tareas',
  'description': 'Oculta el acceso de Chat cuando existe en la build instalada.',
  'category': 'Barra de tareas',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'TaskbarMn', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'left_taskbar',
  'sourceId': 'taskbar_left',
  'title': 'Alinear barra de tareas a la izquierda',
  'description': 'Mueve Inicio y los iconos de la barra de tareas hacia la izquierda.',
  'category': 'Barra de tareas',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'TaskbarAl', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'hide_taskbar_search',
  'sourceId': 'hide_taskbar_search',
  'title': 'Ocultar búsqueda de la barra de tareas',
  'description': 'Oculta el cuadro/icono de búsqueda; Windows Search sigue disponible desde Inicio.',
  'category': 'Barra de tareas',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Search', 'SearchboxTaskbarMode', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'task_view',
  'sourceId': 'hide_task_view',
  'title': 'Ocultar Vista de tareas',
  'description': 'Oculta el botón Vista de tareas sin desactivar escritorios virtuales.',
  'category': 'Barra de tareas',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
           'ShowTaskViewButton',
           0,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'hide_copilot_button',
  'sourceId': 'hide_copilot_button',
  'title': 'Ocultar botón de Copilot',
  'description': 'Oculta el botón de Copilot cuando la build de Windows lo expone en la barra de tareas.',
  'category': 'Barra de tareas',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
           'ShowCopilotButton',
           0,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'transparency',
  'sourceId': 'disable_transparency',
  'title': 'Desactivar transparencias',
  'description': 'Reduce efectos de transparencia en Inicio, barra de tareas y superficies compatibles.',
  'category': 'Interfaz',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize',
           'EnableTransparency',
           0,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'reduce_animations',
  'sourceId': 'reduce_animations',
  'title': 'Reducir animaciones de Windows',
  'description': 'Desactiva varias animaciones y sombras visuales para priorizar respuesta de interfaz.',
  'category': 'Interfaz',
  'risk': 'Medio',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Control Panel\\Desktop\\WindowMetrics', 'MinAnimate', '0', 'string'],
          ['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'TaskbarAnimations', 0, 'dword'],
          ['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
           'ListviewAlphaSelect',
           0,
           'dword'],
          ['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'ListviewShadow', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_aero_shake',
  'sourceId': 'disable_aero_shake',
  'title': 'Desactivar Aero Shake',
  'description': 'Evita minimizar las demás ventanas al agitar una ventana con el mouse.',
  'category': 'Interfaz',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'DisallowShaking', 1, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'reduce_menu_delay',
  'sourceId': 'reduce_menu_delay',
  'title': 'Reducir retardo de menús',
  'description': 'Reduce la demora de apertura de menús a 200 ms.',
  'category': 'Interfaz',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Control Panel\\Desktop', 'MenuShowDelay', '200', 'string']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_startup_delay',
  'sourceId': 'disable_startup_delay',
  'title': 'Reducir retraso de apps al iniciar sesión',
  'description': 'Elimina el retardo artificial de inicio de algunas aplicaciones del usuario.',
  'category': 'Interfaz',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Serialize',
           'StartupDelayInMSec',
           0,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'dark_mode',
  'sourceId': 'dark_mode',
  'title': 'Forzar modo oscuro de Windows',
  'description': 'Configura aplicaciones y sistema para usar el tema oscuro.',
  'category': 'Interfaz',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize',
           'AppsUseLightTheme',
           0,
           'dword'],
          ['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize',
           'SystemUsesLightTheme',
           0,
           'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_start_recommendations',
  'sourceId': 'disable_start_recommendations',
  'title': 'Reducir recomendaciones de Inicio',
  'description': 'Desactiva recomendaciones dinámicas de contenido en el menú Inicio cuando la build respeta esta '
                 'clave.',
  'category': 'Interfaz',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
           'Start_IrisRecommendations',
           0,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_lock_screen',
  'sourceId': 'disable_lock_screen',
  'title': 'Desactivar pantalla de bloqueo',
  'description': 'Omite la pantalla de bloqueo y pasa directamente a la pantalla de inicio de sesión.',
  'category': 'Interfaz',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\Personalization', 'NoLockScreen', 1, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_taskbar_window_sharing',
  'sourceId': 'disable_taskbar_window_sharing',
  'title': 'Desactivar compartir ventana desde la barra de tareas',
  'description': 'Desactiva la integración de compartir ventanas desde la barra de tareas. Reduce una integración del '
                 'shell que no todos usan.',
  'category': 'Interfaz',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'TaskbarSn', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_account_notifications_start',
  'sourceId': 'disable_account_notifications_start',
  'title': 'Ocultar avisos de cuenta en Inicio',
  'description': 'Evita avisos de cuenta, copia de seguridad y suscripciones en el menú Inicio. No desactiva '
                 'notificaciones normales de aplicaciones.',
  'category': 'Interfaz',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'SOFTWARE\\Policies\\Microsoft\\Windows\\CurrentVersion\\AccountNotifications',
           'DisableAccountNotifications',
           1,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_web_search',
  'sourceId': 'disable_web_search',
  'title': 'Desactivar resultados web en Inicio',
  'description': 'Evita sugerencias web/Bing en la búsqueda de Inicio sin desactivar Windows Search.',
  'category': 'Privacidad',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Policies\\Microsoft\\Windows\\Explorer', 'DisableSearchBoxSuggestions', 1, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_advertising_id',
  'sourceId': 'disable_advertising_id',
  'title': 'Desactivar ID de publicidad',
  'description': 'Deshabilita el identificador de publicidad personalizado del usuario actual.',
  'category': 'Privacidad',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\AdvertisingInfo', 'Enabled', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_tailored_experiences',
  'sourceId': 'disable_tailored_experiences',
  'title': 'Desactivar experiencias personalizadas',
  'description': 'Evita recomendaciones personalizadas basadas en datos de diagnóstico.',
  'category': 'Privacidad',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Privacy',
           'TailoredExperiencesWithDiagnosticDataEnabled',
           0,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_sync_provider_ads',
  'sourceId': 'disable_sync_provider_ads',
  'title': 'Desactivar anuncios del Explorador',
  'description': 'Oculta notificaciones promocionales del proveedor de sincronización.',
  'category': 'Privacidad',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced',
           'ShowSyncProviderNotifications',
           0,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_content_suggestions',
  'sourceId': 'disable_content_suggestions',
  'title': 'Reducir sugerencias y contenido promocionado',
  'description': 'Desactiva varias suscripciones de sugerencias sin eliminar Microsoft Store.',
  'category': 'Privacidad',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
           'SystemPaneSuggestionsEnabled',
           0,
           'dword'],
          ['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
           'SubscribedContent-338388Enabled',
           0,
           'dword'],
          ['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
           'SubscribedContent-338389Enabled',
           0,
           'dword'],
          ['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
           'SubscribedContent-353694Enabled',
           0,
           'dword'],
          ['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\ContentDeliveryManager',
           'SubscribedContent-353696Enabled',
           0,
           'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_activity_history',
  'sourceId': 'disable_activity_history',
  'title': 'Desactivar historial de actividad',
  'description': 'Impide publicar/subir el historial de actividad mediante políticas de Windows.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\System', 'EnableActivityFeed', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\System', 'PublishUserActivities', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\System', 'UploadUserActivities', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_telemetry',
  'sourceId': 'disable_telemetry',
  'title': 'Reducir telemetría de Windows',
  'description': 'Solicita el nivel mínimo permitido por la edición instalada mediante política del sistema.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\DataCollection', 'AllowTelemetry', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_online_speech',
  'sourceId': 'disable_online_speech',
  'title': 'Desactivar reconocimiento de voz en línea',
  'description': 'Deshabilita el consentimiento de reconocimiento de voz conectado para el usuario.',
  'category': 'Privacidad',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Speech_OneCore\\Settings\\OnlineSpeechPrivacy', 'HasAccepted', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_inking_typing',
  'sourceId': 'disable_inking_typing',
  'title': 'Reducir personalización de escritura y entrada',
  'description': 'Limita la recopilación implícita de texto/tinta usada para personalización.',
  'category': 'Privacidad',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\InputPersonalization', 'RestrictImplicitInkCollection', 1, 'dword'],
          ['HKCU', 'Software\\Microsoft\\InputPersonalization', 'RestrictImplicitTextCollection', 1, 'dword'],
          ['HKCU', 'Software\\Microsoft\\InputPersonalization\\TrainedDataStore', 'HarvestContacts', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_feedback_prompts',
  'sourceId': 'disable_feedback_prompts',
  'title': 'Desactivar solicitudes de comentarios',
  'description': 'Reduce las solicitudes periódicas de feedback de Windows.',
  'category': 'Privacidad',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Siuf\\Rules', 'NumberOfSIUFInPeriod', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_app_launch_tracking',
  'sourceId': 'disable_app_launch_tracking',
  'title': 'Desactivar seguimiento de inicio de aplicaciones',
  'description': 'Evita que Windows rastree lanzamientos para personalizar Inicio y búsqueda.',
  'category': 'Privacidad',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'Start_TrackProgs', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_location',
  'sourceId': 'disable_location',
  'title': 'Desactivar ubicación para el usuario',
  'description': 'Deniega el acceso a ubicación desde el almacén de consentimiento del usuario.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'Software\\Microsoft\\Windows\\CurrentVersion\\CapabilityAccessManager\\ConsentStore\\location',
           'Value',
           'Deny',
           'string']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_error_reporting',
  'sourceId': 'disable_error_reporting',
  'title': 'Desactivar Windows Error Reporting',
  'description': 'Evita el envío automático de reportes de errores del usuario.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\Windows Error Reporting', 'Disabled', 1, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_copilot_policy',
  'sourceId': 'disable_copilot_policy',
  'title': 'Desactivar Windows Copilot por política',
  'description': 'Solicita desactivar Windows Copilot mediante política del usuario cuando la build la respeta.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Policies\\Microsoft\\Windows\\WindowsCopilot', 'TurnOffWindowsCopilot', 1, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_recall',
  'sourceId': 'disable_recall',
  'title': 'Desactivar Recall / AI Data Analysis',
  'description': 'Desactiva la política de análisis de datos de Windows AI/Recall cuando el componente existe.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsAI', 'DisableAIDataAnalysis', 1, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_consumer_features',
  'sourceId': 'disable_consumer_features',
  'title': 'Desactivar Consumer Features',
  'description': 'Reduce instalaciones promocionadas y sugerencias de aplicaciones de Microsoft.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM',
           'SOFTWARE\\Policies\\Microsoft\\Windows\\CloudContent',
           'DisableWindowsConsumerFeatures',
           1,
           'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_delivery_optimization',
  'sourceId': 'disable_delivery_optimization',
  'title': 'Desactivar P2P de Delivery Optimization',
  'description': 'Evita usar ancho de banda para distribuir actualizaciones a otros equipos.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\DeliveryOptimization', 'DODownloadMode', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_clipboard_history',
  'sourceId': 'disable_clipboard_history',
  'title': 'Desactivar historial del portapapeles',
  'description': 'Desactiva Win+V y evita que Windows mantenga un historial de elementos copiados.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\System', 'AllowClipboardHistory', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_cross_device_clipboard',
  'sourceId': 'disable_cross_device_clipboard',
  'title': 'Desactivar sincronización del portapapeles',
  'description': 'Impide sincronizar el portapapeles entre dispositivos asociados a la misma cuenta.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\System', 'AllowCrossDeviceClipboard', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_recent_documents_tracking',
  'sourceId': 'disable_recent_documents_tracking',
  'title': 'Desactivar seguimiento de documentos recientes',
  'description': 'Evita que Windows mantenga listas de documentos recientes para Inicio y Jump Lists. Puede reducir '
                 'comodidad en accesos recientes.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': True,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced', 'Start_TrackDocs', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_search_location',
  'sourceId': 'disable_search_location',
  'title': 'Evitar que Windows Search use ubicación',
  'description': 'Impide que Windows Search use la ubicación para personalizar resultados.',
  'category': 'Privacidad',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search', 'AllowSearchToUseLocation', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_mouse_acceleration',
  'sourceId': 'disable_mouse_acceleration',
  'title': 'Desactivar aceleración del mouse',
  'description': 'Usa movimiento clásico sin Enhance Pointer Precision; útil para consistencia en juegos.',
  'category': 'Gaming',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Control Panel\\Mouse', 'MouseSpeed', '0', 'string'],
          ['HKCU', 'Control Panel\\Mouse', 'MouseThreshold1', '0', 'string'],
          ['HKCU', 'Control Panel\\Mouse', 'MouseThreshold2', '0', 'string']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'enable_game_mode',
  'sourceId': 'enable_game_mode',
  'title': 'Mantener Modo Juego habilitado',
  'description': 'Solicita a Windows mantener Game Mode activo.',
  'category': 'Gaming',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\GameBar', 'AutoGameModeEnabled', 1, 'dword'],
          ['HKCU', 'Software\\Microsoft\\GameBar', 'AllowAutoGameMode', 1, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_game_dvr',
  'sourceId': 'disable_game_dvr',
  'title': 'Desactivar Game DVR y capturas en segundo plano',
  'description': 'Desactiva captura/grabación de Game DVR. Puede afectar funciones de grabación de Xbox Game Bar.',
  'category': 'Gaming',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'System\\GameConfigStore', 'GameDVR_Enabled', 0, 'dword'],
          ['HKCU', 'Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR', 'AppCaptureEnabled', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_gamebar_startup',
  'sourceId': 'disable_gamebar_startup',
  'title': 'Reducir avisos de Xbox Game Bar',
  'description': 'Evita el panel de bienvenida/inicio automático de Game Bar sin desinstalarla.',
  'category': 'Gaming',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\GameBar', 'ShowStartupPanel', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_gamebar_controller_launch',
  'sourceId': 'disable_gamebar_controller_launch',
  'title': 'Evitar que el mando abra Xbox Game Bar',
  'description': 'Desactiva el atajo que permite al botón Xbox/Nexus del controlador abrir Game Bar.',
  'category': 'Gaming',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU', 'Software\\Microsoft\\GameBar', 'UseNexusForGameBarEnabled', 0, 'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'disable_game_dvr_policy',
  'sourceId': 'disable_game_dvr_policy',
  'title': 'Bloquear Game DVR por política',
  'description': 'Desactiva grabación y difusión de juegos mediante la política oficial de Windows. Útil si no '
                 'utilizas capturas de Xbox Game Bar.',
  'category': 'Gaming',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\GameDVR', 'AllowGameDVR', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'enable_hags',
  'sourceId': 'enable_hags',
  'title': 'Activar Hardware-Accelerated GPU Scheduling',
  'description': 'Solicita HAGS. Sólo tiene efecto si GPU, driver y build lo soportan; requiere reinicio.',
  'category': 'Gaming',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SYSTEM\\CurrentControlSet\\Control\\GraphicsDrivers', 'HwSchMode', 2, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_power_throttling',
  'sourceId': 'disable_power_throttling',
  'title': 'Desactivar Power Throttling global',
  'description': 'Reduce la limitación energética de procesos en segundo plano. Puede aumentar consumo y temperatura.',
  'category': 'Gaming',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SYSTEM\\CurrentControlSet\\Control\\Power\\PowerThrottling', 'PowerThrottlingOff', 1, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_edge_startup_boost',
  'sourceId': 'disable_edge_startup_boost',
  'title': 'Desactivar Startup Boost de Microsoft Edge',
  'description': 'Evita que Edge mantenga procesos preparados desde el inicio de sesión. Edge puede tardar ligeramente '
                 'más en su primer arranque.',
  'category': 'Rendimiento',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'StartupBoostEnabled', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_edge_background_mode',
  'sourceId': 'disable_edge_background_mode',
  'title': 'Cerrar procesos de Edge al cerrar el navegador',
  'description': 'Evita que Edge continúe ejecutando extensiones y aplicaciones en segundo plano después de cerrar la '
                 'última ventana.',
  'category': 'Rendimiento',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'BackgroundModeEnabled', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_windows_background_apps',
  'sourceId': 'disable_windows_background_apps',
  'title': 'Bloquear apps de Windows en segundo plano',
  'description': 'Fuerza a las apps de Windows compatibles a no ejecutar actividad en segundo plano. Puede reducir '
                 'actividad ociosa, pero también notificaciones y sincronización.',
  'category': 'Rendimiento',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\AppPrivacy', 'LetAppsRunInBackground', 2, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_search_highlights',
  'sourceId': 'disable_search_highlights',
  'title': 'Desactivar Search Highlights',
  'description': 'Desactiva contenido dinámico y destacados en Windows Search para reducir contenido conectado dentro '
                 'de la búsqueda.',
  'category': 'Rendimiento',
  'risk': 'Bajo',
  'requiresExplorer': True,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\Windows Search', 'EnableDynamicContentInWSB', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_hibernation',
  'sourceId': 'disable_hibernation',
  'title': 'Desactivar hibernación',
  'description': 'Desactiva hibernación y libera hiberfil.sys. También puede deshabilitar Inicio rápido.',
  'category': 'Energía',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power', 'HibernateEnabled', 0, 'dword'],
          ['HKLM',
           'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FlyoutMenuSettings',
           'ShowHibernateOption',
           0,
           'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_fast_startup',
  'sourceId': 'disable_fast_startup',
  'title': 'Desactivar Inicio rápido',
  'description': 'Desactiva Fast Startup. Puede facilitar diagnósticos de drivers y dual boot.',
  'category': 'Energía',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Power', 'HiberbootEnabled', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_storage_sense',
  'sourceId': 'disable_storage_sense',
  'title': 'Desactivar Storage Sense',
  'description': 'Evita que Windows elimine automáticamente temporales según sus reglas de Storage Sense.',
  'category': 'Sistema',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': False,
  'ops': [['HKCU',
           'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\StorageSense\\Parameters\\StoragePolicy',
           '01',
           0,
           'dword']],
  'enabledByPolicy': True,
  'reason': ''},
 {'id': 'enable_long_paths',
  'sourceId': 'enable_long_paths',
  'title': 'Habilitar rutas Win32 largas',
  'description': 'Permite que aplicaciones compatibles utilicen rutas de más de 260 caracteres.',
  'category': 'Sistema',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SYSTEM\\CurrentControlSet\\Control\\FileSystem', 'LongPathsEnabled', 1, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'verbose_status',
  'sourceId': 'verbose_status',
  'title': 'Mostrar mensajes detallados de inicio/apagado',
  'description': 'Muestra estados detallados durante inicio, cierre de sesión y apagado.',
  'category': 'Sistema',
  'risk': 'Bajo',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System', 'VerboseStatus', 1, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_remote_assistance',
  'sourceId': 'disable_remote_assistance',
  'title': 'Desactivar Asistencia remota',
  'description': 'Impide invitaciones de Windows Remote Assistance. No desactiva Escritorio remoto (RDP).',
  'category': 'Sistema',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SYSTEM\\CurrentControlSet\\Control\\Remote Assistance', 'fAllowToGetHelp', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'exclude_driver_updates',
  'sourceId': 'exclude_driver_updates',
  'title': 'Excluir drivers de Windows Update',
  'description': 'Evita que las actualizaciones de calidad incluyan controladores. Deberás gestionarlos por separado.',
  'category': 'Actualizaciones',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM',
           'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate',
           'ExcludeWUDriversInQualityUpdate',
           1,
           'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'no_auto_reboot_updates',
  'sourceId': 'no_auto_reboot_updates',
  'title': 'Evitar reinicio automático con sesión iniciada',
  'description': 'Solicita a Windows Update no reiniciar automáticamente mientras haya un usuario conectado.',
  'category': 'Actualizaciones',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM',
           'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU',
           'NoAutoRebootWithLoggedOnUsers',
           1,
           'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_auto_updates',
  'sourceId': 'disable_auto_updates',
  'title': 'Desactivar actualizaciones automáticas',
  'description': 'Desactiva la búsqueda/instalación automática mediante política. Aumenta el riesgo de quedar sin '
                 'parches.',
  'category': 'Actualizaciones',
  'risk': 'Alto',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU', 'NoAutoUpdate', 1, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_llmnr',
  'sourceId': 'disable_llmnr',
  'title': 'Desactivar LLMNR',
  'description': 'Deshabilita resolución de nombres multicast LLMNR. Puede mejorar privacidad/seguridad en redes '
                 'administradas.',
  'category': 'Red',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows NT\\DNSClient', 'EnableMulticast', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'edge_debloat',
  'sourceId': 'edge_debloat',
  'title': 'Microsoft Edge: reducir promociones y telemetría',
  'description': 'Aplica políticas para reducir recomendaciones, shopping, rewards, feedback y contenido promocional '
                 'de Edge.',
  'category': 'Apps y debloat',
  'risk': 'Medio',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\EdgeUpdate', 'CreateDesktopShortcutDefault', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'PersonalizationReportingEnabled', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'ShowRecommendationsEnabled', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'HideFirstRunExperience', 1, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'UserFeedbackAllowed', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'ConfigureDoNotTrack', 1, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'AlternateErrorPagesEnabled', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'EdgeCollectionsEnabled', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'EdgeShoppingAssistantEnabled', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'ShowMicrosoftRewards', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'WebWidgetAllowed', 0, 'dword'],
          ['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Edge', 'DiagnosticData', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'remove_edge',
  'sourceId': 'remove_edge',
  'title': 'Desinstalar Microsoft Edge',
  'description': 'Intenta desinstalar Edge a nivel de sistema conservando WebView2 Runtime y el perfil del usuario.',
  'category': 'Apps y debloat',
  'risk': 'Alto',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'remove_onedrive',
  'sourceId': 'remove_onedrive',
  'title': 'Desinstalar Microsoft OneDrive',
  'description': 'Ejecuta el desinstalador oficial de OneDrive sin borrar manualmente la carpeta de archivos '
                 'sincronizados.',
  'category': 'Apps y debloat',
  'risk': 'Alto',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'remove_widgets_package',
  'sourceId': 'remove_widgets_package',
  'title': 'Desinstalar Windows Web Experience / Widgets',
  'description': 'Elimina el paquete que alimenta Widgets. Puede afectar funciones que dependan de Windows Web '
                 'Experience Pack.',
  'category': 'Apps y debloat',
  'risk': 'Alto',
  'requiresExplorer': True,
  'requiresAdmin': True,
  'ops': [],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_defender_stack',
  'sourceId': 'disable_defender_stack',
  'title': 'Desactivar protecciones de Microsoft Defender',
  'description': 'Intenta desactivar protección en tiempo real, comportamiento, IOAV, scripts, nube y envío de '
                 'muestras. Tamper Protection puede bloquearlo.',
  'category': 'Seguridad avanzada',
  'risk': 'Crítico',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_smartscreen',
  'sourceId': 'disable_smartscreen',
  'title': 'Desactivar Microsoft Defender SmartScreen',
  'description': 'Desactiva SmartScreen por política. Reduce protección contra descargas/sitios potencialmente '
                 'maliciosos.',
  'category': 'Seguridad avanzada',
  'risk': 'Crítico',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Policies\\Microsoft\\Windows\\System', 'EnableSmartScreen', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_uac',
  'sourceId': 'disable_uac',
  'title': 'Desactivar UAC',
  'description': 'Desactiva User Account Control. Reduce significativamente el aislamiento de privilegios y requiere '
                 'reinicio.',
  'category': 'Seguridad avanzada',
  'risk': 'Crítico',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System', 'EnableLUA', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_memory_integrity',
  'sourceId': 'disable_memory_integrity',
  'title': 'Desactivar Integridad de memoria (HVCI)',
  'description': 'Desactiva Hypervisor-Enforced Code Integrity. Puede mejorar compatibilidad/rendimiento a costa de '
                 'seguridad.',
  'category': 'Seguridad avanzada',
  'risk': 'Alto',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM',
           'SYSTEM\\CurrentControlSet\\Control\\DeviceGuard\\Scenarios\\HypervisorEnforcedCodeIntegrity',
           'Enabled',
           0,
           'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'},
 {'id': 'disable_vbs',
  'sourceId': 'disable_vbs',
  'title': 'Desactivar Virtualization-Based Security (VBS)',
  'description': 'Solicita desactivar VBS. Puede afectar Credential Guard y otras protecciones; requiere reinicio.',
  'category': 'Seguridad avanzada',
  'risk': 'Alto',
  'requiresExplorer': False,
  'requiresAdmin': True,
  'ops': [['HKLM', 'SYSTEM\\CurrentControlSet\\Control\\DeviceGuard', 'EnableVirtualizationBasedSecurity', 0, 'dword']],
  'enabledByPolicy': False,
  'reason': 'Pendiente de migrar con validación y restauración segura; no se aplicará desde REBUILD.'}]
for _spec in _OPTIONS:
    if _spec["enabledByPolicy"]:
        _op = _spec["ops"][0]
        _spec.update(path=_op[1], name=_op[2], value=_op[3])
_BY_ID = {item["id"]: item for item in _OPTIONS}


def _is_windows_11():
    if os.name != "nt" or winreg is None:
        return False
    try:
        return sys.getwindowsversion().build >= 22000
    except (AttributeError, OSError):
        return False


def _backup_path():
    # AppData/Roaming: persistencia por usuario y extracción portable del ZIP.
    base = Path(os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming"))
    return base / "CorePulse" / "rebuild" / "tweaks_originales.json"


def _read_value(spec):
    """Devuelve (existe, valor, tipo); jamás interpreta faltantes como desactivado."""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, spec["path"], 0, winreg.KEY_READ) as key:
        try:
            value, value_type = winreg.QueryValueEx(key, spec["name"])
        except FileNotFoundError:
            return False, None, None
        return True, value, value_type


def _safe_read(spec):
    try:
        return _read_value(spec)
    except FileNotFoundError:
        return False, None, None


def _write_value(spec, value):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, spec["path"], 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, spec["name"], 0, winreg.REG_DWORD, int(value))


def _restore_value(spec, original):
    if original["present"]:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, spec["path"], 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, spec["name"], 0, winreg.REG_DWORD, original["value"])
    else:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, spec["path"], 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, spec["name"])
        except FileNotFoundError:
            pass


def _matches_original(spec, original):
    """Confirma mediante lectura independiente que Windows volvió al estado previo."""
    present, value, kind = _safe_read(spec)
    if original["present"]:
        return present and kind == winreg.REG_DWORD and value == original["value"]
    return not present


def _matches_target(spec):
    """Evita anunciar éxito cuando el Registro no aceptó o revirtió el cambio."""
    present, value, kind = _safe_read(spec)
    return present and kind == winreg.REG_DWORD and value == spec["value"]


def _valid_backup_entry(value):
    if not isinstance(value, dict) or type(value.get("present")) is not bool:
        return False
    if value["present"]:
        return type(value.get("value")) is int and 0 <= value["value"] <= 0xFFFFFFFF
    return value.get("value") is None


def _load_backup(path):
    if not path.is_file():
        return {"schema": 1, "originales": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != 1 or not isinstance(data.get("originales"), dict):
        raise ValueError("El respaldo de tweaks tiene un formato desconocido.")
    if not all(k in _BY_ID and _valid_backup_entry(v) for k, v in data["originales"].items()):
        raise ValueError("El respaldo de tweaks contiene valores inválidos.")
    return data


def _save_backup(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Escritura atómica: evita perder un respaldo ante un cierre inesperado.
    temp = path.with_suffix(".tmp")
    try:
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


class TweaksManager(QObject):
    stateChanged = Signal()
    busyChanged = Signal()

    def __init__(self, parent=None, *, backup=None):
        super().__init__(parent)
        self._backup = Path(backup) if backup is not None else _backup_path()
        # Nunca leer Registro/PowerShell desde un getter usado por QML.
        # El catálogo se puede mostrar inmediatamente, pero ninguna acción
        # se habilita hasta verificar las fuentes reales.
        self._cached_options = [self._placeholder(spec) for spec in _OPTIONS]
        self._busy = False
        self._closed = False
        self._queued_refresh = False
        self._last_scan = None
        self._future = None
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="corepulse-tweaks-check")
        self._poll = QTimer(self)
        self._poll.setInterval(100)
        self._poll.timeout.connect(self._finish_if_ready)

    @staticmethod
    def _placeholder(spec):
        return {
            "id": spec["id"], "title": spec["title"],
            "category": spec["category"], "description": spec["description"],
            "requiresExplorer": spec["requiresExplorer"],
            "available": False, "active": False, "canRestore": False,
            "status": "Comprobando…", "detail": "Verificando el estado real de Windows.",
            "backupError": False, "enabledByPolicy": spec["enabledByPolicy"],
            "risk": spec["risk"], "requiresAdmin": spec["requiresAdmin"],
            "sourceId": spec["sourceId"],
        }

    @Property("QVariantList", notify=stateChanged)
    def options(self):
        # Solo devuelve memoria; nunca inicia 78 consultas desde bindings QML.
        return self._cached_options

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property(bool, constant=True)
    def isWindows11(self):
        return _is_windows_11()

    def _collect_options(self):
        """Función de trabajo sin acceso a objetos Qt ni propiedades de QML."""
        supported = _is_windows_11()
        try:
            backups = _load_backup(self._backup)["originales"]
            backup_error = ""
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            backups = {}
            backup_error = f"Respaldo no disponible: {exc}"
        # Un solo acceso al registro persistido para todo el catálogo V485.
        # Ahorra decenas de lecturas a disco al abrir la pestaña.
        try:
            rollback_ids = legacy_engine.saved_rollback_ids() if supported else set()
        except (OSError, ValueError, json.JSONDecodeError):
            rollback_ids = set()
        output = []
        for spec in _OPTIONS:
            row = self._placeholder(spec)
            row.update(available=supported, canRestore=spec["id"] in backups,
                       status="Sin aplicar", detail="")
            if not spec["enabledByPolicy"]:
                try:
                    source_id = spec["sourceId"]
                    probe = legacy_engine.preflight_tweak(source_id)
                    detected = legacy_engine.detect_tweak(source_id, _rollback_ids=rollback_ids)
                    row.update(
                        available=bool(probe.get("applicable")) and detected.get("status") != "unknown",
                        active=bool(detected.get("verified")) and bool(detected.get("applied")),
                        canRestore=bool(detected.get("rollback_available")),
                        status=("Ajuste activo" if detected.get("verified") and detected.get("applied")
                                else "Sin aplicar" if probe.get("applicable") and detected.get("status") != "unknown"
                                else "No disponible"),
                        detail=detected.get("detail") or probe.get("reason") or "",
                    )
                except Exception as exc:
                    row.update(available=False, status="No verificable", detail=str(exc))
            elif not supported:
                row.update(status="No disponible", detail="Solo compatible con Windows 11.")
            else:
                try:
                    exists, value, kind = _safe_read(spec)
                    if exists and (kind != winreg.REG_DWORD or type(value) is not int):
                        row.update(available=False, status="No disponible", detail="Tipo de valor no compatible; no se modificará.")
                    elif exists and value == spec["value"]:
                        row.update(active=True, status="Ajuste activo", detail="El valor actual coincide con el ajuste.")
                    else:
                        row.update(status="Sin aplicar", detail="El valor actual es diferente o no existe.")
                except OSError as exc:
                    row.update(available=False, status="No disponible", detail=f"No se pudo consultar Windows: {exc}")
            if backup_error:
                row.update(available=False, canRestore=False, detail=backup_error)
            output.append(row)
        return output

    @Slot()
    def ensureFresh(self):
        # Reabrir la pestaña durante el siguiente minuto no repite los
        # sondeos de PowerShell. "Actualizar" sigue siendo manual e inmediato.
        if self._last_scan is None or time.monotonic() - self._last_scan > 60:
            if self._future is None:
                self.refresh()

    @Slot()
    def refresh(self):
        if self._closed:
            return
        if self._future is not None:
            self._queued_refresh = True
            return
        self._busy = True
        self.busyChanged.emit()
        self._future = self._executor.submit(self._collect_options)
        self._poll.start()

    @Slot()
    def _finish_if_ready(self):
        if self._closed or self._future is None or not self._future.done():
            return
        self._poll.stop()
        succeeded = True
        try:
            result = self._future.result()
        except Exception:
            succeeded = False
            # No anunciamos controles seguros si falló el sondeo global.
            result = [self._placeholder(spec) for spec in _OPTIONS]
            for row in result:
                row.update(status="No verificable", detail="No se pudo completar la consulta de Windows.")
        self._future = None
        self._cached_options = result
        self._last_scan = time.monotonic() if succeeded else None
        self._busy = False
        self.stateChanged.emit()
        self.busyChanged.emit()
        if self._queued_refresh:
            self._queued_refresh = False
            self.refresh()

    @Slot()
    def close(self):
        self._closed = True
        self._poll.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)

    @Slot(str, result=str)
    def applyTweak(self, tweak_id):
        if self._busy:
            return "Espera a que termine la comprobación de los ajustes."
        spec = _BY_ID.get(tweak_id)
        if spec is None or not _is_windows_11():
            return "No disponible: ajuste desconocido o Windows 11 no detectado."
        if not spec["enabledByPolicy"]:
            info = legacy_engine.preflight_tweak(spec["sourceId"])
            if not info.get("applicable"):
                return "No se aplicó: " + str(info.get("reason") or "Este ajuste no es seguro o compatible en este equipo.")
            result = legacy_engine.apply_tweak(spec["sourceId"])
            self.refresh()
            return str(result.get("message", "No se pudo completar la operación."))
        try:
            exists, value, kind = _safe_read(spec)
            if exists and (kind != winreg.REG_DWORD or type(value) is not int):
                return "No se cambió: el valor actual tiene un tipo no compatible."
            if exists and value == spec["value"]:
                return "El ajuste ya está activo. No se modificó Windows."
            data = _load_backup(self._backup)
            if tweak_id not in data["originales"]:
                data["originales"][tweak_id] = {"present": exists, "value": value if exists else None}
                _save_backup(self._backup, data)  # fallar cerrado antes de escribir Windows
            _write_value(spec, spec["value"])
            if not _matches_target(spec):
                # El respaldo se conserva para poder reintentar o restaurar.
                self.refresh()
                return "No confirmado: Windows no conserva el valor solicitado. Respaldo original conservado."
            self.refresh()
            return "Ajuste aplicado y valor verificado. Es posible que debas cerrar y volver a abrir el Explorador o iniciar sesión para verlo."
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.refresh()
            return f"No se pudo aplicar el ajuste: {exc}"

    @Slot(str, result=str)
    def restoreTweak(self, tweak_id):
        if self._busy:
            return "Espera a que termine la comprobación de los ajustes."
        spec = _BY_ID.get(tweak_id)
        if spec is None or not _is_windows_11():
            return "No disponible: ajuste desconocido o Windows 11 no detectado."
        if not spec["enabledByPolicy"]:
            result = legacy_engine.undo_tweak(spec["sourceId"])
            self.refresh()
            return str(result.get("message", "No se pudo completar la restauración."))
        try:
            data = _load_backup(self._backup)
            original = data["originales"].get(tweak_id)
            if original is None:
                return "No hay un valor original guardado para este ajuste."
            _restore_value(spec, original)
            if not _matches_original(spec, original):
                self.refresh()
                return "Restauración no confirmada: Windows no volvió al valor original. Respaldo conservado."
            del data["originales"][tweak_id]
            try:
                _save_backup(self._backup, data)
            except OSError:
                # El Registro ya fue restaurado; mantener en disco el respaldo es
                # más seguro que perderlo si falla la persistencia de limpieza.
                self.refresh()
                return "Windows restaurado y verificado, pero no se pudo actualizar el archivo de respaldo."
            self.refresh()
            return "Valor anterior restaurado y verificado. Vuelve a abrir el Explorador o inicia sesión si aún no ves el cambio."
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.refresh()
            return f"No se pudo restaurar: {exc}"
