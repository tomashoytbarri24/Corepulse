# Guía rápida de pruebas · CorePulse V406

1. Ejecuta `python main.py`.
2. Comprueba CPU, RAM, GPU y almacenamiento en Resumen.
3. Abre cada entrada del sidebar y verifica que todas comparten el mismo fondo maestro.
4. Comprueba que las tarjetas mantienen el diseño V400 y que el wallpaper no bloquea clics ni scroll.
5. Verifica CorePulse AI desde su tarjeta y pestaña.
6. Ejecuta diagnóstico, Centro de salud, Limpieza, Tweaks, Red, Alertas, Tendencias, Historial y Benchmark.
7. En Gaming verifica que los planes mostrados provienen de `powercfg /list` y que no se crean planes nuevos.

## Verificación visual específica V406

1. Abre Resumen y comprueba que la imagen atraviesa las franjas laterales del contenido sin rectángulos azules planos.
2. Maximiza, restaura y prueba 1366×768 y 1920×1080: el wallpaper debe tocar todos los bordes internos del cliente (sin barras de relleno).
3. Comprueba que el header superior deja ver el fondo y la tarjeta CorePulse AI conserva bordes, estado, clic y textos sin superponerse.
4. Navega por Benchmark, Diagnóstico, Gaming, Salud, IA y Temas y vuelve a Resumen: la misma geometría del fondo debe permanecer alineada.
5. Comprueba que las tarjetas originales siguen opacas y que sus tamaños/colores/funciones no cambiaron.

Nota: la verificación visual real debe efectuarse en Windows, no en el empaquetador Linux.
