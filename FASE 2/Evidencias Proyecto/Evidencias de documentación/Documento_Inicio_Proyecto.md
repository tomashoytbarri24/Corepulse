# Documento de inicio de proyecto: CorePulse

**Capstone PTY4614 · Ingeniería en Informática · Duoc UC, sede Valparaíso · Equipo 14**

Integrantes: Tomás Hoyt, Maximiliano Carrasco y Agustín Valdés.

Este documento reúne en un solo lugar lo definido en la Guía 1.5 y agrega los stakeholders, el alcance MVP y las restricciones, que la guía no detallaba. Debe revisarlo el equipo antes de entregarlo.

## 1. Problema

Para conocer el estado real de un PC o notebook con Windows normalmente hay que usar varias herramientas: una para temperaturas y uso de CPU o GPU, otra para SMART y almacenamiento, y otras para FPS o ajustes del sistema. Esa fragmentación dificulta comparar evidencias y obtener un diagnóstico claro. Además, muchas optimizaciones cambian Windows sin ofrecer una forma confiable de volver atrás.

## 2. Objetivos

**Objetivo general:** desarrollar y validar una aplicación modular para Windows que centralice diagnóstico, monitoreo, interpretación asistida por IA y optimización reversible de PC y notebooks mediante datos verificables, compatibilidad dinámica y trazabilidad técnica.

**Objetivos específicos** (versión ajustada del informe de avance):

1. Diseñar una arquitectura modular sobre PySide6/QML y un modelo de datos que separen telemetría, diagnóstico, persistencia, interfaz, IA y acciones sobre Windows.
2. Integrar y validar telemetría real de CPU, GPU, RAM, almacenamiento, batería y red, informando N/A cuando una lectura no esté disponible.
3. Implementar diagnóstico, salud, alertas, historial y benchmark a partir de evidencia técnica trazable.
4. Generar un informe PDF con identidad del equipo, evidencias, resultados, diagnóstico y recomendaciones técnicas.
5. Integrar una capa de IA que interprete únicamente evidencia validada y degrade de forma segura cuando el servicio no esté disponible.
6. Integrar Gaming, overlay y optimizaciones de Windows mediante detección de compatibilidad, snapshot, verificación y rollback persistente.
7. Validar CorePulse mediante pruebas funcionales, de regresión, compatibilidad y hardware real en al menos tres equipos distintos, registrando los resultados en una matriz de pruebas, y documentando errores, limitaciones y mejoras.

## 3. Stakeholders

| Stakeholder | Interés en el proyecto | Cómo participa |
|---|---|---|
| Usuarios de PC y notebooks con Windows | Entender el estado de su equipo sin combinar varias herramientas | Usan la aplicación y reportan problemas |
| Usuarios que juegan en PC | Medir rendimiento y ajustar el equipo sin riesgo para el sistema o sus cuentas | Usan overlay, sesiones de juego y benchmark |
| Equipo 14 | Construir un producto real, demostrar las competencias del perfil de egreso y aprobar el Capstone | Diseña, desarrolla, prueba y documenta |
| Docente de la asignatura | Evaluar el avance, las evidencias y el logro de las competencias | Revisa las entregas y entrega retroalimentación |
| Duoc UC, sede Valparaíso | Formación y titulación según el perfil de egreso | Define la pauta y las fases de evaluación |
| Proveedores externos (Groq, Cloudflare, Supabase, Ookla) | Uso correcto de sus servicios y licencias | Proveen servicios de los que depende parte de la solución |

## 4. Alcance MVP

**Incluido:**

- Identificación de hardware y telemetría real, con N/A cuando no exista una fuente válida.
- Diagnóstico, Centro de Salud, alertas e historial con tendencias.
- Benchmark e informe PDF.
- Asistente de IA que interpreta evidencia validada, con funcionamiento local si el servicio no está disponible.
- Overlay y datos de rendimiento en juegos, cuando exista una fuente válida.
- Optimizaciones de Windows con snapshot, verificación y restauración.
- Sitio web con cuentas de usuario, planes y publicación de versiones.

**Fuera del alcance:**

- Sistemas distintos de Windows 10/11 de 64 bits.
- Valores estimados presentados como lecturas reales.
- Garantizar la compatibilidad con todos los juegos, y en especial con los que usan antitrampas.
- Reemplazar un diagnóstico técnico presencial o reparar fallas físicas de hardware.

## 5. Restricciones

- **Plazo:** 18 semanas, con tres fases de evaluación.
- **Equipo:** tres integrantes.
- **Plataforma:** Windows 10/11 de 64 bits.
- **Regla de datos:** REAL_OR_NA. Si un dato no se puede obtener de una fuente válida, se informa N/A.
- **Reversibilidad:** toda acción sobre Windows debe guardar su estado previo y permitir restaurarlo.
- **Permisos:** algunas lecturas y acciones dependen de los permisos de administrador y del hardware disponible.
- **Dependencias externas:** IA, sensores opcionales y servicios web pueden no estar disponibles, y la aplicación debe seguir funcionando.
- **Recursos:** se usan herramientas gratuitas o de código abierto; los equipos de prueba son principalmente los de los integrantes.

## 6. Justificación

CorePulse centraliza en una sola aplicación información que hoy está repartida y agrega algo que suele faltar: trazabilidad de cada dato y cambios reversibles. El proyecto es pertinente al perfil de egreso porque aplica las cuatro competencias declaradas:

- **Desarrollo de software:** arquitectura e integración de la solución.
- **Pruebas de certificación:** validación de telemetría, compatibilidad y rollback.
- **Gestión de proyectos:** alcance, tareas, tiempos, riesgos y evidencias.
- **Modelos de datos:** historial, diagnósticos, configuraciones y snapshots.

Es factible porque se desarrolla por módulos a partir de un prototipo funcional, y el equipo cuenta con equipos Windows para pruebas y herramientas gratuitas.

**Fuentes:** Guía 1.5 e Informe de Avance Fase 2 del equipo.
