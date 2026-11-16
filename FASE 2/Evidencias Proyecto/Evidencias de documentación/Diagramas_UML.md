# Diagramas UML de CorePulse

Diagramas UML del sistema CorePulse (REBUILD 210 y sitio web corepulse.cl). Los nombres de clases y métodos corresponden al código fuente en `Evidencias de sistema/Aplicación/`. Los diagramas están escritos en Mermaid, que GitHub muestra como imagen.

Contenido:

1. Diagrama de casos de uso
2. Diagrama de componentes
3. Diagrama de clases (controladores principales)
4. Diagrama de secuencia: aplicar y restaurar un tweak
5. Diagrama de secuencia: conectar la app con la cuenta web
6. Diagrama de secuencia: consulta a CorePulse AI
7. Diagrama de despliegue

El modelo de datos y sus diagramas entidad-relación están en `Evidencias de sistema/Base de datos/modelo_datos.md`.

---

## 1. Diagrama de casos de uso

Actores: **Usuario** (cualquier persona que usa CorePulse en su PC), **Jugador** (usuario que usa las funciones de juego), **Administrador del sitio** (integrante del equipo que gestiona el contenido web) y los sistemas externos **Windows**, **CorePulse AI Cloud** y **Ookla**.

```mermaid
flowchart LR
    U(["👤 Usuario"])
    J(["🎮 Jugador"])
    A(["🛠️ Administrador del sitio"])
    W(["🪟 Windows"])
    IA(["☁️ CorePulse AI Cloud"])
    OK(["🌐 Ookla"])

    subgraph CorePulse["Aplicación CorePulse"]
        CU1(("Ver telemetría<br/>en tiempo real"))
        CU2(("Diagnosticar<br/>el equipo"))
        CU3(("Revisar salud<br/>y reparar Windows"))
        CU4(("Aplicar o restaurar<br/>optimizaciones"))
        CU5(("Limpiar<br/>el sistema"))
        CU6(("Exportar<br/>informe PDF"))
        CU7(("Consultar a<br/>CorePulse AI"))
        CU8(("Ejecutar<br/>benchmark"))
        CU9(("Medir velocidad<br/>de red"))
        CU10(("Usar overlay<br/>y medir FPS"))
        CU11(("Revisar sesiones<br/>de juego"))
        CU12(("Conectar la app<br/>con su cuenta"))
    end

    subgraph Web["Sitio web corepulse.cl"]
        CW1(("Crear cuenta e<br/>iniciar sesión"))
        CW2(("Ver planes<br/>y descargas"))
        CW3(("Gestionar contenido<br/>y precios"))
    end

    U --- CU1 & CU2 & CU3 & CU4 & CU5 & CU6 & CU7 & CU8 & CU9 & CU12
    U --- CW1 & CW2
    J --- CU10 & CU11 & CU8
    A --- CW3
    CU1 & CU2 & CU3 & CU4 & CU5 & CU10 --- W
    CU7 --- IA
    CU9 --- OK
    CU12 -. "incluye" .-> CW1
```

| Caso de uso | Descripción |
|---|---|
| Ver telemetría en tiempo real | Muestra uso y temperatura de CPU, GPU, RAM y discos, con su fuente o N/A |
| Diagnosticar el equipo | Revisa el equipo y entrega un estado general con hallazgos |
| Revisar salud y reparar Windows | Batería, almacenamiento SMART/NVMe, análisis y reparación con DISM/SFC, recuperación |
| Aplicar o restaurar optimizaciones | Aplica un tweak guardando el valor original y lo restaura cuando el usuario quiera |
| Limpiar el sistema | Temporales, caché, RAM, Papelera y DNS, con confirmación |
| Exportar informe PDF | Genera un informe con lecturas, diagnóstico y resultados |
| Consultar a CorePulse AI | Pregunta sobre el equipo; la IA solo usa los datos que el usuario autoriza |
| Ejecutar benchmark | Pruebas de CPU, RAM, disco y GPU con veredicto e historial |
| Medir velocidad de red | Prueba con la CLI oficial de Ookla sobre el adaptador verificado |
| Usar overlay y medir FPS | Muestra FPS y uso del equipo sobre el juego |
| Revisar sesiones de juego | Historial de partidas con FPS, 1 % low e incidencias |
| Conectar la app con su cuenta | Inicia sesión en la web y autoriza el equipo sin escribir la contraseña en la app |

---

## 2. Diagrama de componentes

La aplicación de escritorio tiene tres capas: la interfaz QML, los controladores que `main.py` expone a QML y los módulos de `core/`. La interfaz nunca accede directo a Windows.

