# Base de datos de CorePulse

Esta carpeta contiene los scripts y el modelo de datos del proyecto.

## Contenido

| Archivo o carpeta | Descripción |
|---|---|
| `modelo_datos.md` | Modelo de datos completo: tablas, columnas, relaciones, diagramas entidad-relación y seguridad |
| `sqlite/monitoring_history.sql` | Esquema de la base local de monitoreo de la aplicación de escritorio |
| `sqlite/game_sessions.sql` | Esquema de la base local de sesiones de juego |
| `supabase/migraciones/` | Los 10 scripts SQL de la base de datos web, en orden de ejecución (estructura, datos iniciales, cuentas, seguridad y funciones) |
| `supabase/00000000000000_base_local.sql` | Script de apoyo para ejecutar las migraciones en un PostgreSQL común (Docker), sin Supabase |

Las migraciones son una copia de `Aplicación/CorePulse-web/supabase/migrations/`, que es la carpeta que usa la herramienta de Supabase. Si se cambia una migración, hay que actualizar ambas copias.

## Base de datos local (aplicación de escritorio)

No hay que instalar nada. La aplicación crea las dos bases SQLite automáticamente la primera vez que se ejecuta, en `%LOCALAPPDATA%\CorePulse\rebuild\`.

Para revisar el esquema sin abrir la aplicación:

```bash
sqlite3 prueba.sqlite3 < sqlite/monitoring_history.sql
sqlite3 prueba.sqlite3 ".tables"
```

## Base de datos web

### Opción 1: PostgreSQL con Docker (recomendada para revisar)

Desde la carpeta `Evidencias de sistema`:

```bash
docker compose up -d base-datos
```

Esto levanta PostgreSQL 16 y ejecuta, en orden, el script de base local y las 10 migraciones. Quedan creadas las 13 tablas con sus datos iniciales (planes, preguntas, funciones, textos legales, etc.).

Para conectarse y revisar:

```bash
docker compose exec base-datos psql -U corepulse -d corepulse -c "\dt public.*"
docker compose exec base-datos psql -U corepulse -d corepulse -c "select slug, nombre, precio_mensual from public.planes;"
```

Las migraciones se ejecutan solo la primera vez que se crea el volumen. Para empezar de cero:

```bash
docker compose down -v
```

### Opción 2: Supabase

El sitio en producción usa Supabase. Para crear la base en un proyecto nuevo de Supabase, se ejecutan los archivos de `supabase/migraciones/` en orden en el editor SQL de Supabase, o con la CLI de Supabase desde `Aplicación/CorePulse-web` (`supabase db push`). En Supabase **no** se usa `00000000000000_base_local.sql`, porque Supabase ya incluye los usuarios, el almacenamiento y los roles.

## Verificación

Las 10 migraciones se probaron sobre PostgreSQL junto con el script de base local: se ejecutan sin errores, crean las 13 tablas del esquema `public`, cargan los 2 planes iniciales y, al registrar un usuario, el trigger crea su perfil con el plan `free`. Los dos scripts SQLite se probaron con el módulo `sqlite3` de Python.
