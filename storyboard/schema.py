"""Catálogo v1 y validador del storyboard.

Las funciones de validación nunca lanzan excepciones ante entradas mal
formadas: devuelven una lista de errores en inglés pensados para que un LLM
pueda corregir el storyboard (cada error indica la ubicación y, cuando aplica,
las opciones válidas).
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

RUTA_CATALOGO = Path(__file__).resolve().parent.parent / "catalogo.json"

RE_NOMBRE_ASSET = re.compile(r"^[a-z][a-z0-9_]{2,40}$")
RE_REF_ELENCO = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
RE_ID_ESCENA = re.compile(r"^e[0-9]{2,3}$")
RE_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

TIPOS_ASSET = ("set", "prop")
CLAVES_ASSET = ("nombre", "tipo", "descripcion", "codigo")
CLAVES_PERSONA = ("edad", "complexion", "ropa", "pelo", "barba")
TOLERANCIA_AUDIO = 0.05


# ---------------------------------------------------------------- utilidades


def _es_numero(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _opciones(valores) -> str:
    return "(valid: " + ", ".join(str(v) for v in valores) + ")"


def _es_xy(x: Any, pos_max: float) -> bool:
    return (
        isinstance(x, list)
        and len(x) == 2
        and all(_es_numero(v) and abs(v) <= pos_max for v in x)
    )


def _errores_asset(asset: Any, loc: str) -> list[str]:
    """Errores de una entrada de assets_nuevos (lista vacía si es válida)."""
    if not isinstance(asset, dict):
        return [f"{loc}: must be an object with keys {', '.join(CLAVES_ASSET)}"]
    errores = []
    for clave in CLAVES_ASSET:
        if clave not in asset:
            errores.append(f"{loc}.{clave}: missing required key")
        elif not isinstance(asset[clave], str):
            errores.append(f"{loc}.{clave}: must be a string")
    nombre = asset.get("nombre")
    if isinstance(nombre, str) and not RE_NOMBRE_ASSET.match(nombre):
        errores.append(
            f"{loc}.nombre: '{nombre}' must match ^[a-z][a-z0-9_]{{2,40}}$"
        )
    tipo = asset.get("tipo")
    if isinstance(tipo, str) and tipo not in TIPOS_ASSET:
        errores.append(f"{loc}.tipo: '{tipo}' not valid {_opciones(TIPOS_ASSET)}")
    return errores


# ---------------------------------------------------------------- API pública


def cargar_catalogo(ruta: Path | None = None) -> dict:
    """Lee catalogo.json (por defecto el de la raíz del repo)."""
    ruta = Path(ruta) if ruta is not None else RUTA_CATALOGO
    return json.loads(ruta.read_text(encoding="utf-8"))


def extender_catalogo(catalogo: dict, assets_nuevos: list[dict]) -> dict:
    """Copia profunda del catálogo con los assets nuevos válidos agregados.

    Las entradas inválidas se ignoran aquí; validar_storyboard las reporta.
    """
    extendido = copy.deepcopy(catalogo)
    extendido.setdefault("sets", {})
    extendido.setdefault("props", {})
    if not isinstance(assets_nuevos, list):
        return extendido
    for asset in assets_nuevos:
        if _errores_asset(asset, "asset"):
            continue
        if asset["tipo"] == "set":
            extendido["sets"][asset["nombre"]] = asset["descripcion"]
        else:
            extendido["props"][asset["nombre"]] = {}
    return extendido


def validar_storyboard(
    d: dict, catalogo: dict, duracion_audio: float | None = None
) -> list[str]:
    """Valida un storyboard contra el catálogo. Lista vacía = válido."""
    try:
        return _Validador(d, catalogo, duracion_audio).validar()
    except Exception as exc:  # red de seguridad: nunca lanzar
        return [f"storyboard: unexpected validation failure ({type(exc).__name__}: {exc})"]


def ajustar_duraciones(d: dict, duraciones: list[float]) -> dict:
    """Copia con escenas[i].duracion reemplazada y tiempos de acción recortados."""
    escenas = d.get("escenas", [])
    if len(escenas) != len(duraciones):
        raise ValueError(
            f"duraciones has {len(duraciones)} items but storyboard has {len(escenas)} scenes"
        )
    nuevo = copy.deepcopy(d)
    for escena, dur in zip(nuevo["escenas"], duraciones):
        dur = round(float(dur), 3)
        escena["duracion"] = dur
        tope = round(max(0.0, dur - 0.2), 3)
        for actor in escena.get("actores", []):
            acciones = actor.get("acciones", [])
            for accion in acciones:
                if _es_numero(accion.get("t")) and accion["t"] >= dur:
                    accion["t"] = tope
            acciones.sort(key=lambda a: a.get("t", 0) if _es_numero(a.get("t")) else 0)
    return nuevo


# ---------------------------------------------------------------- validador


class _Validador:
    def __init__(self, d: Any, catalogo: dict, duracion_audio: float | None):
        self.d = d
        self.cat = catalogo
        self.duracion_audio = duracion_audio
        self.errores: list[str] = []
        lim = catalogo.get("limites", {})
        self.pos_max = lim.get("pos_max", 3.0)
        self.dur_min = lim.get("duracion_escena_min", 1.0)
        self.dur_max = lim.get("duracion_escena_max", 20.0)
        self.max_actores_por_formato = lim.get("actores_por_escena", {})

    def err(self, msg: str) -> None:
        self.errores.append(msg)

    def en_lista(self, valor: Any, validos, loc: str, campo: str) -> bool:
        if isinstance(valor, str) and valor in validos:
            return True
        if valor is None:
            self.err(f"{loc}: missing required key '{campo}' {_opciones(validos)}")
        else:
            self.err(f"{loc}: {campo} {valor!r} not in catalog {_opciones(validos)}")
        return False

    # -------------------------------------------------- nivel superior

    def validar(self) -> list[str]:
        d = self.d
        if not isinstance(d, dict):
            return [f"storyboard: must be a JSON object, got {type(d).__name__}"]

        assets = d.get("assets_nuevos")
        if "assets_nuevos" not in d:
            self.err("assets_nuevos: missing required key (use [] if none)")
            assets = []
        elif not isinstance(assets, list):
            self.err("assets_nuevos: must be a list")
            assets = []
        else:
            for i, asset in enumerate(assets):
                self.errores.extend(_errores_asset(asset, f"assets_nuevos[{i}]"))
        self.cat = extender_catalogo(self.cat, assets)

        if d.get("version") != 1:
            self.err(f"version: must be 1, got {d.get('version')!r}")
        tid = d.get("trabajo_id")
        if not isinstance(tid, str) or not tid.strip():
            self.err("trabajo_id: must be a non-empty string")

        formatos = self.cat.get("formatos", {})
        formato = d.get("formato")
        formato_ok = self.en_lista(formato, list(formatos), "formato", "formato")

        fps = d.get("fps")
        if fps not in self.cat.get("fps", []) or isinstance(fps, bool):
            self.err(f"fps: {fps!r} not allowed {_opciones(self.cat.get('fps', []))}")

        if formato_ok:
            esperado = formatos[formato]
            if d.get("resolucion") != esperado:
                self.err(
                    f"resolucion: {d.get('resolucion')!r} must be {esperado} for formato '{formato}'"
                )
        self.en_lista(d.get("calidad"), self.cat.get("calidades", []), "calidad", "calidad")
        if "estilo" in d:
            self.en_lista(d.get("estilo"), self.cat.get("estilos", []), "estilo", "estilo")

        self.elenco = self.validar_elenco(d.get("elenco"))

        if formato_ok:
            self.max_actores = self.max_actores_por_formato.get(formato, 1)
        else:
            self.max_actores = max(self.max_actores_por_formato.values(), default=1)

        escenas = d.get("escenas")
        if not isinstance(escenas, list) or not escenas:
            self.err("escenas: must be a non-empty list of scene objects")
            escenas = []
        ids_vistos: set[str] = set()
        total = 0.0
        duraciones_ok = True
        for i, escena in enumerate(escenas):
            dur = self.validar_escena(escena, f"escenas[{i}]", ids_vistos)
            if dur is None:
                duraciones_ok = False
            else:
                total += dur

        audio = self.duracion_audio
        if audio is not None and not _es_numero(audio):
            self.err(f"duracion_audio: must be a number, got {audio!r}")
        elif audio is not None and escenas and duraciones_ok:
            if abs(total - audio) > TOLERANCIA_AUDIO:
                self.err(
                    f"escenas: total scene duration {total:.3f} s does not match audio "
                    f"duration {audio:.3f} s (tolerance {TOLERANCIA_AUDIO} s)"
                )
        return self.errores

    # -------------------------------------------------- elenco

    def validar_elenco(self, elenco: Any) -> dict:
        """Valida el elenco y devuelve {ref: tipo} de las entradas utilizables."""
        tipos: dict[str, str] = {}
        if not isinstance(elenco, dict) or not elenco:
            self.err("elenco: must be a non-empty object mapping ref -> cast member")
            return tipos
        tipos_validos = self.cat.get("tipos_elenco", [])
        for ref, miembro in elenco.items():
            loc = f"elenco[{ref!r}]"
            if not isinstance(ref, str) or not RE_REF_ELENCO.match(ref):
                self.err(f"{loc}: ref must match ^[a-z][a-z0-9_]{{1,30}}$")
            if not isinstance(miembro, dict):
                self.err(f"{loc}: must be an object with 'tipo'")
                continue
            tipo = miembro.get("tipo")
            if not self.en_lista(tipo, tipos_validos, f"{loc}.tipo", "tipo"):
                continue
            tipos[ref] = tipo
            if tipo == "persona":
                self.validar_persona(miembro, loc)
            elif tipo == "prop":
                self.validar_prop_elenco(miembro, loc)
        return tipos

    def validar_persona(self, miembro: dict, loc: str) -> None:
        params = miembro.get("params")
        if not isinstance(params, dict):
            self.err(f"{loc}.params: persona requires a params object with {', '.join(CLAVES_PERSONA)}")
            return
        opciones = self.cat.get("persona_params", {})
        for clave in CLAVES_PERSONA:
            validos = opciones.get(clave, [])
            if clave not in params:
                self.err(f"{loc}.params.{clave}: missing required key {_opciones(validos)}")
            else:
                self.en_lista(params[clave], validos, f"{loc}.params.{clave}", clave)
        if "piel" in params and not (isinstance(params["piel"], str) and RE_HEX.match(params["piel"])):
            self.err(f"{loc}.params.piel: {params['piel']!r} must be a hex color like '#c68642'")

    def validar_prop_elenco(self, miembro: dict, loc: str) -> None:
        props = self.cat.get("props", {})
        nombre = miembro.get("nombre")
        if not self.en_lista(nombre, list(props), f"{loc}.nombre", "nombre"):
            return
        params = miembro.get("params", {})
        if not isinstance(params, dict):
            self.err(f"{loc}.params: must be an object")
            return
        spec = props.get(nombre) or {}
        for clave, tipo_param in spec.items():
            if clave in params and tipo_param == "hex":
                valor = params[clave]
                if not (isinstance(valor, str) and RE_HEX.match(valor)):
                    self.err(f"{loc}.params.{clave}: {valor!r} must be a hex color like '#f2c200'")

    # -------------------------------------------------- escenas

    def validar_escena(self, escena: Any, loc: str, ids_vistos: set[str]) -> float | None:
        """Valida una escena; devuelve su duración si es numérica."""
        if not isinstance(escena, dict):
            self.err(f"{loc}: must be a scene object")
            return None

        id_ = escena.get("id")
        if not isinstance(id_, str) or not RE_ID_ESCENA.match(id_):
            self.err(f"{loc}.id: {id_!r} must match ^e[0-9]{{2,3}}$ (e.g. 'e01')")
        elif id_ in ids_vistos:
            self.err(f"{loc}.id: duplicate scene id '{id_}'")
        else:
            ids_vistos.add(id_)

        dur = escena.get("duracion")
        dur_ok = _es_numero(dur)
        if not dur_ok:
            self.err(f"{loc}.duracion: must be a number of seconds, got {dur!r}")
        elif not (self.dur_min <= dur <= self.dur_max):
            self.err(f"{loc}.duracion: {dur} out of range [{self.dur_min}, {self.dur_max}]")

        self.en_lista(escena.get("set"), list(self.cat.get("sets", {})), f"{loc}.set", "set")
        self.en_lista(escena.get("luz"), self.cat.get("luces", []), f"{loc}.luz", "luz")

        # props primero: las acciones los referencian
        refs_props: list[str] = []
        props = escena.get("props", [])
        if not isinstance(props, list):
            self.err(f"{loc}.props: must be a list")
            props = []
        for j, prop in enumerate(props):
            ref = self.validar_prop_escena(prop, f"{loc}.props[{j}]")
            if ref is not None:
                refs_props.append(ref)

        actores = escena.get("actores")
        refs_actores: list[str] = []
        if not isinstance(actores, list) or not actores:
            self.err(f"{loc}.actores: must be a non-empty list")
            actores = []
        elif len(actores) > self.max_actores:
            self.err(f"{loc}.actores: {len(actores)} actors exceed the limit of {self.max_actores} for this formato")
        for j, actor in enumerate(actores):
            if isinstance(actor, dict) and isinstance(actor.get("ref"), str):
                ref = actor["ref"]
                if ref in refs_actores:
                    self.err(f"{loc}.actores[{j}].ref: duplicate actor '{ref}' in scene")
                elif self.elenco.get(ref) == "persona":
                    refs_actores.append(ref)

        presentes = set(refs_actores) | set(refs_props)
        for j, actor in enumerate(actores):
            self.validar_actor(actor, f"{loc}.actores[{j}]", dur if dur_ok else None,
                               refs_actores, refs_props, presentes)

        self.validar_camara(escena.get("camara"), f"{loc}.camara", refs_actores)

        texto = escena.get("texto_narracion")
        if not isinstance(texto, str) or not texto.strip():
            self.err(f"{loc}.texto_narracion: must be a non-empty string")

        return dur if dur_ok else None

    def validar_camara(self, camara: Any, loc: str, refs_actores: list[str]) -> None:
        if not isinstance(camara, dict):
            self.err(f"{loc}: must be an object with movimiento, desde, hasta, objetivo")
            return
        self.en_lista(camara.get("movimiento"), self.cat.get("camara", []), f"{loc}.movimiento", "movimiento")
        planos = self.cat.get("planos", [])
        self.en_lista(camara.get("desde"), planos, f"{loc}.desde", "desde")
        self.en_lista(camara.get("hasta"), planos, f"{loc}.hasta", "hasta")
        objetivo = camara.get("objetivo")
        if objetivo not in refs_actores:
            self.err(f"{loc}.objetivo: {objetivo!r} must be an actor in this scene {_opciones(refs_actores)}")

    def validar_prop_escena(self, prop: Any, loc: str) -> str | None:
        if not isinstance(prop, dict):
            self.err(f"{loc}: must be an object with ref, pos, sobre")
            return None
        ref = prop.get("ref")
        ref_ok = isinstance(ref, str) and self.elenco.get(ref) == "prop"
        if not ref_ok:
            validos = [r for r, t in self.elenco.items() if t == "prop"]
            self.err(f"{loc}.ref: {ref!r} must be a prop in elenco {_opciones(validos)}")
        if not _es_xy(prop.get("pos"), self.pos_max):
            self.err(f"{loc}.pos: must be [x, y] numbers with abs <= {self.pos_max}, got {prop.get('pos')!r}")
        self.en_lista(prop.get("sobre"), self.cat.get("soportes", []), f"{loc}.sobre", "sobre")
        return ref if ref_ok else None

    def validar_actor(self, actor: Any, loc: str, dur: float | None,
                      refs_actores: list[str], refs_props: list[str], presentes: set[str]) -> None:
        if not isinstance(actor, dict):
            self.err(f"{loc}: must be an object with ref, pos, acciones")
            return
        ref = actor.get("ref")
        if not (isinstance(ref, str) and self.elenco.get(ref) == "persona"):
            validos = [r for r, t in self.elenco.items() if t == "persona"]
            self.err(f"{loc}.ref: {ref!r} must be a persona in elenco {_opciones(validos)}")
        if not _es_xy(actor.get("pos"), self.pos_max):
            self.err(f"{loc}.pos: must be [x, y] numbers with abs <= {self.pos_max}, got {actor.get('pos')!r}")
        if "mira_a" in actor:
            mira = actor["mira_a"]
            if mira != "camara" and mira not in presentes:
                self.err(f"{loc}.mira_a: {mira!r} must be 'camara' or a ref in this scene "
                         f"{_opciones(['camara', *sorted(presentes)])}")

        acciones = actor.get("acciones")
        if not isinstance(acciones, list) or not acciones:
            self.err(f"{loc}.acciones: must be a non-empty list")
            return
        t_previo = None
        for k, item in enumerate(acciones):
            t = self.validar_accion(item, f"{loc}.acciones[{k}]", dur, refs_props, presentes)
            if t is not None:
                if t_previo is not None and t < t_previo:
                    self.err(f"{loc}.acciones[{k}]: t={t} is before previous t={t_previo}; sort acciones by t ascending")
                t_previo = t

    def validar_accion(self, item: Any, loc: str, dur: float | None,
                       refs_props: list[str], presentes: set[str]) -> float | None:
        if not isinstance(item, dict):
            self.err(f"{loc}: must be an object with t and accion and/or expresion")
            return None
        t = item.get("t")
        t_ok = _es_numero(t)
        if not t_ok:
            self.err(f"{loc}.t: must be a number of seconds, got {t!r}")
        elif t < 0 or (dur is not None and t >= dur):
            self.err(f"{loc}.t: {t} must satisfy 0 <= t < duracion ({dur})")

        acciones_cat = self.cat.get("acciones", {})
        expresiones = self.cat.get("expresiones", [])
        if "accion" not in item and "expresion" not in item:
            self.err(f"{loc}: needs 'accion' {_opciones(acciones_cat)} and/or 'expresion' {_opciones(expresiones)}")

        if "expresion" in item and item["expresion"] not in expresiones:
            self.err(f"{loc}: expresion {item['expresion']!r} not in catalog {_opciones(expresiones)}")

        if "accion" in item:
            accion = item["accion"]
            if not isinstance(accion, str) or accion not in acciones_cat:
                self.err(f"{loc}: accion {accion!r} not in catalog {_opciones(acciones_cat)}")
            else:
                for param, tipo in (acciones_cat[accion] or {}).items():
                    self.validar_param(item.get(param), tipo, f"{loc}.{param}", accion,
                                       refs_props, presentes)
        return t if t_ok else None

    def validar_param(self, valor: Any, tipo: str, loc: str, accion: str,
                      refs_props: list[str], presentes: set[str]) -> None:
        if tipo == "xy":
            if not _es_xy(valor, self.pos_max):
                self.err(f"{loc}: accion '{accion}' requires [x, y] numbers with abs <= {self.pos_max}, got {valor!r}")
        elif tipo == "prop":
            if valor not in refs_props:
                self.err(f"{loc}: accion '{accion}' requires a prop ref present in this scene's props "
                         f"{_opciones(refs_props)}, got {valor!r}")
        elif tipo == "ref":
            if valor not in presentes:
                self.err(f"{loc}: accion '{accion}' requires an actor or prop ref present in this scene "
                         f"{_opciones(sorted(presentes))}, got {valor!r}")