```mermaid
flowchart TB
    subgraph Presentacion["Capa de presentación (ui/*.qml)"]
        UI["Pantallas QML<br/>Resumen · Salud · Tweaks · Limpieza · Red<br/>Benchmark · Overlay · Sesiones · IA · Cuenta"]
    end

    subgraph Control["Capa de control (main.py)"]
        CTX["Controladores expuestos a QML<br/>telemetry · tweaks · cleanup · systemHealth<br/>overlayController · gameSessions · benchmarkController<br/>reportExporter · corepulseAI · cuenta · networkSpeedTest"]
    end

    subgraph Dominio["Capa de dominio (core/)"]
        MON["monitoring<br/>Telemetry"]
        HEA["health<br/>SystemHealth · StorageHealth · BatteryHealth<br/>WindowsHealth · RepairHealth · RecoveryHealth<br/>PerformanceHealth · MonitoringInsights<br/>PresentMonFPSReader · GameSessionStore · ReportExporter"]
        MAI["maintenance<br/>CleanupManager · NetworkHealth · StartupManager"]
        TWK["tweaks<br/>TweaksManager"]
        OVL["overlay<br/>OverlayController · GlobalHotkeys"]
        BEN["benchmark<br/>BenchmarkController · benchmark_gpu.py (D3D11Renderer)"]
        AIC["ai<br/>AIController · CorePulseCloudGateway"]
        CTA["cuenta<br/>CuentaManager"]
    end

    subgraph Externos["Recursos externos"]
        WIN["Windows<br/>psutil · LibreHardwareMonitor · PowerShell/CIM<br/>Registro · powercfg · ETW/PresentMon · DirectX 11"]
        DB[("Datos locales<br/>SQLite · JSON · DPAPI")]
        CLOUD["Servicios en la nube<br/>ai.corepulse.cl · corepulse.cl · Ookla"]
    end

    UI --> CTX
    CTX --> MON & HEA & MAI & TWK & OVL & BEN & AIC & CTA
    MON & HEA & MAI & TWK & OVL & BEN --> WIN
    HEA & TWK & MAI --> DB
    CTA --> DB
    AIC --> CLOUD
    CTA --> CLOUD
    MAI --> CLOUD
```

---

## 3. Diagrama de clases (controladores principales)

Clases principales y sus dependencias, según cómo se construyen en `main.py`. Se muestran solo los atributos y métodos más relevantes.

```mermaid
classDiagram
    class Telemetry {
        +close()
    }
    class SystemHealth
    class BatteryHealth
    class StorageHealth
    class WindowsHealth
    class RecoveryHealth
    class PerformanceHealth
    class MonitoringInsights {
        -monitoring_history.sqlite3
    }
    class CuentaManager {
        +iniciarSesion()
        +cerrarSesion()
    }
    class AIController {
        +setInternetOnline(online)
    }
    class CorePulseCloudGateway {
        +chat(token, question, snapshot, history)
        +chat_structured(token, question, snapshot, history)
    }
    class TweaksManager {
        +applyTweak(tweak_id) str
        +restoreTweak(tweak_id) str
        +close()
    }
    class CleanupManager {
        +close()
    }
    class OverlayController {
        +setThemePalette(palette)
    }
    class GlobalHotkeys
    class PresentMonFPSReader
    class GameSessionsController
    class GameSessionStore {
        -game_sessions.sqlite3
    }
    class ProblemCapture
    class BenchmarkController
    class BenchmarkGpuScript {
        +D3D11Renderer
        +escena DirectX 11
    }
    class ReportExporter

    SystemHealth --> Telemetry
    SystemHealth --> BatteryHealth
    SystemHealth --> StorageHealth
    SystemHealth --> WindowsHealth
    SystemHealth --> RecoveryHealth
    MonitoringInsights --> Telemetry
    MonitoringInsights --> SystemHealth
    AIController --> Telemetry
    AIController --> SystemHealth
    AIController --> CuentaManager
    AIController --> MonitoringInsights
    AIController --> CorePulseCloudGateway
    OverlayController --> Telemetry
    OverlayController --> PerformanceHealth
    OverlayController --> CleanupManager
    OverlayController --> StorageHealth
    OverlayController --> GlobalHotkeys
    OverlayController --> PresentMonFPSReader
    GameSessionsController --> Telemetry
    GameSessionsController --> PerformanceHealth
    GameSessionsController --> OverlayController
    GameSessionsController --> GameSessionStore
    ProblemCapture --> OverlayController
    BenchmarkController ..> BenchmarkGpuScript : ejecuta benchmark_gpu.py en otro proceso
    ReportExporter --> Telemetry
    ReportExporter --> SystemHealth
    ReportExporter --> MonitoringInsights
    ReportExporter --> WindowsHealth
    ReportExporter --> AIController
    ReportExporter --> BenchmarkController
```

---

## 4. Diagrama de secuencia: aplicar y restaurar un tweak

Muestra cómo `TweaksManager` garantiza que cada cambio en Windows sea reversible: guarda el valor original antes de escribir y verifica el resultado.

