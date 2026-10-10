import argparse

import uvicorn

from portal.app import crear_app


def main() -> None:
    parser = argparse.ArgumentParser(description="SICOF, portal legacy de causación de facturas de proveedores")
    parser.add_argument("--ui", choices=["v1", "v2"], default="v1", help="versión de la interfaz")
    parser.add_argument("--inestable", action="store_true", help="responde 503 en una de cada tres confirmaciones")
    parser.add_argument("--puerto", type=int, default=8020)
    args = parser.parse_args()

    modo = "inestable" if args.inestable else "estable"
    print(f"SICOF | interfaz {args.ui} | modo {modo} | http://127.0.0.1:{args.puerto}", flush=True)
    print("Los datos viven en memoria: se pierden al detener el portal.", flush=True)
    uvicorn.run(crear_app(ui=args.ui, inestable=args.inestable), host="127.0.0.1", port=args.puerto, log_level="warning")


if __name__ == "__main__":
    main()
