# Modelo de datos de CorePulse

CorePulse usa dos bases de datos con propósitos distintos:

1. **Base de datos local (SQLite)**, dentro del equipo del usuario. La crea y usa la aplicación de escritorio. Guarda el historial de monitoreo, las alertas y las sesiones de juego. Estos datos **nunca salen del equipo**.
2. **Base de datos web (PostgreSQL en Supabase)**, en la nube. La usa el sitio corepulse.cl. Guarda el contenido del sitio, las cuentas de usuario y el enlace seguro entre la aplicación de escritorio y la cuenta web.

Además, la aplicación guarda respaldos en archivos JSON/JSONL (estado original de cada optimización de Windows, historial de benchmark) y el token de la cuenta cifrado con DPAPI de Windows (`cuenta.dat`). La contraseña del usuario nunca se guarda en el equipo.

## 1. Base de datos local: monitoreo

Archivo: `%LOCALAPPDATA%\CorePulse\rebuild\monitoring_history.sqlite3`. Script: [`sqlite/monitoring_history.sql`](sqlite/monitoring_history.sql).

| Tabla | Clave primaria | Descripción |
|---|---|---|
| windows_sessions | id | Una fila por cada arranque de Windows, con su hora de arranque, primera y última muestra, y cierre |
| samples | ts | Muestras de uso cada 30 segundos (CPU, GPU, RAM, disco, temperaturas, batería y disco). Se conservan 90 días |
| alert_events | id | Cada cambio de estado de una alerta, con su valor, detalle y fuente del dato |

Relación: cada muestra (`samples.session_id`) pertenece a una sesión de Windows (`windows_sessions.id`). Una sesión de Windows tiene muchas muestras (relación uno a muchos).

```mermaid
erDiagram
    windows_sessions ||--o{ samples : "agrupa"
    windows_sessions {
        TEXT id PK
        REAL boot_ts
        REAL first_seen
        REAL last_seen
        REAL end_ts
        TEXT end_source
    }
    samples {
        REAL ts PK
        TEXT session_id FK
        REAL cpu
        REAL gpu
        REAL ram
        REAL disk
        REAL cpu_temp
        REAL gpu_temp
        TEXT battery_state
        TEXT disk_state
    }
    alert_events {
        INTEGER id PK
        REAL ts
        TEXT key
        TEXT title
        TEXT state
        TEXT value
        TEXT detail
        TEXT source
    }
```

## 2. Base de datos local: sesiones de juego

Archivo: `%LOCALAPPDATA%\CorePulse\rebuild\game_sessions.sqlite3`. Script: [`sqlite/game_sessions.sql`](sqlite/game_sessions.sql).

| Tabla | Clave primaria | Descripción |
|---|---|---|
| sessions | id | Una fila por partida: juego, inicio, término, tiempo activo, FPS (promedio, mínimo, máximo, 1 % low), picos de CPU y GPU, y plan de energía |
| samples | id | Lecturas durante la partida (FPS, CPU, GPU, RAM y temperaturas) |
| events | id | Incidencias de la partida, como caídas de FPS o temperatura alta |
| profiles | game_key | Preferencias por juego: plan de energía, esquina del overlay y temperaturas |

Relaciones: una partida (`sessions`) tiene muchas lecturas (`samples`) y muchas incidencias (`events`). Las claves foráneas usan `ON DELETE CASCADE`: al borrar una partida se borran sus lecturas e incidencias. `profiles` se relaciona con `sessions` por `game_key`.

```mermaid
erDiagram
    sessions ||--o{ samples : "tiene"
    sessions ||--o{ events : "registra"
    profiles ||--o{ sessions : "configura (game_key)"
    sessions {
        INTEGER id PK
        TEXT game_key
        TEXT name
        TEXT executable
        REAL started
        REAL ended
        INTEGER active_seconds
        REAL fps_min
        REAL fps_max
        REAL low_1
        REAL cpu_peak
        REAL gpu_peak
        TEXT plan_name
    }
    samples {
        INTEGER id PK
        INTEGER session_id FK
        REAL ts
        REAL fps
        REAL cpu
        REAL gpu
        REAL ram
    }
    events {
        INTEGER id PK
        INTEGER session_id FK
        REAL ts
        TEXT kind
        TEXT title
        TEXT detail
    }
    profiles {
        TEXT game_key PK
        TEXT name
        TEXT plan_guid
        TEXT corner
        TEXT temperatures
    }
```

## 3. Base de datos web (Supabase / PostgreSQL)

Scripts: [`supabase/migraciones/`](supabase/migraciones/) (10 migraciones, en orden de fecha).

### 3.1 Cuentas de usuario y aplicación de escritorio

| Tabla | Clave primaria | Descripción |
|---|---|---|
| auth.users | id | Usuarios registrados. La administra Supabase Auth (correo y contraseña cifrada) |
| perfiles | id (FK a auth.users) | Nombre, plan (free o pro), vencimiento del plan y si es administrador. Se crea solo al registrarse (trigger `al_crear_usuario`) |
| codigos_app | hash | Código de un solo uso (2 minutos) para conectar la app de escritorio con la cuenta. Solo se guarda su huella SHA-256 |
| sesiones_app | id | Equipos conectados a la cuenta: huella del token, creación, último uso, caducidad y si fue desconectado |

Relaciones: un usuario tiene un perfil (uno a uno), muchos códigos de conexión y muchos equipos conectados (uno a muchos). Todas usan `ON DELETE CASCADE`: si se borra el usuario, se borran sus datos.

```mermaid
erDiagram
    users ||--|| perfiles : "tiene"
    users ||--o{ codigos_app : "genera"
    users ||--o{ sesiones_app : "conecta"
    users {
        uuid id PK
        text email
        jsonb raw_user_meta_data
    }
    perfiles {
        uuid id PK, FK
        text nombre
        text plan
        timestamptz plan_vence
        boolean es_admin
        timestamptz creado
    }
    codigos_app {
        text hash PK
        uuid usuario FK
        text reto
        timestamptz vence
        boolean usado
    }
    sesiones_app {
        uuid id PK
        uuid usuario FK
        text hash
        timestamptz creada
        timestamptz ultimo_uso
        timestamptz caduca
        boolean revocada
    }
```

### 3.2 Contenido del sitio

Tablas independientes (sin relaciones entre sí) que el sitio lee para mostrar su contenido. Todas se pueden leer públicamente y solo se modifican desde el panel de administración o con migraciones.

| Tabla | Clave primaria | Descripción |
|---|---|---|
| ajustes | clave | Textos y opciones generales del sitio (JSON) |
| planes | slug | Planes Free y Pro con precios en CLP |
| plan_caracteristicas | id | Comparación de funciones entre planes |
| preguntas | id | Preguntas frecuentes |
| funciones | slug | Funciones de la aplicación con su captura |
| destacados | id | Bloques destacados de la portada |
| cifras | id | Cifras de la portada |
| temas | id | Temas visuales de la aplicación |
| versiones | id | Versiones publicadas (se sincronizan desde GitHub) |
| documentos_legales | slug | Términos y política de privacidad |

### 3.3 Seguridad

- Todas las tablas tienen **seguridad por fila (RLS)** activada.
- El contenido del sitio se puede leer, pero no modificar desde el navegador.
- Cada usuario solo puede ver y modificar su propio perfil y sus propios equipos.
- Los códigos y tokens de la app se guardan como huellas SHA-256, nunca en texto plano.
- Las operaciones sensibles (conectar la app, dar o quitar administrador) se hacen con funciones `security definer` que validan los permisos.
