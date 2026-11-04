<p align="center">
  <img src="docs/corepulse_banner.svg" width="960" alt="CorePulse — El pulso real de tu PC">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Windows-10%20%7C%2011-1e9bdb?style=flat-square" alt="Windows 10 y 11">
  <img src="https://img.shields.io/badge/Python-3.12+-3776ab?style=flat-square" alt="Python 3.12 o posterior para desarrollo">
  <img src="https://img.shields.io/badge/Interfaz-Qt%20%2F%20QML-249f91?style=flat-square" alt="Qt y QML">
  <a href="FASE%202/Evidencias%20Proyecto/CorePulse_REBUILD_177"><img src="https://img.shields.io/badge/REBUILD-177-956bda?style=flat-square" alt="REBUILD 177"></a>
</p>

<p align="center">
  <a href="https://corepulse.cl">Sitio web</a> ·
  <a href="FASE%202/Evidencias%20Proyecto/CorePulse_REBUILD_177">Aplicación</a> ·
  <a href="#web">Documentación web</a> ·
  <a href="FASE%202/Evidencias%20Proyecto/CorePulse_REBUILD_177/versiones/HISTORIAL.md">Historial</a>
</p>

CorePulse reúne el monitoreo del equipo, el diagnóstico de Windows y las herramientas de rendimiento en una aplicación. Permite consultar el hardware, revisar el estado de los discos y registrar lo que ocurre durante una partida.

<p align="center">
  <img src="docs/corepulse_temas.gif" width="820" alt="Vista de CorePulse y sus temas oscuros">
</p>

## Funciones

| Área | Qué puedes hacer |
|---|---|
| **Monitoreo** | Consultar CPU, GPU, RAM, almacenamiento y las temperaturas disponibles. |
| **Diagnóstico y salud** | Revisar el sistema, consultar SMART/NVMe y generar un informe PDF. |
| **Juegos** | Usar el overlay propio, ver FPS y frametime, guardar sesiones y aplicar perfiles por juego. |
| **Benchmark** | Medir CPU, RAM, disco y GPU DirectX 11; guardar y comparar resultados. |
| **Mantenimiento** | Limpiar temporales, cachés y RAM; aplicar ajustes reversibles de Windows. |
| **Red** | Consultar adaptadores, tráfico y pruebas de velocidad. |
| **CorePulse AI** | Pedir explicaciones sobre las lecturas y comparar sesiones con los permisos elegidos. |
| **Personalización** | Elegir entre 15 temas oscuros y ajustar el diseño del overlay. |

Cuando una lectura no está disponible, se muestra **N/A**. La cobertura de los sensores depende del hardware, del controlador y de los permisos de Windows.

## Empezar

