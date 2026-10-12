# CorePulse V476 — Investigation Engine

## Usar
1. Cierra CorePulse y el puente Groq anterior. Extrae el ZIP en una carpeta nueva.
2. Ejecuta `Iniciar_CorePulse.bat`, abre CorePulse AI y autoriza la nube sólo si lo deseas.
3. Pulsa **Conectar IA** y pregunta: `Analiza mi equipo`.
4. Espera al menos 15 segundos y vuelve a preguntar: `Compara mis lecturas actuales con las anteriores`.
5. Verás una comparación de los valores que ambos mensajes tenían disponibles. Si falta un sensor, se informa **N/A**.

**Importante:** estas dos lecturas no constituyen una tendencia sostenida y no permiten certificar averías.
Sólo se almacenan hasta cinco muestras mínimas en la memoria de esta ventana. No se guardan en disco.
El historial se borra al limpiar la conversación, cambiar de servidor o revocar consentimiento.
La conexión cloud transmite, con consentimiento, las muestras mínimas previas del chat y la telemetría actual.
El motor no realiza cambios en Windows, no estima FPS y no crea alertas térmicas por umbrales inventados.

## Validar sin nube
Ejecuta `24_VALIDAR_INVESTIGACION_V476.bat` para casos sintéticos sin datos del equipo.

## Limitaciones
- No usa aún el historial de sesiones persistente de CorePulse ni registros de eventos Windows; no presume haberlos leído.
- La evidencia histórica declarada por cliente no ha sido comprobada independientemente por el servidor.
- Para una investigación real con casos complejos se necesitan capturas adicionales y registros técnicos, con consentimiento.
- Probar en Windows el chat y la interfaz es parte pendiente de la validación.
