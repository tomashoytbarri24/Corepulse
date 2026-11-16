# Manual técnico de CorePulse

Guía de instalación, configuración, compilación y despliegue de CorePulse para desarrolladores y para quien deba mantener o revisar el sistema.

**Versión documentada:** REBUILD 210 (aplicación de escritorio) y sitio web corepulse.cl.

## Contenido

1. Componentes del sistema
2. Requisitos
3. Estructura del código
4. Instalación y ejecución de la aplicación de escritorio
5. Datos locales y configuración
6. Pruebas automatizadas
7. Compilación del instalador de Windows
8. Sitio web y base de datos
9. Servicio de IA (CorePulse AI Cloud)
10. Procedimiento para crear una versión nueva
11. Solución de problemas

---

## 1. Componentes del sistema

| Componente | Tecnología | Dónde está | Dónde se ejecuta |
|---|---|---|---|
| Aplicación de escritorio | Python 3.12, PySide6/QML | `Evidencias de sistema/Aplicación/CorePulse_REBUILD_210/` | PC del usuario (Windows 10/11 de 64 bits) |
| Base de datos local | SQLite, JSON, DPAPI | La crea la aplicación en `%LOCALAPPDATA%\CorePulse\` | PC del usuario |
| Sitio web | Next.js 16, React 19, TypeScript | `Evidencias de sistema/Aplicación/CorePulse-web/` | Cloudflare Workers (corepulse.cl) |
| Base de datos web | PostgreSQL (Supabase) | Scripts en `Evidencias de sistema/Base de datos/supabase/` | Supabase |
| Servicio de IA | Cloudflare Worker | `CorePulse_REBUILD_210/cloud/corepulse-ai/` | Cloudflare (ai.corepulse.cl) |
| Instalador | PyInstaller e Inno Setup 7 | `CorePulse_REBUILD_210/installer/` | Equipo de compilación |

La arquitectura y los diagramas están en `Diagramas_UML.md`, y el modelo de datos en `Evidencias de sistema/Base de datos/modelo_datos.md`.

## 2. Requisitos

### Para ejecutar la aplicación desde el código

- Windows 10 u 11 de 64 bits.
- Python 3.12 de 64 bits (también acepta 3.13 y 3.14). Python 3.15 no está validado y el lanzador no lo selecciona.
- Conexión a Internet la primera vez, para instalar las dependencias.
- Opcional: permisos de administrador para algunas lecturas (temperaturas de CPU con PawnIO) y para la medición de FPS por eventos de Windows (o pertenecer al grupo *Performance Log Users*).

### Para compilar el instalador

- Lo anterior, más PyInstaller (en un entorno virtual aparte, con `installer/requirements-build.txt`) e Inno Setup 7.

### Para el sitio web

- Node.js 22 o superior, o Docker.
- Un proyecto de Supabase y una cuenta de Cloudflare para publicarlo.

## 3. Estructura del código

| Carpeta o archivo | Contenido |
|---|---|
| `main.py` | Punto de entrada: prepara el entorno de Python, crea los controladores y los expone a QML |
| `ui/` | Pantallas y componentes QML (33 archivos) |
| `core/monitoring/` | Telemetría de CPU, GPU, RAM y discos |
| `core/health/` | Salud, diagnóstico, reparación, informes PDF, FPS, sesiones de juego, tendencias |
| `core/maintenance/` | Limpieza, red, inicio de Windows, prueba de velocidad |
| `core/tweaks/` | Motor de optimizaciones reversibles |
| `core/overlay.py` | Overlay de juego y atajos globales |
| `core/benchmark.py`, `core/benchmark_gpu.py` | Benchmark del sistema y escena DirectX 11 |
| `core/ai.py` | Cliente de CorePulse AI Cloud |
| `core/cuenta.py` | Conexión con la cuenta web y almacenamiento cifrado del token |
| `core/runtime.py` | Entorno de ejecución, permisos y procesos auxiliares |
| `native/` | Componentes nativos opcionales para el módulo dentro del juego |
| `cloud/corepulse-ai/` | Código del servicio de IA en Cloudflare |
| `installer/` | Archivos para compilar el instalador |
| `tests/` | Pruebas automatizadas (pytest) |
| `versiones/HISTORIAL.md` | Registro de cada versión |
| `requirements.txt` | Dependencias de Python |

## 4. Instalación y ejecución de la aplicación de escritorio

### Opción A: con el instalador (usuarios)

1. Ejecutar `CorePulse_Setup_210_x64.exe`.
2. Seguir el asistente. No requiere tener Python instalado.
3. Abrir CorePulse desde el menú Inicio.

El instalador no está firmado digitalmente. En equipos con el Control inteligente de aplicaciones de Windows activo, Windows puede bloquearlo.

### Opción B: desde el código fuente (desarrolladores)

```bash
cd "FASE 2/Evidencias Proyecto/Evidencias de sistema/Aplicación/CorePulse_REBUILD_210"
Iniciar_CorePulse.bat
```

`Iniciar_CorePulse.bat` busca un Python de 64 bits compatible y ejecuta `main.py`. La primera vez, `main.py` crea un entorno aislado en `%LOCALAPPDATA%\CorePulse\runtime\` e instala las dependencias de `requirements.txt`:

| Dependencia | Uso |
|---|---|
| PySide6 (6.6 o superior) | Interfaz Qt/QML |
| psutil (5.9 o superior) | Uso de CPU, RAM, disco y red |
| pythonnet (3.1 o superior) | Puente con .NET para leer sensores |
| HardwareMonitor (1.2.1 o superior) | LibreHardwareMonitor: temperaturas y sensores |

También se puede ejecutar desde Visual Studio Code abriendo la carpeta y ejecutando `main.py` con Python 3.12.

## 5. Datos locales y configuración

La aplicación no necesita variables de entorno ni archivos de configuración: la IA y la cuenta web ya vienen configuradas. Los datos se guardan por usuario:

| Ubicación | Contenido |
|---|---|
| `%LOCALAPPDATA%\CorePulse\rebuild\monitoring_history.sqlite3` | Historial de monitoreo (90 días) y alertas |
| `%LOCALAPPDATA%\CorePulse\rebuild\game_sessions.sqlite3` | Sesiones de juego |
| `%APPDATA%\CorePulse\rebuild\tweaks_originales.json` | Valores originales de las optimizaciones aplicadas |
| `%LOCALAPPDATA%\CorePulse\cuenta.dat` | Token de la cuenta, cifrado con DPAPI |
| `%LOCALAPPDATA%\CorePulse\reportes\` | Informes PDF |
| `HKCU\Software\CorePulse\CorePulseRebuild` | Preferencias de la interfaz y del overlay |

Para volver la aplicación a su estado inicial basta con borrar esas carpetas y la clave del Registro. Antes, conviene restaurar las optimizaciones aplicadas desde la pantalla Tweaks.

## 6. Pruebas automatizadas

```bash
cd "FASE 2/Evidencias Proyecto/Evidencias de sistema/Aplicación/CorePulse_REBUILD_210"
python -B -m pytest -p no:cacheprovider -q tests
```

El plan de pruebas, los tipos de prueba y los resultados están en `Plan_de_Pruebas.md`. Las pruebas del overlay escriben en la configuración real del usuario (`HKCU\Software\CorePulse\CorePulseRebuild\overlay`); después de ejecutarlas conviene revisar la posición del overlay.

## 7. Compilación del instalador de Windows

1. Crear un entorno virtual de compilación en una ruta corta (por ejemplo `D:\cpbuild`) con Python 3.12:

   ```bash
   python -m venv D:\cpbuild
   D:\cpbuild\Scripts\pip install -r requirements.txt -r installer/requirements-build.txt
   ```

2. Generar la aplicación con PyInstaller usando `installer/CorePulse.spec`.
3. Compilar el instalador con Inno Setup 7 usando `installer/CorePulse.iss` (`ISCC.exe installer\CorePulse.iss`).
4. Probar primero una compilación de prueba con `/DTestBuild`, que usa otro identificador y no reemplaza una instalación real.

El script `installer/build_installer.ps1` automatiza estos pasos. En Windows PowerShell 5.1 puede detenerse porque PyInstaller escribe avisos en la salida de errores; en ese caso, ejecutar los pasos manualmente. El instalador queda en `release/CorePulse_Setup_210_x64.exe`, y el script calcula su huella SHA-256 para verificar que el archivo compartido no fue alterado. Falta firmarlo digitalmente.

## 8. Sitio web y base de datos

Las instrucciones completas están en `Evidencias de sistema/README.md` y `Evidencias de sistema/Base de datos/README.md`. En resumen:

**Con Docker** (desde `Evidencias de sistema`):

```bash
cp .env.example .env
docker compose up -d --build
```

Levanta PostgreSQL con las 13 tablas y sus datos iniciales (puerto 5432) y el sitio en http://localhost:3000.

**Sin Docker** (desde `Aplicación/CorePulse-web`):

```bash
npm ci
cp .env.example .env.local
npm run dev
```

**Variables de entorno del sitio:**

| Variable | Uso |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Dirección del proyecto de Supabase |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Clave pública de Supabase (la seguridad la dan las políticas RLS) |
| `NEXT_PUBLIC_SITE_URL` | Dirección pública del sitio |
| `SUPABASE_SECRET_KEY` | Solo en el equipo del administrador, para subir capturas. Nunca en Cloudflare ni en el repositorio |

**Publicación en producción:** el sitio se publica en Cloudflare Workers con `npm run deploy` (compila con OpenNext). La base de datos se crea ejecutando en orden las migraciones de `Base de datos/supabase/migraciones/` en el proyecto de Supabase.

## 9. Servicio de IA (CorePulse AI Cloud)

El servicio está publicado en `https://ai.corepulse.cl` y la aplicación lo usa sin configuración. Para probarlo o publicarlo (Node.js 22 o superior):

