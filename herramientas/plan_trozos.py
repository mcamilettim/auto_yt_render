"""Reparte un storyboard en tramos de cuadros para renderizar en paralelo.

Los cuadros de cada escena salen de los límites acumulados redondeados, así la suma de cuadros coincide con la
duración total del audio (no se acumula desfase escena a escena).

    python herramientas/plan_trozos.py storyboard.json [tamano_trozo]  -> imprime JSON {"include": [...]} para la matriz
"""
import json
import sys

TROZO = 72


def cuadros_por_escena(storyboard: dict) -> list[tuple[str, int]]:
    fps = storyboard["fps"]
    acumulado = 0.0
    salida = []
    for escena in storyboard["escenas"]:
        inicio = round(acumulado * fps)
        acumulado += escena["duracion"]
        fin = round(acumulado * fps)
        salida.append((escena["id"], max(1, fin - inicio)))
    return salida


def trozos(storyboard: dict, tamano: int = TROZO) -> list[dict]:
    lista = []
    for id_escena, total in cuadros_por_escena(storyboard):
        n = -(-total // tamano)
        paso = -(-total // n)                 # tramos parejos dentro de la escena
        for k in range(n):
            desde = k * paso + 1
            hasta = min(total, (k + 1) * paso)
            if desde <= hasta:
                lista.append({"escena": id_escena, "desde": desde, "hasta": hasta, "total": total,
                              "nombre": f"{id_escena}_{desde:05d}"})
    return lista


if __name__ == "__main__":
    sb = json.load(open(sys.argv[1], encoding="utf-8"))
    tamano = int(sys.argv[2]) if len(sys.argv) > 2 else TROZO
    print(json.dumps({"include": trozos(sb, tamano)}))