**Con el instalador:** ejecuta `CorePulse_Setup_177_x64.exe`. Incluye la aplicación, Python, Qt y sus componentes empaquetados. El instalador 177 se conserva localmente; su publicación en [Releases](https://github.com/tomashoytbarri24/Corepulse/releases) queda pendiente.

**Desde el código:** necesitas Windows 10/11 de 64 bits y Python 3.12 o posterior. Desde la raíz del repositorio, abre PowerShell y ejecuta:

```powershell
cd "FASE 2/Evidencias Proyecto/CorePulse_REBUILD_177"
.\Iniciar_CorePulse.bat
```

El primer inicio prepara el entorno. Algunas lecturas y acciones requieren permisos de administrador. El módulo interno del overlay se autoriza por juego; las exclusiones de antitrampas se explican en la documentación de la aplicación.

## Versión actual

La **REBUILD 177** conserva el overlay propio, su editor, la línea de frametime, las sesiones y los registros de problemas con PDF. Incorpora autorización por ejecutable, elevación opcional y recuperación del inicio ante una base SQLite dañada.

[Ver la aplicación](FASE%202/Evidencias%20Proyecto/CorePulse_REBUILD_177/README.md) · [Historial de versiones](FASE%202/Evidencias%20Proyecto/CorePulse_REBUILD_177/versiones/HISTORIAL.md) · [Validación de la entrega](FASE%202/Evidencias%20Proyecto/CorePulse_REBUILD_177/versiones/VALIDACION_177.json)

## Organización del proyecto

```text
FASE 1/                         Documentación de la primera fase
FASE 2/
├── Evidencias Grupales/
├── Evidencias Individuales/
└── Evidencias Proyecto/
    ├── CorePulse_REBUILD_177/   Aplicación de Windows
    └── CorePulse-web/          Sitio web y cuentas
FASE 3/                         Documentación de la tercera fase
docs/                           Recursos de este README
```

La web del proyecto está en **[corepulse.cl](https://corepulse.cl)**. Su código y las evidencias académicas se conservan junto a la aplicación en la estructura por fases.

## Documentación

<details>
<summary><b>Aplicación de Windows y CorePulse AI</b> · arquitectura, datos y desarrollo</summary>

### Arquitectura y desarrollo

#### Arquitectura

```mermaid
flowchart LR
    UI["🎨 ui/*.qml"] --> C["🎛️ main.py<br/>controladores Qt"]
    C --> CORE["🧠 core/<br/>monitoring · health · maintenance<br/>tweaks · benchmark · ai · cuenta"]
    CORE --> WIN["🪟 Windows<br/>psutil · HardwareMonitor · PowerShell/CIM<br/>Overlay propio · ETW · DirectX · powercfg"]
    CORE --> DB[("💾 %LOCALAPPDATA%\\CorePulse<br/>SQLite · JSON/JSONL · DPAPI")]
    CORE -- "🔐 solo con permiso" --> AI["☁️ ai.corepulse.cl<br/>Cloudflare Worker"]
    AI --> KB["📚 knowledge.mjs<br/>RAG curado"]
    AI --> LLM["🤖 GPT-OSS 120B<br/>vía Groq"]
```

**Separación de responsabilidades:** la interfaz nunca habla con Windows directo. Todo pasa por `core/`,
y lo pesado (WMI, sensores, NVIDIA-SMI) corre en hilos o procesos aparte para mantener la interfaz disponible.

<details>
<summary>📂 <b>¿Qué hay en cada carpeta?</b> (dentro de <code>FASE 2/Evidencias Proyecto/CorePulse_REBUILD_177/</code>)</summary>

<br>

| Carpeta | Contenido |
|---|---|
| `ui/` | Pantallas QML. `GlassPanel.qml` es el material Liquid Glass 🫧 que usan todas las tarjetas |
| `core/monitoring/` | Telemetría en vivo (CPU, GPU multivendedor, RAM, disco) |
| `core/health/` | Salud, diagnóstico, PDF, FPS, Game Boost, tendencias, almacenamiento |
| `core/maintenance/` | Limpieza, red, inicio de Windows, Speedtest y test de audio |
| `core/tweaks/` | Motor de tweaks reversibles 🔄 |
| `core/ai.py` | Cliente de CorePulse AI Cloud |
| `core/benchmark_gpu.py` | El benchmark DirectX 11 de la ciudad de neón 🏙️ |
| `cloud/corepulse-ai/` | El Worker de Cloudflare: API, RAG y control de cuotas |
| `tests/` | Suite pytest de la app y del cliente cloud |
| `versiones/HISTORIAL.md` | La bitácora de cada versión 📜 |

</details>

### 💾 Dónde guarda las cosas

Todo vive en `%LOCALAPPDATA%\CorePulse`:

| Archivo | Tipo | Para qué |
|---|---|---|
| `monitoring_history.sqlite3` → `samples` | 🗃️ SQLite | Muestras cada 30 s, retención de 90 días |
| `monitoring_history.sqlite3` → `windows_sessions` | 🗃️ SQLite | Un registro por arranque de Windows |
| `monitoring_history.sqlite3` → `alert_events` | 🗃️ SQLite | Historial de alertas con su fuente |
| `windows_tweaks_state.json` | 📄 JSON | Cómo estaba Windows antes de cada tweak ↩️ |
| `benchmark_historial.jsonl` | 📄 JSONL | Hasta 500 sesiones de benchmark |
| `cuenta.dat` | 🔒 DPAPI | Token de la cuenta, cifrado por Windows |
| `reportes\` | 📄 PDF | Informes de diagnóstico y de benchmark |

### 🏃 Ejecutar y probar

```bash
cd "FASE 2/Evidencias Proyecto/CorePulse_REBUILD_177"

# ▶️ Arrancar (prepara el entorno aislado la primera vez)
Iniciar_CorePulse.bat

# 🧪 Correr las pruebas sin dejar __pycache__
python -B -m pytest -p no:cacheprovider -q tests
```

**Validación del 03/11/2026:** 105 pruebas enfocadas Python y 61 de Node aprobadas.
La suite histórica tiene 286 aprobadas y las mismas 63 fallas de la 176; no se
declara completamente aprobada. Overlay y Sesiones abren sin avisos QML.

**Dependencias** (se instalan solas): `PySide6` · `psutil` · `pythonnet` · `HardwareMonitor`

---

## ☁️ CorePulse AI Cloud

El servidor de la IA vive en `FASE 2/Evidencias Proyecto/CorePulse_REBUILD_177/cloud/corepulse-ai/`: un **Cloudflare Worker** (`corepulse-ai-cloud`) publicado en **`https://ai.corepulse.cl`**. La app lo usa por defecto: el usuario no configura URL ni claves.

| Pieza | Detalle |
|---|---|
| 🧠 Modelo | GPT-OSS 120B vía **Groq** (`openai/gpt-oss-120b`). La clave del proveedor vive **solo** en Cloudflare como secreto |
| 📚 Conocimiento | RAG léxico sobre fichas oficiales curadas (Microsoft, Intel, AMD, NVIDIA) en `src/knowledge.mjs`, versión `corepulse-kb-v3`. Sin búsqueda web ni índice vectorial |
| 🔌 Rutas | `GET /v1/health` (solo confirma que responde) · `GET /v1/status` · `POST /v1/chat` · `POST /v1/analyze` (reglas propias, no gasta Groq) |
| 🚦 Límites | 8 consultas por minuto por usuario · **20** consultas generativas diarias por cuenta · **250** diarias y **3000** mensuales en total (Durable Object SQLite `MODEL_BUDGET`, reinicio en UTC) |

**Cómo responde la IA, paso a paso:**
1. 🔑 Verifica tu cuenta CorePulse contra `corepulse.cl/api/app/yo` (no confía en el `userId` que manda el cliente).
2. 🚦 Aplica el límite de consultas y el presupuesto **antes** de llamar al modelo; si no hay cupo responde `429` sin contactar a Groq.
3. 📚 Busca hasta 3 fichas oficiales relacionadas con tu pregunta (RAG).
4. 📏 Si comparás sesiones, **las reglas propias deciden** si el problema se repite (por ejemplo, CPU ≥ 90 °C durante 3 min). El modelo solo lo explica, y la respuesta trae resumen (`answer`) y dictamen completo (`details`) en una sola llamada.
5. 🔗 Las fuentes salen del catálogo, nunca del modelo.

<details>
<summary>🔐 <b>Privacidad del servidor</b></summary>

<br>

- El Worker no guarda conversaciones, IP ni telemetría en bases de datos; los contadores usan claves hash.
- Hardware: sin permiso se envía `{}`. Con permiso, solo nombres acotados y uso de CPU/GPU/RAM/disco, sin identificadores, rutas ni números de serie.
- Tendencias: un **permiso aparte, apagado por defecto**. Solo viajan contadores, picos y rachas calculados en el equipo; nunca muestras crudas, fechas exactas, nombres ni IDs.
- Nunca se aceptan mensajes de tipo `system` desde el cliente.
- Los límites cuentan **consultas**, no dinero ni tokens: configurar también alertas de gasto en el proveedor.

</details>

### 🚀 Probar y publicar el Worker

Desde PowerShell, con Node.js 22+:

```powershell
cd "FASE 2\Evidencias Proyecto\CorePulse_REBUILD_177\cloud\corepulse-ai"
npm.cmd install          # 📦 dependencias (Wrangler 4.151.1 fijado)
npm.cmd run verify       # ✅ sintaxis + 61 pruebas (simuladas, no gastan tokens)
npm.cmd audit            # 🔍 revisar antes de publicar; nunca "npm audit fix --force" a ciegas
npx.cmd wrangler whoami  # 👤 si no hay sesión: npx.cmd wrangler login (lo hace el dueño de la cuenta)
npx.cmd wrangler deploy  # 🚀 publicar en ai.corepulse.cl
```

> ⚠️ **No** volver a ejecutar `wrangler secret put`, **no** crear otro Worker, dominio ni Durable Object, y **nunca** subir tokens, claves ni `.dev.vars`.
> El deploy está completo solo cuando muestra `Deployed` junto a `ai.corepulse.cl` y un `Current Version ID`. `/v1/health` no prueba el modelo: la validación real es una pregunta autenticada desde la app.

</details>

<a id="web"></a>

<details>
<summary><b>Documentación de la web</b> · Supabase, cuentas, contenido y despliegue</summary>

> 📁 El código de la web está en [`FASE 2/Evidencias Proyecto/CorePulse-web/`](FASE%202/Evidencias%20Proyecto/CorePulse-web). Todas las rutas y comandos de esta parte son relativos a esa carpeta.

**Todo el contenido sale de Supabase**: textos, precios, planes, funciones, novedades, preguntas, legales e imágenes. En el código solo quedan etiquetas de interfaz (botones, menús). ¿Quieres cambiar un precio? Se edita una fila en Supabase y no hace falta tocar el código.

**Stack:** Next.js 16 (React 19) · Tailwind CSS 4 · Motion + Lenis (animaciones) · Supabase (base de datos, Auth y Storage) · Cloudflare Workers con OpenNext (hosting) en `https://corepulse.cl`.

### ⚡ CorePulse Web en 30 segundos

```mermaid
flowchart LR
    TU["🧑‍💻 Tú<br/>Table Editor"] -->|editas una fila| DB[("Supabase<br/>tablas + Storage")]
    DB -->|lectura| CF["☁️ Cloudflare Worker<br/>Next.js + OpenNext"]
    CF <-->|"caché 60 s<br/>respaldo 7 días"| CACHE[("Caché de<br/>Cloudflare")]
    CF -->|página| WEB["🌐 corepulse.cl"]
    APP["🖥️ App de escritorio"] -->|"/api/app/*"| CF
    CF -->|"cuentas y planes"| DB
```

Si Supabase se cae, la web sigue funcionando con la última copia guardada.

#### Así inicia sesión la app de escritorio (sin pedir la contraseña)

```mermaid
sequenceDiagram
    autonumber
    participant App as 🖥️ App
    participant Nav as 🌐 Navegador
    participant Web as ☁️ corepulse.cl
    App->>App: genera verificador secreto<br/>y escucha en 127.0.0.1
    App->>Nav: abre /app/conectar?reto=SHA-256(verificador)
    Nav->>Web: el usuario inicia sesión y pulsa «Autorizar este equipo»
    Web-->>App: redirige a 127.0.0.1/callback con un código (2 min)
    App->>Web: POST /api/app/token (código + verificador)
    Web-->>App: token de equipo 🎟️
    App->>Web: GET /api/app/yo
    Web-->>App: nombre, email y plan
```

### 🚀 Puesta en marcha

<details>
<summary><b>1. Supabase</b> · base de datos, cuentas e imágenes</summary>

1. **SQL Editor** → ejecuta en orden los archivos de `supabase/migrations/`:
   1. `…_contenido.sql`: tablas del contenido, seguridad (RLS) y bucket `capturas`.
   2. `…_datos_iniciales.sql`: el contenido actual de la web (se puede repetir sin duplicar).
   3. `…_cuentas.sql`: perfiles de usuario con su plan.
   4. `…_precios_clp_y_limite_free.sql`: precios en pesos chilenos y plan Free con 2 usos por función.
   5. `…_app_escritorio.sql`: inicio de sesión de la app de escritorio.
   6. `…_caducidad_tokens_app.sql`: los tokens de la app caducan (30 días sin uso o 180 días desde que se conectó el equipo).
   7. `…_administradores.sql`: cuentas admin que pueden cambiar los precios desde `/cuenta/admin`.
   8. `…_gestionar_admins.sql`: los admins dan o quitan admin a otras cuentas por email.
   9. `…_capturas_windows.sql`: usa las capturas sacadas en Windows (con todas las métricas visibles).
   10. `…_novedades_github.sql`: vacía Novedades y la prepara para recibir las versiones desde GitHub.
2. **Authentication → URL Configuration:**
   - *Site URL:* `https://corepulse.cl`.
   - *Redirect URLs:* añade `https://corepulse.cl/auth/callback` y `http://localhost:3000/auth/callback`.
3. **Authentication → Sign In / Providers → Email:** deja activado *Confirm email*.
4. Copia `.env.example` como `.env.local` y rellena las claves (**Project Settings → API Keys**).
5. Sube las imágenes al Storage:
   ```bash
   npm run subir-capturas
   ```

</details>

<details>
<summary><b>2. Cloudflare Workers</b> · hosting en corepulse.cl</summary>

1. **Workers & Pages → Create → Import a repository** → elige el repositorio (Workers Builds) e indica como *Root directory* la carpeta `FASE 2/Evidencias Proyecto/CorePulse-web`. Usa la configuración por defecto: `npm run build` compila con OpenNext y `wrangler.jsonc` define el Worker y los dominios `corepulse.cl` y `www.corepulse.cl`.
2. Las variables públicas de compilación (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_SITE_URL`) están en `.env.production`. Si prefieres definirlas en Cloudflare, ponlas en **Settings → Build → Variables** y en **Settings → Variables and Secrets**.
3. Cada `git push` a la rama configurada en Workers Builds vuelve a publicar. A mano: `npm run deploy`.

> [!WARNING]
> Las variables `NEXT_PUBLIC_*` se incrustan al compilar: si las cambias, lanza una nueva compilación.
> **Nunca** pongas `SUPABASE_SECRET_KEY` en Cloudflare: solo se usa en tu equipo para subir imágenes.

</details>

### ✏️ Editar el contenido

Todo se edita en **Supabase → Table Editor**. La web se actualiza sola en un máximo de **60 segundos**: las lecturas de Supabase se guardan un minuto en la caché de Cloudflare (`src/lib/supabase/cache.ts`). Si Supabase falla, la web sigue mostrando la última copia guardada (hasta 7 días). En local (`npm run dev`) no hay caché y los cambios se ven al instante.

<details>
<summary><b>¿Qué tabla cambia qué?</b></summary>

| Tabla | Qué controla |
|---|---|
| `ajustes` | Textos por página en JSON: `sitio` (nombre, versión, enlace de descarga, email de soporte), `inicio`, `funciones`, `precios`, `descargar`, `novedades` |
| `planes` | Planes Free/Pro: nombre, precios mensual y anual, botón. `moneda` con código ISO (`CLP`, `USD`…) usa el formato oficial (`$4.990`) |
| `plan_caracteristicas` | Filas de la comparativa (`true`, `false` o un texto como `"2 usos"`) |
| `preguntas` | Preguntas frecuentes (sección `precios`) |
| `funciones` | Módulos de la página Funciones; `en_portada` los muestra en la sección fija del inicio |
| `destacados` | Tarjetas del inicio (icono: `gamepad`, `thermo`, `wrench`, `bolt`, `lock`) |
| `cifras` | Contadores animados del inicio |
| `temas` | Galería horizontal de temas |
| `versiones` | Página Novedades. Se llena sola desde los Releases de GitHub (ver «Novedades desde GitHub» más abajo); también se pueden añadir filas a mano |
| `documentos_legales` | Términos, privacidad y reembolsos (crear una fila nueva publica `/legal/<slug>`) |
| `perfiles` | Usuarios registrados y su plan (`free`/`pro`) |

Las imágenes van en **Storage → capturas**; en las tablas se escribe solo el nombre del archivo (`summary.jpg`).

</details>

<details>
<summary><b>📸 Cambiar capturas</b></summary>

1. Saca las capturas nuevas de la app (mejor en Windows, con la ventana en proporción ~16:9.5, como 1800×1068) y ponlas en `contenido/capturas-nuevas/` con el nombre de la que reemplazan, en cualquier formato: `summary.png`, `health.png`, `tweaks.png`, `cleanup.png`, `themes.png`, `tema_aurora.png`, `tema_violet.png`, `tema_ember.png`, `tema_sakura.png`, `tema_cyber.png`. Puedes cambiar solo algunas.
2. `npm run actualizar-capturas -- --prueba` las deja preparadas en `contenido/capturas/` para revisarlas (1800×1068, WebP).
3. `npm run actualizar-capturas` las prepara, las sube a Supabase y cambia las tablas (`funciones`, `temas`, `ajustes`). Necesita `SUPABASE_SECRET_KEY` en `.env.local`.
4. Haz commit de `contenido/capturas/` para que el repositorio quede igual que la web.

Cada subida usa un nombre nuevo (`summary-20261015-1830.webp`): las imágenes llevan 7 días de caché y con el mismo nombre los navegadores seguirían mostrando la vieja. La captura usada como vista previa en redes (`ajustes.sitio.imagenSocial`) se genera además en JPEG de 1200×630.

</details>

### 📰 Novedades desde GitHub

Cuando publicas un **Release** en el repositorio del programa, una GitHub Action lo guarda en la tabla `versiones` y aparece en [`/novedades`](https://corepulse.cl/novedades) en menos de un minuto. Si editas o borras el Release, la web también se actualiza.

<details>
<summary><b>Conectarlo (una sola vez) y cómo escribir el Release</b></summary>

1. Ejecuta la migración `…_novedades_github.sql` en Supabase.
2. En Supabase, **Project Settings → API Keys → Secret keys → New secret key**, llámala `github-novedades`. Úsala solo para esto: si algún día se filtra, la borras sin afectar al resto.
3. En el repositorio **del programa**, **Settings → Secrets and variables → Actions → New repository secret**:
   - `SUPABASE_URL`: la URL del proyecto (`https://….supabase.co`).
   - `SUPABASE_NOVEDADES_KEY`: la clave del paso 2.
4. Copia [`docs/github/novedades-web.yml`](FASE%202/Evidencias%20Proyecto/CorePulse-web/docs/github/novedades-web.yml) a `.github/workflows/novedades-web.yml` del programa y haz commit.

| En GitHub | En la web |
|---|---|
| Etiqueta (tag), sin espacios, p. ej. `REBUILD-146` | La versión: los guiones se ven como espacios («REBUILD 146») |
| Nombre del Release | El título |
| Primer párrafo del texto | La explicación corta |
| Cada línea que empieza por `- ` | Un cambio de la lista |

```markdown
La limpieza de RAM ahora tarda la mitad y hay un tema nuevo.

- Limpieza de RAM en un clic desde la bandeja.
- Nuevo tema Ocean.
```

Los borradores y las *pre-release* no se publican. El enlace «Ver en GitHub» solo aparece si el repositorio del programa es público.

**Detalles técnicos:**
- Cada Release se guarda en la tabla `versiones` con su `github_id`. Al editar el Release se actualiza la misma fila (`on_conflict=github_id`) y al borrarlo se borra la fila.
- Columnas: `version` (tag, con `-` y `_` cambiados por espacios), `titulo` (nombre), `resumen` (texto que no es lista ni título, máx. 600 caracteres), `cambios` (líneas `- `, `* ` o `+ `), `enlace` (vacío si el repositorio es privado), `publicado` (fecha del Release), `origen = 'github'`.
- La web lee Supabase con la caché de 60 segundos, por eso tarda hasta un minuto en verse.
- La clave vive solo en los Secrets de GitHub, nunca en Cloudflare.

</details>

### 👤 Cuentas

- `/registro`, `/login`, `/recuperar`, `/cuenta`, `/cuenta/contrasena`, `/logout` (las mismas rutas que abre el menú de la app).
- Contraseña mínima de 8 caracteres y confirmación por email.
- El **plan** solo lo cambia el servidor o tú desde el panel: la seguridad de la base de datos impide que un usuario se lo cambie.
- **Admin:** en el SQL Editor, `update public.perfiles set es_admin = true where id = (select id from auth.users where email = 'tu@email.com');`. Hace falta solo para el primer admin: desde `/cuenta/admin` cualquier admin cambia los precios (solo los precios; el resto de la tabla `planes` se sigue editando en Supabase) y da o quita admin a otras cuentas por email. Nadie puede quitarse el admin a sí mismo.

<details>
<summary><b>🖥️ Inicio de sesión desde la app de escritorio, paso a paso</b></summary>

La app nunca pide la contraseña: abre `/app/conectar` en el navegador y la web la devuelve a la app.

1. La app genera un verificador secreto, abre `/app/conectar?puerto=…&estado=…&reto=…` (reto = SHA-256 del verificador) y escucha solo en `127.0.0.1`.
2. El usuario inicia sesión (si hace falta) y pulsa **Autorizar este equipo** → la web crea un código de un solo uso (2 min) y redirige a `http://127.0.0.1:<puerto>/callback`.
3. La app canjea código + verificador en `POST /api/app/token` y recibe un token de equipo.
4. Con ese token: `GET /api/app/yo` (nombre, email, plan) y `POST /api/app/salir` (cerrar sesión).
5. El token caduca tras **30 días sin usarse** o a los **180 días** de conectar el equipo. Entonces `GET /api/app/yo` responde `401` y la app debe volver al paso 1.
6. Límite por IP (Rate Limiting de Cloudflare, en `wrangler.jsonc`): 10 canjes por minuto en `/api/app/token` y 60 peticiones por minuto en `/api/app/yo` y `/api/app/salir`. Al pasarse, la API responde `429` con `Retry-After: 60`.

En la base solo hay huellas SHA-256 de códigos y tokens (tablas `codigos_app` y `sesiones_app`, migración `…_app_escritorio.sql`). Cada usuario ve y desconecta sus equipos en **Mi cuenta**.

</details>

### 🛠️ Comandos

<details>
<summary><b>Ver todos</b></summary>

```bash
cd "FASE 2/Evidencias Proyecto/CorePulse-web"
npm run dev             # desarrollo en http://localhost:3000 (necesita .env.local)
npm run build           # compilación de producción (OpenNext para Cloudflare)
npm run preview         # compila y prueba en local con el entorno de Workers
npm run deploy          # compila y publica en Cloudflare
npm run lint
npm run subir-capturas  # sube contenido/capturas a Supabase Storage
npm run actualizar-capturas  # cambia capturas: prepara, sube y actualiza las tablas (ver «Cambiar capturas»)
```

</details>

</details>

<details>
<summary><b>Versiones y trabajo en equipo</b> · reglas del proyecto y Git</summary>

### Cómo se trabaja en el proyecto

### 📜 Reglas para crear una versión nueva

```text
📖  Leer completos "Reglas para crear Versiones nuevas.txt" y versiones/HISTORIAL.md
✍️  Agregar la entrada ARRIBA del historial: base · cambios · validación · reversión
🧹  Quitar el código que quedó obsoleto; no llenar el proyecto de .py nuevos
🧪  Correr las pruebas: ninguna versión debería sumar fallos nuevos
📦  Guardar el ZIP de respaldo de la versión anterior (con el TXT de reglas adentro)
```

### 🌳 Trabajo con Git

| ✅ Sí | ❌ No |
|---|---|
| `git pull` antes de subir | `git push --force` sobre `main` 💥 |
| Una rama por integrante (`maxi/corepulse-dev`, ...) | Subir tokens, claves o `.env` |
| Mensajes de commit claros | Subir `__pycache__` o entornos virtuales |

</details>

## Equipo

<table>
  <tr>
    <td align="center" width="250">
      <a href="https://github.com/tomashoytbarri24"><img src="https://github.com/tomashoytbarri24.png" width="64" height="64" alt="Tomás Hoyt"><br><b>Tomás Hoyt</b></a><br>
      Arquitectura · Telemetría · IA
    </td>
    <td align="center" width="250">
      <a href="https://github.com/agtttttttttttt"><img src="https://github.com/agtttttttttttt.png" width="64" height="64" alt="Agustín Valdés"><br><b>Agustín Valdés</b></a><br>
      Web · Validación · Documentación
    </td>
    <td align="center" width="250">
      <a href="https://github.com/maxicpa"><img src="https://github.com/maxicpa.png" width="64" height="64" alt="Maximiliano Carrasco"><br><b>Maximiliano Carrasco</b></a><br>
      Interfaz · Benchmark · Pruebas
    </td>
  </tr>
</table>

Proyecto **Capstone · PTY4614** — Ingeniería en Informática, **Duoc UC Valparaíso**.