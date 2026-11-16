# Definition of Done de CorePulse

La Definition of Done (definición de terminado) es el acuerdo del equipo sobre cuándo un trabajo se considera terminado. Un elemento que no cumple todos los criterios no se presenta como terminado en la revisión del sprint ni se marca como "Terminado" en el Product Backlog.

## 1. Elemento del Product Backlog

Un elemento está terminado cuando:

1. Cumple lo que describe el elemento y funciona en la aplicación, no solo en el código.
2. Respeta la regla **REAL_OR_NA**: si un dato no se puede obtener de una fuente válida, se muestra N/A y nunca un valor estimado.
3. Si modifica Windows (Registro, energía, servicios, inicio), guarda el estado original **antes** de aplicar el cambio, verifica que Windows conservó el valor y permite restaurarlo.
4. Funciona sin permisos de administrador, o informa con claridad qué permiso necesita y por qué.
5. No guarda contraseñas ni envía datos del equipo fuera de él sin un permiso explícito del usuario.
6. Tiene pruebas automatizadas que cubren su comportamiento principal.
7. Está probado en un equipo Windows real.

## 2. Versión (incremento REBUILD)

Una versión está terminada cuando:

1. Está registrada en `versiones/HISTORIAL.md` con su base, cambios, validación y forma de reversión.
2. La aplicación abre y se ejecuta sin errores.
3. No agrega fallos nuevos a la suite de pruebas automatizadas respecto de la versión anterior.
4. Existe un respaldo de la versión anterior para poder volver atrás.
5. No deja código obsoleto ni archivos de compilación (versión liviana).

## 3. Sprint

Un sprint está terminado cuando:

1. Se alcanzó el hito de desarrollo del sprint (una versión verificada) o se registró por qué no.
2. Se revisó el Sprint Backlog y cada tarea quedó como Terminado o Pendiente.
3. Se hizo la reunión de retrospectiva por Discord y quedó registrada en `Retrospectivas.md`, con lo que salió bien, lo que salió mal y los acuerdos de mejora.
4. Se actualizó el estado de los elementos del Product Backlog.

## 4. Entrega de fase

Una entrega de fase está terminada cuando:

1. Los cambios están subidos al repositorio en la carpeta de la fase, con la estructura de evidencias pedida.
2. El README explica cómo ejecutar el sistema y las instrucciones funcionan.
3. Los informes grupales e individuales están en sus carpetas, con el nombre que pide la asignatura.
4. La documentación (backlog, sprints, retrospectivas, requisitos, modelo de datos y diagramas) refleja el estado real del producto.
