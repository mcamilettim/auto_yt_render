"""Revisión estática del código de assets nuevos que escribe Claude (Python puro, sin Blender)."""
import ast

NOMBRES_PROHIBIDOS = {"eval", "exec", "open", "compile", "globals", "locals", "getattr", "setattr", "delattr", "vars",
                      "input", "breakpoint", "help", "memoryview", "type", "object", "super", "bpy"}
MAX_CARACTERES = 12000


class AssetInvalido(Exception):
    pass


def revisar_codigo(codigo: str) -> None:
    """Rechaza código que no cumpla el contrato. Lanza AssetInvalido con un mensaje en inglés (va al LLM)."""
    if not codigo or not codigo.strip():
        raise AssetInvalido("codigo is empty")
    if len(codigo) > MAX_CARACTERES:
        raise AssetInvalido(f"codigo has {len(codigo)} characters; max {MAX_CARACTERES}")
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as error:
        raise AssetInvalido(f"syntax error: {error}") from error
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.Import, ast.ImportFrom)):
            raise AssetInvalido("imports are not allowed; use the provided helpers and math")
        if isinstance(nodo, (ast.Global, ast.Nonlocal)):
            raise AssetInvalido("global/nonlocal are not allowed")
        if isinstance(nodo, ast.Attribute) and nodo.attr.startswith("_"):
            raise AssetInvalido(f"attribute '{nodo.attr}' is not allowed (no underscore attributes)")
        if isinstance(nodo, ast.Name) and (nodo.id in NOMBRES_PROHIBIDOS or nodo.id.startswith("__")):
            raise AssetInvalido(f"name '{nodo.id}' is not allowed")
    funciones = [n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "construir"]
    if not funciones:
        raise AssetInvalido("codigo must define a top-level function construir(...)")
