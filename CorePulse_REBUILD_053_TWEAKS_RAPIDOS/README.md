# CorePulse REBUILD 053 — Temas iniciales + iconos de Centro de Salud

Base utilizada: **CorePulse REBUILD 051 — Game Card debajo**.

## Qué incluye esta versión

### 1) Centro de Salud
- Se mantienen los módulos migrados del hub de Centro de Salud.
- **Cada icono del hub ahora tiene un color propio** para distinguir mejor cada área:
  - Batería: turquesa
  - Windows: celeste
  - Reparación: verde
  - Historial y cambios: ámbar
  - Recuperación: aqua
  - Rendimiento: violeta
  - Test de Audio: rosado
- El icono principal del encabezado de cada módulo también adopta su color distintivo.

### 2) Módulo de Temas (inicio)
- Se habilita por primera vez el módulo **Temas** desde la barra lateral.
- Incluye una primera colección funcional de temas:
  - CorePulse
  - Aurora
  - Violet Neon
  - Ember Tech
- En esta etapa inicial, los temas cambian en caliente la **paleta base del shell principal**:
  - fondo general
  - degradado principal
  - barra lateral
  - resaltado de navegación
  - acentos visuales base
- La integración profunda en todos los módulos se seguirá ampliando en versiones siguientes.

## Archivos nuevos o modificados
- `ui/Main.qml`
- `ui/HealthPage.qml`
- `ui/ThemesPage.qml` (nuevo)
- `tests/test_rebuild.py`
- `versiones/HISTORIAL.md`

## Validación
- `pytest -q` → **161 PASS**

## Notas
- Se eliminaron carpetas de caché (`__pycache__`, `.pytest_cache`) del proyecto entregado.
- No se alteraron las reglas base de REAL_OR_NA ni los módulos ya migrados.


## REBUILD 053 — Tweaks sin espera de apertura

- **Base única:** REBUILD 052 — Temas e iconos de Centro de Salud.
- **Problema corregido:** al acceder a Tweaks, el getter `options` ejecutaba 78 inspecciones de Registro/PowerShell en el hilo gráfico y QML construía los 78 controles de forma simultánea.
- **Motor asíncrono:** `TweaksManager` devuelve 78 entradas provisionales, seguras y no aplicables, inmediatamente; consulta Windows en un único trabajador y publica los resultados al terminar. Su getter es de memoria, sin E/S ni sondeos.
- **Reversibilidad y seguridad:** durante las comprobaciones se bloquea aplicar y restaurar; tras terminarlas se conserva exactamente el estado y respaldo verificado por el motor anterior. No se modificó el catálogo ni la política de disponibilidad.
- **Consultas consolidadas:** el conjunto de respaldos del motor heredado se consulta una sola vez por sondeo, no de forma independiente por cada tweak.
- **Interfaz virtualizada:** `ListView` muestra solo tarjetas de las filas visibles, preservando las 12 categorías, sus colores y las 78 entradas, con scroll oscuro reutilizable.
- **Reaperturas eficientes:** conserva los resultados durante 60 segundos, salvo que pulses **Actualizar**, que solicita una nueva verificación.
- **Sin alteraciones** en Centro de Salud, Temas, sensores, alertas, Game Card, Limpieza ni Reparación.
- **Validación automatizada:** 165 pruebas aprobadas; comprobaciones de getters no bloqueantes, respuestas asíncronas, cache de reapertura y controles de seguridad.
- **Pendiente:** validación QML en un Windows 11 real y cronometraje del tiempo de apertura en tu PC.