```mermaid
sequenceDiagram
    actor U as Usuario
    participant Q as TweaksPage (QML)
    participant T as TweaksManager
    participant B as Respaldo (tweaks_originales.json)
    participant R as Registro de Windows

    U->>Q: Pulsa "Aplicar" y confirma
    Q->>T: applyTweak(tweak_id)
    T->>R: Leer valor actual
    alt El valor ya es el deseado
        T-->>Q: "El ajuste ya está activo"
    else Hay que cambiarlo
        T->>B: Guardar valor original
        Note over T,B: Si no se puede guardar, no se modifica Windows
        T->>R: Escribir valor nuevo
        T->>R: Verificar que Windows conservó el valor
        alt Verificado
            T-->>Q: "Ajuste aplicado y valor verificado"
        else No verificado
            T-->>Q: "No confirmado: respaldo original conservado"
        end
    end

    U->>Q: Pulsa "Restaurar"
    Q->>T: restoreTweak(tweak_id)
    T->>B: Leer valor original
    T->>R: Restaurar valor original
    T->>R: Verificar restauración
    T->>B: Eliminar el respaldo de ese ajuste
    T-->>Q: "Windows restaurado y verificado"
```

---

## 5. Diagrama de secuencia: conectar la app con la cuenta web

La app de escritorio nunca recibe ni guarda la contraseña del usuario. Usa un código de un solo uso con verificador (PKCE).

```mermaid
sequenceDiagram
    actor U as Usuario
    participant App as CorePulse (CuentaManager)
    participant Nav as Navegador
    participant Web as corepulse.cl
    participant DB as Supabase (PostgreSQL)

    U->>App: Pulsa "Iniciar sesión"
    App->>App: Crear verificador y reto (PKCE)
    App->>Nav: Abrir corepulse.cl/app/conectar con el reto
    Nav->>Web: El usuario inicia sesión
    U->>Web: Pulsa "Autorizar este equipo"
    Web->>DB: crear_codigo_app(reto): código de un solo uso (2 minutos)
    Web-->>Nav: Redirigir a http://127.0.0.1:puerto/callback con el código
    Nav->>App: Entregar el código al servidor local de la app
    App->>Web: POST /api/app/token (código + verificador)
    Web->>DB: canjear_codigo_app(código, verificador)
    DB-->>Web: Token de equipo (se guarda solo su huella SHA-256)
    Web-->>App: Token de equipo
    App->>App: Guardar el token cifrado con DPAPI (cuenta.dat)
    App->>Web: GET /api/app/yo
    Web-->>App: Nombre y plan del usuario
```

---

## 6. Diagrama de secuencia: consulta a CorePulse AI

El servidor verifica la cuenta y los límites de uso antes de llamar al modelo. Los datos del equipo solo viajan si el usuario activó ese permiso.

```mermaid
sequenceDiagram
    actor U as Usuario
    participant App as CorePulse (AIController)
    participant AI as ai.corepulse.cl (Cloudflare Worker)
    participant Web as corepulse.cl
    participant KB as Conocimiento curado (RAG)
    participant M as Modelo (Groq)

    U->>App: Escribe una pregunta
    App->>App: Armar resumen del equipo solo si hay permiso
    App->>AI: POST /v1/chat (token, pregunta, resumen)
    AI->>Web: GET /api/app/yo (verificar la cuenta)
    Web-->>AI: Cuenta válida
    AI->>AI: Revisar límites (8 por minuto, 20 diarias)
    alt Sin cupo
        AI-->>App: 429 (sin llamar al modelo)
    else Con cupo
        AI->>KB: Buscar fichas oficiales relacionadas
        KB-->>AI: Hasta 3 fichas
        AI->>M: Pregunta + fichas + resumen autorizado
        M-->>AI: Respuesta
        AI-->>App: Respuesta con fuentes del catálogo
    end
    App-->>U: Mostrar respuesta
```

---

## 7. Diagrama de despliegue

```mermaid
flowchart LR
    subgraph PC["PC del usuario · Windows 10/11 de 64 bits"]
        APP["CorePulse<br/>(Python 3.12 + PySide6/QML)"]
        LOC[("%LOCALAPPDATA%\CorePulse<br/>SQLite · JSON · cuenta.dat")]
        NAV["Navegador web"]
        APP --- LOC
    end

    subgraph CF["Cloudflare"]
        WEB["Sitio web corepulse.cl<br/>(Next.js con OpenNext)"]
        WK["CorePulse AI<br/>ai.corepulse.cl (Worker)"]
        DO[("Durable Object<br/>presupuesto de uso")]
        WK --- DO
    end

    subgraph SB["Supabase"]
        PG[("PostgreSQL<br/>13 tablas con RLS")]
        AUTH["Auth (usuarios)"]
        ST["Storage (capturas)"]
    end

    GQ["Groq<br/>(modelo de IA)"]
    OOK["Ookla<br/>(prueba de velocidad)"]

    APP -- "HTTPS" --> WK
    APP -- "HTTPS" --> WEB
    APP -- "CLI oficial" --> OOK
    NAV -- "HTTPS" --> WEB
    WEB --> PG & AUTH & ST
    WK -- "verifica la cuenta" --> WEB
    WK -- "HTTPS" --> GQ
```
