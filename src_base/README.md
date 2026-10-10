# SICOF y datos del taller

## Arranque del portal

Requiere `uv` 0.8 o superior. Desde la carpeta `portal_sicof/`:

```bash
uv run python -m portal
```

El portal queda disponible en <http://127.0.0.1:8020>. Credenciales del operador: `operador.rpa` / `CxpSicof2026`.

Los datos viven en memoria: al detener el portal con `Ctrl+C` se pierden todas las causaciones.

## Opciones

| Opción | Efecto |
| :--- | :--- |
| `--ui v2` | Interfaz rediseñada: cambian los `id`, las clases y la estructura HTML; se conservan las etiquetas visibles. |
| `--inestable` | Una de cada tres confirmaciones responde `503 Servicio temporalmente no disponible`, sin registrar la causación. |
| `--puerto N` | Cambia el puerto (por defecto `8020`). |

## Datos

| Archivo | Uso |
| :--- | :--- |
| `datos/estructura_facturas.xlsx` | Crear la lista `<prefijo>-Facturas` con la opción **Desde Excel**. |
| `datos/facturas_prueba.xlsx` | Las siete facturas de los casos de prueba. |
| `datos/por_radicar.xlsx` | Plantilla de la cola de trabajo del robot, con la tabla `PorRadicar`. |
