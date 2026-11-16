# Matriz de pruebas - REBUILD 179

Fecha: 5 de noviembre de 2026. Base: 178.

| Área | Comprobación ejecutada | Resultado |
|---|---|---|
| Unidades | C y D visibles; clic en D cambia modelo, desgaste y volumen; regreso a C. | Aprobada con controladores sintéticos y clics QML. |
| USB | Sin SMART, cero de ocupación y sustitución del inventario. | Aprobada en escenario simulado; falta conexión física. |
| Interfaz | Batería, discos, limpieza, red, informes, detalles y anchura compacta. | 24 casos sin avisos QML. |
| Tamaño de discos | Seleccionar C, D y volver a C; nombres largos y datos ausentes a 1120 y 760 px. | Misma geometría antes y después; tarjetas del mismo ancho salvo redondeo de un píxel. |
| RAM | Código de limpieza y monitor conservados; cancelar confirmación. | Interfaz aprobada; no se ejecutó mantenimiento real. |
| Equipo y diagnóstico PDF | Próximos pasos, valores ausentes, cero real, nombres largos e independencia de benchmark. | Aprobados; tres casos, cuatro páginas revisadas. |
| Benchmark PDF | Resultados primero, métodos y códigos en anexo; cifras conservadas. | Aprobado; dos páginas revisadas. |
| Partida y registro PDF | Explicaciones de FPS, 1 % Low, frametime, mediana y P99; gráfico real del exportador. | Aprobados con datos sintéticos; dos páginas revisadas. |
| Panel GDI | Dos resoluciones y dos combinaciones de marcas, zonas de clic y hueco transparente. | Cuatro vistas renderizadas y comprobaciones nativas aprobadas. |
| Panel D3D11 | Dos resoluciones y dos combinaciones de marcas; RAM, registro, abrir, perfil y cerrar. | Cuatro vistas y 20 acciones de mouse aprobadas fuera de un juego. |
| OSD D3D11 | Distribución existente con la corrección tipográfica. | Revisado a 1920 y 2560 px. |
| Nativos | Host, auxiliares y cinco API x86/x64. | Compilación Zig 0.14.1 completada. |
| Regresiones enfocadas | PDF, runtime, sensores, activación, partidas, registros e IA. | 112 aprobadas en procesos separados por archivo. |
| Histórica | Mismos identificadores fallidos que en 178. | 290 aprobadas, 59 fallidas heredadas; suite no completamente aprobada. |
| Aplicación completa | main.py, carga QML y preparación de sensores. | Abre sin avisos. CPU N/A en la prueba sin administrador. |

Las cifras de los escenarios de diseño son simuladas y no evalúan el PC del
usuario. La compilación de una API no demuestra su funcionamiento en todos los
juegos. No se usaron juegos comerciales, conexión USB física ni una segunda
máquina en esta revisión. Tampoco se construyó ni se probó un instalador nuevo.

## Prueba al volver

1. Cierra CorePulse y los juegos; abre `main.py` de la 179.
2. En Almacenamiento pulsa C y D: las lecturas deben corresponder al disco elegido y las tarjetas y columnas deben mantener su tamaño y posición.
3. Genera de nuevo los PDF; los documentos viejos no cambian automáticamente.
4. Abre el juego y Shift+F2. Comprueba logos, borde único y acciones con mouse.
5. Haz una captura del segundo disco y otra del panel para comparar con la 178.
