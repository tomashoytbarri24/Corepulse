# Retrospectivas de CorePulse · Fase 2

Registro de las retrospectivas de los sprints de CorePulse desde la Fase 2. Al cierre de cada sprint, el equipo se reunió por Discord para revisar qué salió bien, qué salió mal y qué mejorar. Los sprints, sus fechas y sus tareas están en `Sprints.md`.

| Sprint | Fecha del hito | Versión | Tema | Reunión de retrospectiva |
|---|---|---|---|---|
| 1 | 16/09/2026 | V128 | Benchmark del sistema | Por Discord |
| 2 | 17 al 19/09/2026 | V135 a V175 | Optimización gráfica | Por Discord |
| 3 | 22/09/2026 | V257 | Consolidación del proyecto | Por Discord |
| 4 | 04/11/2026 | REBUILD 181 a 184 | Interfaz y overlay | Por Discord |
| 5 | 08/11/2026 | REBUILD 192 y 196 | IA, Tweaks y colaboración | Por Discord |
| 6 | 12/11/2026 | REBUILD 210 y 211 | Estabilización de Speedtest | Por Discord |
| 7 | 15/11/2026 | Sin versión nueva | Documentación e integración de Fase 3 | Por Discord |

---

## Sprint 1 · Benchmark del sistema

**16/09/2026 · V128** · Reunión de retrospectiva por Discord.

**Qué salió bien**

- Se implementaron pruebas reproducibles para CPU, GPU, RAM y SSD, evitando que el benchmark se comportara como una prueba de estrés prolongada.

**Qué salió mal / mejorar**

- Quedaba pendiente comprobar el funcionamiento de algunas mediciones directamente en equipos Windows reales, especialmente OpenGL y SSD.

---

## Sprint 2 · Optimización gráfica

**17 al 19/09/2026 · V135 a V175** · Reunión de retrospectiva por Discord.

**Qué salió bien**

- Se avanzó en el benchmark gráfico con escenas 3D, mediciones de FPS y frametime, y mejoras en el control de la duración de las pruebas.

**Qué salió mal / mejorar**

- Se detectaron problemas de velocidad de cámara y mediciones incompletas de VRAM.
- Se requería ampliar la cobertura y validar que cada resultado correspondiera a una medición real.

---

## Sprint 3 · Consolidación del proyecto

**22/09/2026 · V257** · Reunión de retrospectiva por Discord.

**Qué salió bien**

- Se consolidó la estructura de CorePulse, incluyendo documentación técnica, dependencias y archivos del sistema.
- Se estableció la V257 como versión a conservar.

**Qué salió mal / mejorar**

- Existían versiones duplicadas y dificultades al subir cambios a GitHub, incluyendo un error de conexión durante un `git push`.
- Era necesario organizar mejor las entregas y controlar el tamaño de los cambios.

---

## Sprint 4 · Interfaz y overlay

**04/11/2026 · REBUILD 181 a 184** · Reunión de retrospectiva por Discord.

**Qué salió bien**

- Se corrigieron elementos visuales del overlay, se ajustaron los iconos y se prepararon herramientas de validación para la aplicación Windows.

**Qué salió mal / mejorar**

- Aparecieron advertencias QML durante la ejecución con Python 3.15.
- Persistían fallos históricos de pruebas, y algunos binarios necesitaban recompilación y verificación en Windows.

---

## Sprint 5 · IA, Tweaks y colaboración

**08/11/2026 · REBUILD 192 y 196** · Reunión de retrospectiva por Discord.

**Qué salió bien**

- Se avanzó en la integración de IA mediante servicios en la nube, así como en las funcionalidades de Speedtest y Tweaks.
- La REBUILD 192 registró 64 pruebas aprobadas.

**Qué salió mal / mejorar**

- Se produjeron conflictos de Git al integrar cambios entre las versiones REBUILD 146, 177 y 196.
- Se debe mejorar la coordinación de ramas, la frecuencia de integración y la revisión antes de fusionar cambios.

---

## Sprint 6 · Estabilización de Speedtest

**12/11/2026 · REBUILD 210 y 211** · Reunión de retrospectiva por Discord.

**Qué salió bien**

- Se corrigió la selección y verificación del adaptador de red, mejorando el tratamiento de conexiones Wi-Fi y Ethernet.
- Se aprobaron 24 pruebas específicas.

**Qué salió mal / mejorar**

- Las mediciones por Wi-Fi presentaban inconsistencias frente a Ethernet.
- Se recomienda ampliar las pruebas con distintos adaptadores y condiciones reales de conexión.

---

## Sprint 7 · Documentación e integración de Fase 3

**15/11/2026 · Sin versión nueva** · Reunión de retrospectiva por Discord.

**Qué salió bien**

- Se identificaron las evidencias entregadas y pendientes, lo que permitió establecer prioridades para completar el proyecto.
- La Fase 2 tenía entregados los tres diarios individuales y el informe grupal de avance.

**Qué salió mal / mejorar**

- Faltaban cuatro de las cinco evidencias grupales de la Fase 2 y todas las evidencias revisadas de la Fase 3.
- También faltaban documentos Scrum, diagramas UML y elementos de documentación técnica.

---

## Acuerdos de mejora para los próximos sprints

1. Mantener una versión estable y verificada como referencia antes de incorporar cambios.
2. Realizar pruebas de regresión y pruebas en hardware real.
3. Evitar subir versiones completas y duplicadas cuando no sea necesario.
4. Coordinar los cambios de Git antes de integrar el trabajo de los integrantes.
5. Registrar por sprint su objetivo, tareas, responsables, resultados y retrospectiva.
6. Completar las evidencias académicas y la documentación técnica pendiente.
