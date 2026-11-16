# Retrospectivas de CorePulse

Registro de las retrospectivas de la Fase 2. Los sprints son semanales y cada uno agrupa varias versiones REBUILD. Al cierre de cada sprint, el equipo se reunió por Discord para revisar qué se hizo, qué salió bien, qué se podía mejorar y qué acuerdos tomar para el sprint siguiente.

Los períodos de cada sprint corresponden a las fechas de las versiones registradas en `versiones/HISTORIAL.md`.

| Sprint | Período | Versiones | Reunión de retrospectiva |
|---|---|---|---|
| 1 | 10 al 12 de octubre | REBUILD 001 a 059 | Por Discord |
| 2 | 13 y 14 de octubre | REBUILD 060 a 080 | Por Discord |
| 3 | 15 al 17 de octubre | REBUILD 081 a 117 | Por Discord |
| 4 | 18 al 23 de octubre | REBUILD 118 a 160 | Por Discord |
| 5 | 28 de octubre al 3 de noviembre | REBUILD 161 a 177 | Por Discord |
| 6 | 5 al 16 de noviembre | REBUILD 178 a 210 y entrega final | Por Discord |

---

## Sprint 1 · 10 al 12 de octubre · REBUILD 001 a 059

**Reunión de retrospectiva:** por Discord, al cierre del sprint.

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

**Reunión de retrospectiva:** por Discord, al cierre del sprint.

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

**Reunión de retrospectiva:** por Discord, al cierre del sprint.

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

**Reunión de retrospectiva:** por Discord, al cierre del sprint.

**Qué se hizo:** motor de conocimiento y RAG de CorePulse AI, rediseño visual Liquid Glass, panel rápido y OSD, instalación de PawnIO.

**Qué salió bien**

- La IA avanzó hacia respuestas basadas en evidencia y fuentes de un catálogo propio.
- La revisión del 20 de octubre dio una lista clara de lo que faltaba en el repositorio.

**Qué se puede mejorar**

- Se agregaron y rediseñaron funciones después de haber acordado congelar el alcance.
- La documentación técnica siguió pendiente.

**Acuerdos**

- Priorizar los elementos faltantes de la revisión.
- Pedir un cambio de alcance explícito antes de agregar funciones nuevas.

---

## Sprint 5 · 28 de octubre al 3 de noviembre · REBUILD 161 a 177

**Reunión de retrospectiva:** por Discord, al cierre del sprint.

**Qué se hizo:** overlay propio y captura de FPS sin RTSS, sesiones de juego, editor de OSD y registro de problemas, primer instalador y búsqueda global. La REBUILD 177 corrigió riesgos de seguridad.

**Qué salió bien**

- El instalador, una actividad que no se había iniciado, quedó compilado y probado localmente.
- Una revisión técnica detectó riesgos antes de distribuir la aplicación: inyección automática en juegos, administrador obligatorio e instalación de un driver sin consentimiento.

**Qué se puede mejorar**

- Esos riesgos debieron detectarse antes de llegar a una versión instalable.
- Siguen 57 pruebas fallidas de 349 en `test_rebuild.py`, y falta la matriz en tres equipos.
- El instalador no tiene firma digital.
- La versión del repositorio (146) quedó lejos de la versión actual (177).

**Acuerdos**

- Revisar seguridad y permisos antes de cada versión distribuible.
- Actualizar las pruebas y ejecutar la matriz antes de la entrega final.
- Mantener en el repositorio la versión vigente.

---

## Sprint 6 · 5 al 16 de noviembre · REBUILD 178 a 210 y entrega final

**Reunión de retrospectiva:** por Discord, al cierre del sprint.

**Qué se hizo**

- Centro de Salud y mantenimiento más claros, espacio de discos estable y registro automático de problemas (REBUILD 178 a 182).
- Rediseño de la prueba de velocidad (REBUILD 186 a 189).
- CorePulse AI limitado a temas técnicos del PC, con permisos de privacidad guardados (REBUILD 191 a 194).
- Versión liviana sin artefactos de compilación, con los tweaks restaurados y la sesión de captura de FPS corregida (REBUILD 198 y 199).
- Overlay en dos estilos, minimalista y avanzado, dibujado con Qt dentro de CorePulse y sin el ejecutable externo (REBUILD 200 y 201).
- Sensores más estables, sesiones de juego activas, scroll unificado y página de Overlay reorganizada (REBUILD 202 a 210).
- Instalador compartido con usuarios externos y corrección de los errores que reportaron en Windows en español.
- Informe final 2.6, README con tecnologías, integrantes, roles y metodología, y reorganización del repositorio con la estructura de evidencias y ejecución local con Docker.

**Qué salió bien**

- Probar el instalador con personas ajenas al equipo reveló errores reales que no aparecían en nuestros equipos, como los cierres por tildes en Windows en español y una falla del benchmark en un notebook, y se corrigieron rápido.
- Dibujar el overlay con Qt resolvió el bloqueo del Control inteligente de aplicaciones de Windows.
- La medición de FPS se verificó en un juego real (86,6 FPS en World of Warcraft).
- La versión liviana redujo el tamaño de cada entrega y facilitó compartirla.
- El repositorio quedó con la estructura de evidencias pedida y con instrucciones para ejecutar el sistema.

**Qué se puede mejorar**

- Se publicaron muchas versiones el mismo día (REBUILD 198 a 204 el 8 de noviembre), lo que dificultó revisar cada cambio.
- Siguieron entrando cambios visuales con el alcance congelado.
- Al cierre del sprint quedan 83 pruebas fallidas de 497, la mayoría por textos de pantallas rediseñadas.
- El instalador sigue sin firma digital, y Windows bloquea ejecutables nuevos sin firma.
- La ejecución con Docker no se probó en un equipo con Docker instalado.

**Acuerdos**

- Actualizar las pruebas fallidas para que verifiquen comportamiento y no textos.
- No agregar más cambios visuales hasta la presentación final.
- Probar `docker compose up` en un equipo con Docker antes de la entrega.
- Evaluar la firma digital del instalador o documentar cómo instalarlo de forma segura.
- Preparar la presentación del proyecto y subirla a la carpeta `Presentación Proyecto`.