```bash
cd "Evidencias de sistema/Aplicación/CorePulse_REBUILD_210/cloud/corepulse-ai"
npm install
npm run verify        # sintaxis y pruebas simuladas, sin gastar consultas al modelo
npx wrangler deploy   # publicar (solo el dueño de la cuenta de Cloudflare)
```

La clave del proveedor del modelo (Groq) vive solo como secreto en Cloudflare. Nunca se sube al repositorio.

## 10. Procedimiento para crear una versión nueva

1. Leer `Reglas para crear Versiones nuevas.txt` y `versiones/HISTORIAL.md`.
2. Partir de una copia de la versión vigente.
3. Hacer los cambios y quitar el código que quede obsoleto.
4. Ejecutar las pruebas: ninguna versión debe agregar fallos nuevos.
5. Agregar la entrada al inicio del historial con base, cambios, validación y forma de reversión.
6. Guardar un respaldo de la versión anterior y subir la versión al repositorio.
7. Cumplir la `Definition_of_Done.md`.

## 11. Solución de problemas

| Problema | Causa probable | Solución |
|---|---|---|
| "Se requiere Python 3.12, 3.13 o 3.14 de 64 bits" | No hay un Python compatible | Instalar Python 3.12 x64 y volver a ejecutar el `.bat` |
| Temperaturas de CPU en N/A | El sensor necesita PawnIO o permisos de administrador | Aceptar la instalación de PawnIO o abrir como administrador |
| FPS en N/A en el overlay | La medición por eventos de Windows requiere permisos | Usar el botón para habilitar la medición o abrir como administrador |
| Windows bloquea el instalador | El instalador no está firmado y el Control inteligente de aplicaciones está activo | Ejecutar desde el código fuente o esperar la versión firmada |
| La aplicación se cierra al leer datos en Windows en español | Versión anterior a la corrección de codificación | Usar REBUILD 210, que lee la consola con la página de códigos del sistema |
| El overlay aparece en otra posición después de correr las pruebas | Las pruebas del overlay usan la configuración real | Ajustar la posición desde la página Overlay |
| El sitio no inicia sesión en local | Variables de Supabase vacías | Completar `.env` o `.env.local` con la URL y la clave pública |
