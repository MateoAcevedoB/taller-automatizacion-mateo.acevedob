# Robot de causación de facturas (SICOF)

Lee `datos/por_radicar.xlsx` (tabla `PorRadicar`, descargada de OneDrive), causa cada factura en el portal SICOF con Playwright y escribe `salida/bot.log` y `salida/resultados.xlsx`.

## Uso

1. Arrancar el portal (otra terminal, desde `src_base/portal_sicof`): `uv run python -m portal` (admite `--ui v2` y `--inestable`).
2. Copiar `.env.example` a `.env` (el ejemplo ya apunta al portal por defecto).
3. Desde esta carpeta: `uv run python main.py`

Si Chromium no está instalado, el robot lo descarga solo en la primera ejecución (`playwright install chromium`).

## Reglas principales

- NIT: se limpia a dígitos (`900.123.456` -> `900123456`).
- Se rechaza antes de tocar SICOF: valor no entero o <= 0, fecha inválida o posterior a hoy.
- Mensajes `alert` de SICOF y centros de costo inexistentes: `RECHAZADA`, sin reintento.
- 503, tiempos de espera y errores de conexión: hasta 3 intentos; si se agotan, `FALLA_SISTEMA` y captura en `salida/evidencias/`.
- Idempotencia: antes de registrar consulta `/causaciones?factura=`; si ya existe el mismo NIT y factura, devuelve `YA_CAUSADA` con el número existente.
