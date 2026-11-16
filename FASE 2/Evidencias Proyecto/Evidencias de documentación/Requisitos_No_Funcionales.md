# Requisitos no funcionales de CorePulse

Requisitos de calidad de CorePulse, ordenados según las características de calidad de la norma ISO/IEC 25010. Cada requisito indica cómo se verifica y su estado al cierre de la Fase 2.

**Estados:** Cumple, Cumple parcialmente y Pendiente.

## 1. Adecuación funcional (exactitud de los datos)

| ID | Requisito | Cómo se verifica | Estado |
|---|---|---|---|
| RNF01 | Toda lectura del equipo debe provenir de una fuente válida (sensor, Windows o herramienta oficial). Si no existe una fuente válida, se muestra N/A y nunca un valor estimado (regla REAL_OR_NA). | Pruebas automatizadas de casos N/A y revisión en equipos sin sensores disponibles | Cumple |
| RNF02 | Cada dato mostrado debe indicar su procedencia (sensor, Windows, NVIDIA-SMI u otra fuente). | Revisión de las pantallas de detalle de componentes | Cumple |
| RNF03 | Las mediciones del benchmark deben ser reproducibles: la misma prueba en el mismo equipo debe entregar resultados comparables. | Historial de benchmark y comparación entre sesiones | Cumple |

## 2. Eficiencia de desempeño

| ID | Requisito | Cómo se verifica | Estado |
|---|---|---|---|
| RNF04 | La interfaz no debe congelarse mientras se leen sensores o se ejecutan tareas pesadas (WMI, PowerShell, NVIDIA-SMI, limpieza, reparación); estas tareas corren en hilos o procesos aparte. | Uso de la aplicación durante diagnósticos y limpiezas | Cumple |
| RNF05 | El historial de monitoreo registra una muestra cada 30 segundos y conserva 90 días, para no crecer sin límite. | Esquema y limpieza de `monitoring_history.sqlite3` | Cumple |
| RNF06 | El overlay de juego debe tener un costo bajo de rendimiento y dibujarse dentro de CorePulse, sin inyectar código en el juego por defecto. | Prueba sobre juegos reales (86,6 FPS medidos en World of Warcraft) | Cumple |

## 3. Compatibilidad

| ID | Requisito | Cómo se verifica | Estado |
|---|---|---|---|
| RNF07 | La aplicación debe funcionar en Windows 10 y 11 de 64 bits. | Ejecución en los equipos del equipo y de usuarios externos | Cumple parcialmente (falta la matriz en tres equipos) |
| RNF08 | Debe leer GPU NVIDIA, AMD e Intel, y discos HDD, SSD SATA y NVMe. | Pruebas automatizadas y equipos reales | Cumple |
| RNF09 | Debe funcionar con Windows en español y con nombres con tildes; las respuestas de la consola se leen con la página de códigos del sistema. | Pruebas con salidas reales de Windows en español | Cumple |
| RNF10 | La prueba de velocidad debe seleccionar y verificar el adaptador de red correcto en conexiones Wi-Fi y Ethernet. | 24 pruebas específicas de Speedtest | Cumple parcialmente (falta validar Wi-Fi frente a Ethernet) |

## 4. Usabilidad

| ID | Requisito | Cómo se verifica | Estado |
|---|---|---|---|
| RNF11 | Toda la interfaz está en español, con textos claros para usuarios sin conocimientos técnicos. | Revisión de las pantallas | Cumple |
| RNF12 | Las acciones que modifican Windows o borran archivos piden confirmación antes de ejecutarse. | Revisión de los diálogos de confirmación | Cumple |
| RNF13 | La interfaz mantiene un estilo visual uniforme en todas las páginas, con temas seleccionables. | Revisión de las pantallas | Cumple |

## 5. Fiabilidad

| ID | Requisito | Cómo se verifica | Estado |
|---|---|---|---|
| RNF14 | Toda optimización de Windows guarda el valor original antes de aplicarse, verifica que Windows conservó el valor nuevo y permite restaurarlo. Si la verificación falla, el respaldo se conserva. | Pruebas del motor de tweaks y restauración en equipos reales | Cumple |
| RNF15 | Si la IA, Internet o un sensor opcional no están disponibles, la aplicación sigue funcionando con su diagnóstico local. | Pruebas sin conexión y sin servicio de IA | Cumple |
| RNF16 | La aplicación debe abrir sin permisos de administrador; las funciones que los necesitan lo informan. | Arranque como usuario estándar | Cumple |

## 6. Seguridad y privacidad

| ID | Requisito | Cómo se verifica | Estado |
|---|---|---|---|
| RNF17 | La aplicación nunca guarda la contraseña del usuario. El token de la cuenta se guarda cifrado con DPAPI de Windows. | Revisión de `cuenta.dat` y del flujo de inicio de sesión | Cumple |
| RNF18 | Los datos del equipo (lecturas, historial, respaldos) no salen del equipo. Compartir el hardware o el historial con la IA requiere un permiso explícito, apagado por defecto. | Revisión de los permisos de CorePulse AI | Cumple |
| RNF19 | En la base de datos web, cada usuario solo puede ver y modificar sus propios datos (seguridad por fila, RLS). Los códigos y tokens de la app se guardan como huellas SHA-256. | Migraciones SQL y políticas RLS | Cumple |
| RNF20 | Los tokens de la app caducan tras 30 días sin uso o 180 días desde que se conectó el equipo. | Migración de caducidad de tokens | Cumple |
| RNF21 | El servicio de IA limita el uso para controlar costos: 8 consultas por minuto por usuario y 20 consultas diarias por cuenta. | Pruebas del servicio en la nube | Cumple |
| RNF22 | El instalador debe estar firmado digitalmente para que Windows no lo bloquee. | Instalación en un equipo con Control inteligente de aplicaciones | Pendiente |

## 7. Mantenibilidad

| ID | Requisito | Cómo se verifica | Estado |
|---|---|---|---|
| RNF23 | Arquitectura en capas: la interfaz (QML) nunca habla directo con Windows; todo pasa por los controladores y los módulos de `core/`. | Revisión de la estructura del código | Cumple |
| RNF24 | Cada versión queda registrada en el historial con su base, cambios, validación y forma de reversión. | `versiones/HISTORIAL.md` | Cumple |
| RNF25 | La suite automatizada debe ejecutarse en cada versión y ninguna versión debe agregar fallos nuevos. | Ejecución de pytest (434 de 517 aprobadas al cierre de la fase) | Cumple parcialmente (83 pruebas por actualizar) |

## 8. Portabilidad e instalación

| ID | Requisito | Cómo se verifica | Estado |
|---|---|---|---|
| RNF26 | La aplicación prepara su propio entorno de Python e instala sus dependencias la primera vez que se ejecuta. | Ejecución en un equipo sin el entorno preparado | Cumple |
| RNF27 | Existe un instalador de Windows que no requiere instalar Python. | Instalación en equipos de usuarios externos | Cumple |
| RNF28 | El sitio web y la base de datos se pueden levantar en local con Docker. | `docker compose up` desde `Evidencias de sistema` | Cumple parcialmente (falta probar en un equipo con Docker) |
