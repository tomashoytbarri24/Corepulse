# Product Backlog de CorePulse

Lista priorizada del trabajo del producto, escrita como historias de usuario con sus criterios de aceptación. El Product Backlog se presentó en el informe de avance de la Fase 2 (Anexo D, 30 elementos) y aquí se actualiza al cierre de la Fase 2. La planificación de cada sprint está en `Sprints.md`, y un elemento solo se marca como "Terminado" si cumple la `Definition_of_Done.md`.

**Formato:** *Como \<rol\>, quiero \<acción\>, para \<beneficio\>.*

**Roles:** usuario (cualquier persona que usa CorePulse en su PC), jugador (usuario que juega en su PC), técnico (persona que da soporte a equipos), administrador del sitio (integrante que gestiona corepulse.cl) y equipo (integrantes del proyecto).

**Prioridades:** Alta (necesaria para el objetivo del proyecto), Media (aporta valor importante) y Baja (mejora deseable).

**Estados:** Terminado, En curso, En validación y Pendiente.

## Resumen al cierre de la Fase 2

| Estado | Historias |
|---|---|
| Terminado | 32 |
| En curso | 2 |
| Pendiente | 4 |
| **Total** | **38** |

## Épicas

| Épica | Historias |
|---|---|
| E1. Monitoreo y telemetría | PB01, PB02, PB06, PB07, PB12, PB26, PB30 |
| E2. Salud y diagnóstico | PB05, PB16, PB25, PB27 |
| E3. Optimización y mantenimiento | PB03, PB04, PB11, PB28 |
| E4. Gaming y rendimiento | PB10, PB13, PB24, PB31, PB32 |
| E5. Red | PB15, PB29, PB34, PB38 |
| E6. Inteligencia artificial | PB09, PB33 |
| E7. Cuenta y sitio web | PB08, PB14, PB20 |
| E8. Calidad, distribución y documentación | PB17, PB18, PB19, PB21, PB22, PB23, PB35, PB36, PB37 |

## Historias de usuario

