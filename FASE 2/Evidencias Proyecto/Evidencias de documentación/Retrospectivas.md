# Retrospectivas de CorePulse

> **Estado: borrador para que el equipo lo confirme.** Estos registros se reconstruyeron a partir del historial de versiones, el informe de avance y el diario de reflexión 2.1. No son actas de reuniones.
>
> Antes de entregarlo, el equipo debe revisar cada sprint, corregir lo que no coincida y completar los campos de reunión. Si una reunión no se hizo, conviene dejarlo indicado y no inventar una fecha.

Según el informe de avance, los sprints son semanales y cada uno agrupa varias versiones REBUILD. Aquí se agrupan por los períodos que registra el historial. Las fechas corresponden a las versiones, no a reuniones.

## Formato para confirmar cada sprint

- **Fecha de la reunión:** por completar
- **Asistentes:** por completar
- **Confirmado por el equipo:** sí / no

---

## Sprint 1 · 10 al 12 de octubre · REBUILD 001 a 059

**Qué se hizo:** base limpia en PySide6/QML, telemetría de CPU, GPU, RAM y almacenamiento, tweaks reversibles, limpieza y Centro de Salud.

**Qué salió bien**

- La base nueva resolvió el problema de mantenimiento del prototipo anterior.
- Las reglas comunes y el historial dejaron cada cambio documentado y reversible.
- Las funciones se migraron por módulos, sin arrastrar código obsoleto.

**Qué se puede mejorar**

- Reconstruir la interfaz desplazó tiempo que estaba destinado a validar.

**Acuerdos**

- Seguir migrando módulo por módulo, priorizando telemetría, salud y tweaks.

---

## Sprint 2 · 13 y 14 de octubre · REBUILD 060 a 080

**Qué se hizo:** inicio de sesión web, migración de funciones del prototipo, FPS con RTSS, telemetría de GPU NVIDIA, AMD e Intel y benchmark DirectX 11.

**Qué salió bien**

- El tercer integrante permitió avanzar en paralelo en interfaz, cuenta web y benchmark.
- Migrar desde el prototipo evitó partir desde cero.

**Qué se puede mejorar**

- El alcance creció con funciones no planificadas, como la cuenta web, los temas y el benchmark 3D.
- La fusión manual de versiones con archivos ZIP generó superposiciones.

**Acuerdos**

- Mantener un responsable único de integración.

---

## Sprint 3 · 15 al 17 de octubre · REBUILD 081 a 117

**Qué se hizo:** historial de benchmark, prueba de velocidad con Ookla, unidades removibles y desgaste NVMe, tendencias por sesión, PDF profesional e inicio de CorePulse AI Cloud.

**Qué salió bien**

- La suite detectó regresiones antes de cerrar versiones.
- Los aportes de distintos integrantes se integraron, como la versión 086 de Maximiliano.

**Qué se puede mejorar**

- En REBUILD 108 hubo 39 pruebas fallidas de 291, por depender de textos exactos de la interfaz.
- En una ocasión se descartó trabajo de un integrante por superponerse con otra rama.
- La documentación de la Fase 1 quedó desactualizada, y faltó validar en más equipos.

**Acuerdos**

- Reescribir las pruebas para que verifiquen comportamiento.
- Congelar el alcance desde la semana 14.
- Crear un repositorio Git con una rama por integrante.
- Hacer una reunión corta semanal y acordar quién trabaja en qué archivos.
- Ejecutar una matriz de pruebas en al menos tres equipos.

---

## Sprint 4 · 18 al 23 de octubre · REBUILD 118 a 160

**Qué se hizo:** motor de conocimiento y RAG de CorePulse AI, rediseño visual Liquid Glass, panel rápido y OSD, instalación de PawnIO.

**Qué salió bien**

- La IA avanzó hacia respuestas basadas en evidencia y fuentes de un catálogo propio.
- La revisión del 20 de octubre dio una lista clara de lo que faltaba en el repositorio.

**Qué se puede mejorar**

- Se agregaron y rediseñaron funciones después de haber acordado congelar el alcance. *(El equipo debe confirmar si hubo una excepción acordada.)*
- La documentación técnica siguió pendiente.

**Acuerdos propuestos** *(no registrados; el equipo debe confirmarlos)*

- Priorizar los elementos faltantes de la revisión.
- Pedir un cambio de alcance explícito antes de agregar funciones nuevas.

---

## Sprint 5 · 28 de octubre al 3 de noviembre · REBUILD 161 a 177

**Qué se hizo:** overlay propio y captura de FPS sin RTSS, sesiones de juego, editor de OSD y registro de problemas, primer instalador y búsqueda global. La REBUILD 177 corrigió riesgos de seguridad.

**Qué salió bien**

- El instalador, una actividad que no se había iniciado, quedó compilado y probado localmente.
- Una revisión técnica detectó riesgos antes de distribuir la aplicación: inyección automática en juegos, administrador obligatorio e instalación de un driver sin consentimiento.

**Qué se puede mejorar**

- Esos riesgos debieron detectarse antes de llegar a una versión instalable.
- Siguen 57 pruebas fallidas de 349 en `test_rebuild.py`, y falta la matriz en tres equipos.
- El instalador no tiene firma digital.
- La versión del repositorio (146) quedó lejos de la versión actual (177).

**Acuerdos propuestos** *(no registrados; el equipo debe confirmarlos)*

- Revisar seguridad y permisos antes de cada versión distribuible.
- Actualizar las pruebas y ejecutar la matriz antes de la entrega final.
- Mantener en el repositorio la versión vigente.
