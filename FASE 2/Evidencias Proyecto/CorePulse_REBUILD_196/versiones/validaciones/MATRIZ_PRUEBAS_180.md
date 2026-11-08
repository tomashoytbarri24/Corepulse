# Matriz de pruebas - REBUILD 180

Fecha: 5 de noviembre de 2026. Base: 179.

| Área | Comprobación | Resultado |
|---|---|---|
| Discos | C → D → C; nombres largos; N/A; desgaste alto. | Áreas y tamaños estables a 760/1120/1450 px. |
| Captura automática | Pico real simulado, ventana anterior/posterior, instante original y persistencia. | Aprobada. |
| Duplicados | Picos cercanos en una captura y separación entre registros. | Aprobada. |
| Detecciones falsas | FPS bajos estables, escritorio, PID distinto, datos inválidos/antiguos/duplicados y discontinuidad. | No crean registros automáticos en los escenarios probados. |
| Preferencia | Activada por defecto, desactivar, reabrir y marcar manualmente. | Aprobada; ajustes de prueba aislados. |
| Interfaz | Selección de discos, interruptor y detalle de origen automático/manual. | 28 casos sin avisos QML. |
| PDF | Registro automático y manual por el exportador real, gráfico y textos. | Una página cada uno; renderizados y revisados. |
| Regresiones enfocadas | Capturas, overlay, sesiones, PDF, runtime, sensores e IA. | 123 aprobadas. |
| Aplicación completa | main.py y carga QML. | Abre sin avisos; versión 180 confirmada. |
| Nativos y RAM | Comparación con la 179. | Conservados; sin recompilar ni ejecutar limpieza real. |

La detección se prueba con intervalos sintéticos controlados. No demuestra la
sensibilidad en todas las partidas: una carga del juego también puede dar un
pico real. El automático exige intervalos ETW del juego; no los inventa si faltan.
No se repitió la suite histórica, ni se construyó un instalador.

## Probar en una partida

1. Cierra la versión anterior desde la bandeja y abre main.py de la 180.
2. Alterna C y D en Almacenamiento: comprueba que el espacio del modelo,
   las otras columnas y las tarjetas mantengan sus medidas.
3. En Sesiones de juego → Registros comprueba Detección automática activada.
4. Abre el juego y el overlay. La detección prepara unos segundos de fotogramas.
   Ante un pico suficientemente alto guarda automáticamente el contexto, sin
   tener que pulsar REGISTRAR. Espera unos 15 s después del pico.
5. Revisa el registro identificado como Automático y genera su PDF.
   REGISTRAR y el atajo siguen disponibles para marcar un problema manualmente.