| ID | Historia de usuario | Criterios de aceptación | Prioridad | Responsable | Estado |
|---|---|---|---|---|---|
| PB01 | Como usuario, quiero abrir una aplicación rápida y ordenada, para revisar mi PC sin perderme entre pantallas. | Abre sin errores en Windows 10/11 · navegación lateral entre todos los módulos · la interfaz no se congela al cargar datos | Alta | Tomás Hoyt | Terminado |
| PB02 | Como usuario, quiero ver el uso y la temperatura de CPU, GPU, RAM y discos con su fuente, para saber si los datos son confiables. | Cada lectura indica su fuente · si no hay fuente válida se muestra N/A · se actualiza en tiempo real | Alta | Tomás Hoyt | Terminado |
| PB03 | Como usuario, quiero aplicar optimizaciones de Windows que pueda deshacer, para mejorar el rendimiento sin riesgo. | Se guarda el valor original antes de aplicar · se verifica el cambio en el Registro · restaurar devuelve el valor original | Alta | Tomás Hoyt | Terminado |
| PB04 | Como usuario, quiero limpiar archivos temporales, caché, RAM, Papelera y DNS, para liberar espacio y memoria. | Muestra cuánto se puede liberar antes de limpiar · pide confirmación · informa el resultado real | Media | Tomás Hoyt | Terminado |
| PB05 | Como técnico, quiero revisar la batería, el almacenamiento y reparar Windows desde un solo lugar, para diagnosticar fallas sin otras herramientas. | Batería y discos con datos reales o N/A · reparación con DISM y SFC · recuperación del sistema | Alta | Tomás Hoyt | Terminado |
| PB06 | Como usuario, quiero que se guarde el historial de uso y alertas, para ver si un problema se repite. | Una muestra cada 30 segundos · retención de 90 días · alertas con valor, estado y fuente | Media | Tomás Hoyt | Terminado |
| PB07 | Como usuario, quiero un gráfico de rendimiento fluido, para ver los cambios de uso en tiempo real. | El gráfico se actualiza sin saltos · colores por componente · no afecta el rendimiento de la interfaz | Media | Agustín Valdés | Terminado |
| PB08 | Como usuario, quiero iniciar sesión con mi cuenta de corepulse.cl, para usar las funciones de mi plan. | La app nunca recibe la contraseña · el token se guarda cifrado · se puede cerrar sesión | Baja | Agustín Valdés | Terminado |
| PB09 | Como usuario, quiero preguntarle a una IA sobre mi equipo, para entender los datos sin conocimientos técnicos. | Compartir datos del equipo requiere permiso explícito · sin servicio, el diagnóstico local sigue funcionando · respuestas con fuentes | Alta | Tomás Hoyt | Terminado |
| PB10 | Como jugador, quiero ver los FPS reales sobre el juego, para saber cómo rinde mi equipo mientras juego. | FPS medidos de una fuente real o N/A · se muestra y oculta con una tecla · no requiere inyectar código en el juego por defecto | Alta | Agustín Valdés | Terminado |
| PB11 | Como usuario, quiero tener en la nueva versión las funciones del prototipo (Game Boost, inicio, drivers, velocidad, tendencias y PDF), para no perder lo que ya funcionaba. | Cada función migrada funciona en la nueva base · los cambios de energía son reversibles · sin código obsoleto | Alta | Tomás Hoyt | Terminado |
| PB12 | Como usuario con GPU AMD o Intel, quiero ver los datos de mi tarjeta, para tener la misma información que con NVIDIA. | Uso, VRAM y temperatura cuando el fabricante los expone · N/A si no están disponibles | Alta | Tomás Hoyt | Terminado |
| PB13 | Como jugador, quiero un benchmark de GPU con una escena 3D, para medir y comparar el rendimiento gráfico. | Escena DirectX 11 con FPS y frametime · resultados reproducibles · se guardan en el historial | Media | Agustín Valdés | Terminado |
| PB14 | Como usuario, quiero elegir un tema visual, para adaptar la apariencia a mi gusto. | Varios temas seleccionables · la elección se recuerda · los colores de marca de CPU y GPU se mantienen | Baja | Agustín Valdés | Terminado |
| PB15 | Como usuario, quiero que mi IP y mi red Wi-Fi estén ocultas por defecto, para proteger mi privacidad al compartir pantalla. | IP, IPv6 y SSID enmascarados · se revelan con el botón del ojo · se vuelven a ocultar a los 30 segundos | Media | Agustín Valdés | Terminado |
| PB16 | Como usuario, quiero un diagnóstico general con progreso real, para saber qué está revisando la aplicación. | El progreso refleja pasos reales · entrega un estado general con hallazgos | Alta | Agustín Valdés | Terminado |
| PB17 | Como equipo, queremos que las pruebas verifiquen comportamiento y no textos de pantallas, para que la suite detecte fallas reales. | Las 83 pruebas desactualizadas se reescriben · ninguna versión agrega fallos nuevos | Alta | Equipo | En curso |
| PB18 | Como equipo, queremos un repositorio Git común, para integrar el trabajo sin fusionar archivos ZIP a mano. | Repositorio en GitHub con estructura por fase · cada integrante sube sus cambios | Alta | Tomás Hoyt / Agustín Valdés | Terminado |
| PB19 | Como equipo, queremos probar CorePulse en al menos tres equipos distintos, para asegurar la compatibilidad. | Matriz con los resultados por equipo · fallas registradas y corregidas | Alta | Maximiliano Carrasco | Pendiente |
| PB20 | Como usuario, quiero que el inicio de sesión y el cifrado del token funcionen en mi Windows, para usar mi cuenta sin problemas. | Flujo completo probado en Windows real · el token sobrevive al reinicio de la app | Media | Agustín Valdés | Pendiente |
| PB21 | Como equipo, queremos la documentación del proyecto al día, para que el revisor encuentre cada evidencia. | Requisitos, backlog, sprints, retrospectivas, UML, modelo de datos y manual en el repositorio | Media | Maximiliano Carrasco | Terminado |
| PB22 | Como usuario, quiero instalar CorePulse con un instalador, para no tener que instalar Python. | Instalador de Windows funcional · probado en equipos de usuarios externos | Alta | Agustín Valdés | Terminado |
| PB23 | Como equipo, queremos el informe final, la presentación y la demo, para cerrar la Fase 2. | Informe 2.6 según la plantilla y la pauta · presentación subida al repositorio | Alta | Maximiliano Carrasco / Equipo | En curso |
| PB24 | Como jugador, quiero comparar resultados de benchmark y exportarlos, para ver si mi equipo mejoró. | Comparación entre dos sesiones del mismo método · exportación CSV | Media | Agustín Valdés | Terminado |
| PB25 | Como usuario, quiero ver mis unidades removibles y el desgaste de mi SSD NVMe, para anticipar fallas de almacenamiento. | Unidades detectadas al conectarlas · desgaste NVMe desde SMART o N/A | Media | Maximiliano Carrasco | Terminado |
| PB26 | Como usuario, quiero comparar el uso entre sesiones de Windows, para saber si un problema empezó en un arranque específico. | Muestras agrupadas por arranque · comparación entre dos sesiones | Media | Tomás Hoyt | Terminado |
| PB27 | Como técnico, quiero exportar un informe PDF del equipo, para respaldar mi diagnóstico ante el cliente. | PDF con lecturas, fuentes, diagnóstico y benchmark · se abre desde la app | Alta | Tomás Hoyt | Terminado |
| PB28 | Como usuario, quiero encontrar los drivers correctos de mi hardware, para mantener el equipo actualizado. | Búsqueda por Hardware ID · descarga por lote | Media | Tomás Hoyt | Terminado |
| PB29 | Como usuario, quiero medir mi velocidad de Internet con una herramienta oficial, para tener un resultado confiable. | Usa la CLI oficial de Ookla · muestra el enlace al resultado oficial | Baja | Agustín Valdés | Terminado |
| PB30 | Como usuario, quiero reconocer mi CPU y GPU por su marca, para ubicar rápido cada componente. | Logos y colores por fabricante en el Resumen y en el detalle | Baja | Agustín Valdés | Terminado |
| PB31 | Como jugador, quiero un benchmark reproducible de CPU, GPU, RAM y SSD, para comparar mi equipo de forma justa. | Pruebas de duración controlada, no de estrés · escenas 3D con FPS y frametime · veredicto del resultado | Alta | Agustín Valdés | Terminado |
| PB32 | Como jugador, quiero un overlay propio en estilo minimalista o avanzado, para elegir cuánta información ver sin depender de otros programas. | Dibujado con Qt dentro de CorePulse · dos estilos y panel rápido · no lo bloquea Windows | Alta | Agustín Valdés | Terminado |
| PB33 | Como usuario, quiero que la IA responda solo sobre mi PC y con fuentes oficiales, para confiar en sus recomendaciones. | Conocimiento curado de fabricantes · límites de 8 consultas por minuto y 20 diarias · no responde temas ajenos al PC | Alta | Tomás Hoyt | Terminado |
| PB34 | Como usuario, quiero que la prueba de velocidad use el adaptador de red correcto, para que el resultado corresponda a mi conexión real. | Selección y verificación del adaptador en Wi-Fi y Ethernet · 24 pruebas específicas aprobadas | Media | Maximiliano Carrasco | Terminado |
| PB35 | Como usuario de Windows en español, quiero que la aplicación no se cierre por tildes en nombres, para usarla con mi configuración regional. | La consola se lee con la página de códigos del sistema · probado con salidas reales en español | Alta | Agustín Valdés | Terminado |
| PB36 | Como revisor del proyecto, quiero poder levantar el sistema en local, para verificar que funciona. | Estructura de evidencias de sistema · modelo de datos con diagramas · docker-compose con instrucciones | Media | Agustín Valdés | Terminado |
| PB37 | Como usuario, quiero un instalador firmado digitalmente, para que Windows no lo bloquee. | Instalador firmado · se instala con el Control inteligente de aplicaciones activo | Media | Equipo | Pendiente |
| PB38 | Como usuario con Wi-Fi, quiero que la prueba de velocidad sea tan precisa como por cable, para confiar en el resultado. | Mediciones Wi-Fi validadas frente a Ethernet con distintos adaptadores | Media | Maximiliano Carrasco | Pendiente |

## Cambios respecto del informe de avance

- **Formato:** los elementos se reescribieron como historias de usuario con criterios de aceptación y se agruparon en épicas.
- **PB10:** pasó de "En validación" a "Terminado" al reemplazar RTSS por un overlay propio con medición de FPS por eventos de Windows.
- **PB18, PB21 y PB22:** terminados durante la Fase 2 (repositorio, documentación e instalador).
- **PB17 y PB23:** en curso al cierre de la fase.
- **PB31 a PB38:** historias agregadas a partir de los sprints de la Fase 2 y de sus retrospectivas.
