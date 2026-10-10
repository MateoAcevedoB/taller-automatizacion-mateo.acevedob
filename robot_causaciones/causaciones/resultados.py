from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.table import Table, TableStyleInfo

from causaciones.modelos import Resultado

ENCABEZADOS = ["IdLista", "Factura", "NIT", "Estado", "Causacion", "Detalle"]


def escribir_resultados(ruta: Path, resultados: list[Resultado]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Resultados"
    hoja.append(ENCABEZADOS)
    for r in resultados:
        hoja.append([r.id_lista, r.factura, r.nit, r.estado, r.causacion, r.detalle])
    # Una tabla de Excel necesita al menos una fila de datos en su rango.
    ultima = max(len(resultados) + 1, 2)
    tabla = Table(displayName="Resultados", ref=f"A1:F{ultima}")
    tabla.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    hoja.add_table(tabla)
    for columna, ancho in zip("ABCDEF", (10, 14, 14, 16, 18, 70)):
        hoja.column_dimensions[columna].width = ancho
    libro.save(ruta)
