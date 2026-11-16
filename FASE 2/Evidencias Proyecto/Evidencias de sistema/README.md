# Evidencias de sistema · CorePulse

Esta carpeta contiene el código fuente del proyecto y su base de datos, junto con lo necesario para ejecutarlo en local.

## Estructura

| Carpeta o archivo | Contenido |
|---|---|
| `Aplicación/CorePulse_REBUILD_210/` | Aplicación de escritorio para Windows (Python 3.12 + PySide6/QML). Incluye el servidor de IA (`cloud/corepulse-ai/`), las pruebas (`tests/`) y el historial de versiones (`versiones/HISTORIAL.md`) |
| `Aplicación/CorePulse-web/` | Sitio web corepulse.cl (Next.js 16 + Supabase): frontend y backend (rutas de API y funciones del servidor) |
| `Base de datos/` | Scripts SQL, modelo de datos y diagramas entidad-relación (ver `Base de datos/README.md`) |
| `docker-compose.yml` | Levanta la base de datos web (PostgreSQL) y el sitio web con Docker |
| `.env.example` | Variables de entorno de docker-compose |
| `Aplicación/CorePulse-web/Dockerfile` | Imagen de Docker del sitio web |

## Componentes del sistema

| Componente | Tecnología | Cómo se ejecuta en local |
|---|---|---|
| Aplicación de escritorio | Python 3.12, PySide6/QML, SQLite | En Windows, con `Iniciar_CorePulse.bat` (sin Docker) |
| Base de datos local de la app | SQLite | La crea la aplicación automáticamente |
| Sitio web | Next.js 16, React 19, TypeScript | Docker (`docker compose up`) o Node.js 22 |
| Base de datos web | PostgreSQL (Supabase) | Docker (`docker compose up`) o un proyecto de Supabase |
| Servidor de IA | Cloudflare Workers | Publicado en `https://ai.corepulse.cl`; la app lo usa sin configuración |

## 1. Sitio web y base de datos con Docker

Requisitos: Docker Desktop (o Docker Engine con Docker Compose).

```bash
cd "FASE 2/Evidencias Proyecto/Evidencias de sistema"
cp .env.example .env          # opcional: sin .env se usan los mismos valores por defecto
docker compose up -d --build
```

Resultado:

- **Sitio web:** http://localhost:3000
- **Base de datos web:** PostgreSQL en `localhost:5432` (usuario `corepulse`, contraseña `corepulse_local`, base `corepulse`), con las 13 tablas del modelo y sus datos iniciales.

Comandos útiles:

```bash
docker compose ps                                   # estado de los contenedores
docker compose logs base-datos                      # ver cómo se aplicaron las migraciones
docker compose exec base-datos psql -U corepulse -d corepulse -c "\dt public.*"
docker compose down                                 # detener
docker compose down -v                              # detener y borrar la base para empezar de cero
```

**Sobre la conexión del sitio con la base de datos.** El sitio no se conecta directo a PostgreSQL: usa los servicios de Supabase (inicio de sesión, API de datos y almacenamiento de imágenes). Por eso el contenedor `web` se conecta al proyecto de Supabase configurado en `.env` (por defecto, el proyecto real de CorePulse, con su clave pública). El contenedor `base-datos` permite revisar y probar el modelo de datos completo en local. Para que el sitio use una base propia, se crea un proyecto en Supabase, se ejecutan las migraciones de `Base de datos/supabase/migraciones/` y se ponen su URL y su clave pública en `.env`.

## 2. Sitio web sin Docker

Requisitos: Node.js 22 o superior.

```bash
cd "FASE 2/Evidencias Proyecto/Evidencias de sistema/Aplicación/CorePulse-web"
npm ci
cp .env.example .env.local    # completar con la URL y la clave pública de Supabase
npm run dev                   # http://localhost:3000
```

## 3. Aplicación de escritorio

La aplicación de escritorio **no se ejecuta en Docker**: es una aplicación de Windows con interfaz gráfica que lee directamente los sensores del equipo (CPU, GPU, discos, batería) y aplica ajustes de Windows. Un contenedor no tiene acceso a ese hardware ni a la interfaz de Windows.

Requisitos: Windows 10 u 11 de 64 bits y Python 3.12 o superior.

```bash
cd "FASE 2/Evidencias Proyecto/Evidencias de sistema/Aplicación/CorePulse_REBUILD_210"
Iniciar_CorePulse.bat
```

La primera vez prepara su propio entorno de Python e instala las dependencias (`requirements.txt`: PySide6, psutil, pythonnet y HardwareMonitor). Crea sus bases SQLite en `%LOCALAPPDATA%\CorePulse\rebuild\`. No necesita variables de entorno: la IA y la cuenta web ya vienen configuradas.

Pruebas automatizadas:

```bash
python -B -m pytest -p no:cacheprovider -q tests
```

## Verificación realizada

- Las 10 migraciones SQL se ejecutaron sobre PostgreSQL junto con el script de base local, sin errores.
- Los esquemas SQLite se ejecutaron con Python (`sqlite3`).
- El sitio web se compiló con `next build` y se sirvió con `next start` (los mismos comandos del Dockerfile): las páginas de inicio, precios y funciones responden y cargan sus datos desde Supabase.
