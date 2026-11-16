# Matriz de pruebas — REBUILD 182

Fecha: 5 de noviembre de 2026. Base: REBUILD 181.

| Área | Comprobación | Resultado |
|---|---|---|
| Encabezados QML | 14 iconos de cabeceras principales y secundarias sin envoltorios decorativos | PASS (prueba nueva de regresión) |
| Catálogo de glifos | Íconos declarados presentes en `Glyph.qml` sin duplicación de rutas | PASS (prueba histórica enfocada) |
| Sidebar | Íconos distintos para entradas clave, sin alterar la navegación | PASS (prueba histórica enfocada) |
| Benchmark | Velocímetro SVG con trayectoria curva y aguja conservada | PASS (prueba histórica enfocada) |
| Estructura | No se modificaron fuentes `core`, nativos, `Glyph.qml` ni archivos de nube | PASS (comparación de árbol original y entrega) |
| Control histórico obsoleto | Test antiguo `test_all_qml_components_exist`: exige 16 nombres exactos; la REBUILD 181 ya contiene 30 | FAIL preexistente; fuera del alcance, no atribuido a REBUILD 182 |
| Carga de Qt Quick | Validación de ejecución y captura de pantalla en Windows | Pendiente: PySide6 y escritorio Windows no disponibles en este entorno |
| Benchmark / limpieza / overlay en juego | Operaciones de hardware / integración real | No ejecutadas, módulos sin modificar |

La regresión de 182 verifica la presencia de glifos directos contiguos a sus
rótulos, sin propiedad `anchors.centerIn` de una placa decorativa. Se han
conservado los textos y las acciones de botones. La suite histórica completa
contiene contratos antiguos no compatibles con el árbol actual; no se declara
que esté completamente aprobada.

Para una revisión visual de aceptación en Windows: abrir Benchmark, CorePulse AI,
Limpieza, Sesiones de juego, Tendencias, Alertas técnicas, Historial de alertas,
Red avanzada, Overlay, Inicio de Windows, Tweaks, Temas, Resumen y Lecturas
disponibles. Cada cabecera mostrará un icono sin contenedor de color.
