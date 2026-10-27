"""Record-level three-way merge for the collections stored in app_data.

Before this module, saving a collection required the client's whole copy to
match the server exactly. Two receptionists editing *different* patients at
the same time got a conflict, and every save sent the full collection twice
(``value`` + ``baseValue``).

Now a save is turned into a small change set (records added, modified or
removed by the client). Each touched record is checked against the server's
current version: a conflict happens only when another user changed **the same
record**. Untouched records keep the server's latest version.

Clients may send either the classic ``value`` + ``baseValue`` pair or the
compact ``delta`` produced by assets/js/app.js.
"""
import json

LIST_KEYS = {
    "cajas", "facturas", "pacientes", "medicos", "especialidades", "seguros",
    "quirofanos", "equipos", "stockQx", "servicios", "examenes", "cotizaciones", "cie10",
}
MAP_KEYS = {"config", "notas", "recetas", "archivosClinicos"}


class MergeConflict(ValueError):
    def __init__(self, message, items=None):
        super().__init__(message)
        self.items = list(items or [])


def _canon(value, normalize=None):
    if normalize:
        value = normalize(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _id_key(item):
    if not isinstance(item, dict):
        return None
    raw = item.get("id")
    if raw is None or raw == "" or isinstance(raw, (dict, list, bool)):
        return None
    return str(raw)


def _index(items):
    """Map id -> item, or None when ids are missing or duplicated."""
    if not isinstance(items, list):
        return None
    result = {}
    for item in items:
        key = _id_key(item)
        if key is None or key in result:
            return None
        result[key] = item
    return result


def diff(base, value, normalize=None):
    """Return a change set describing how ``value`` differs from ``base``.

    ``None`` means the data cannot be merged by record (missing ids, wrong
    types) and the caller must fall back to a strict whole-value comparison.
    """
    if isinstance(value, list):
        base_index = _index(base if base is not None else [])
        value_index = _index(value)
        if base_index is None or value_index is None:
            return None
        upsert = [item for key, item in value_index.items()
                  if key not in base_index or _canon(item, normalize) != _canon(base_index[key], normalize)]
        remove = [key for key in base_index if key not in value_index]
        touched = [_id_key(item) for item in upsert] + remove
        return {
            "type": "list",
            "upsert": upsert,
            "remove": remove,
            "base": {key: base_index.get(key) for key in touched},
            "order": [_id_key(item) for item in value],
        }
    if isinstance(value, dict):
        base = base if isinstance(base, dict) else {}
        changed = {k: v for k, v in value.items() if k not in base or _canon(v, normalize) != _canon(base[k], normalize)}
        remove = [k for k in base if k not in value]
        return {
            "type": "map",
            "set": changed,
            "remove": remove,
            "base": {k: base.get(k) for k in [*changed, *remove]},
        }
    return None


def validate_delta(delta):
    if not isinstance(delta, dict) or delta.get("type") not in ("list", "map"):
        raise ValueError("Cambios con formato inválido.")
    if not isinstance(delta.get("base", {}), dict):
        raise ValueError("Cambios con formato inválido.")
    if delta["type"] == "list":
        if not isinstance(delta.get("upsert", []), list) or not isinstance(delta.get("remove", []), list):
            raise ValueError("Cambios con formato inválido.")
        if any(_id_key(item) is None for item in delta.get("upsert", [])):
            raise ValueError("Cada registro necesita un identificador.")
        if not isinstance(delta.get("order", []), list):
            raise ValueError("Cambios con formato inválido.")
    else:
        if not isinstance(delta.get("set", {}), dict) or not isinstance(delta.get("remove", []), list):
            raise ValueError("Cambios con formato inválido.")
    return delta


def apply(current, delta, normalize=None):
    """Apply a change set on top of the server's current (visible) value."""
    delta = validate_delta(delta)
    base = delta.get("base") or {}
    conflicts = []
    if delta["type"] == "list":
        current = current if isinstance(current, list) else []
        current_index = _index(current)
        if current_index is None:
            raise MergeConflict("Los datos guardados no tienen identificadores únicos. Actualiza la página.")
        upserts = {_id_key(item): item for item in delta.get("upsert", [])}
        removes = {str(k) for k in delta.get("remove", [])}
        for key in [*upserts, *removes]:
            expected = base.get(key)
            server = current_index.get(key)
            if expected is None:
                if server is not None and (key not in upserts or _canon(server, normalize) != _canon(upserts[key], normalize)):
                    conflicts.append(key)
            elif server is None:
                if key in upserts:
                    conflicts.append(key)
            elif _canon(server, normalize) != _canon(expected, normalize):
                conflicts.append(key)
        if conflicts:
            raise MergeConflict("Otro usuario modificó los mismos registros. Actualiza la página antes de guardar.", conflicts)
        result = []
        for item in current:
            key = _id_key(item)
            if key in removes:
                continue
            result.append(upserts.pop(key) if key in upserts else item)
        if isinstance(delta.get("positions"), dict):
            position = {}
            for key, idx in delta["positions"].items():
                try:
                    position[str(key)] = max(0, int(idx))
                except (TypeError, ValueError):
                    continue
        else:
            position = {str(key): idx for idx, key in enumerate(delta.get("order", []))}
        for key, item in upserts.items():
            idx = min(position.get(key, len(result)), len(result))
            result.insert(idx, item)
        return result
    current = current if isinstance(current, dict) else {}
    result = dict(current)
    changes = delta.get("set") or {}
    removes = [str(k) for k in delta.get("remove", [])]
    for key in [*changes, *removes]:
        expected = base.get(key)
        server = current.get(key)
        if expected is None and server is None:
            continue
        if expected is None and key in changes and _canon(server, normalize) == _canon(changes[key], normalize):
            continue
        if _canon(server, normalize) != _canon(expected, normalize):
            conflicts.append(key)
    if conflicts:
        raise MergeConflict("Otro usuario modificó los mismos datos. Actualiza la página antes de guardar.", conflicts)
    result.update(changes)
    for key in removes:
        result.pop(key, None)
    return result


def merge_save(key, visible, payload, normalize=None):
    """Return the merged value for a /api/data save, or raise MergeConflict.

    ``visible`` is the server value as this user is allowed to see it.
    """
    if key == "nextIds":
        incoming = payload.get("value") if "value" in payload else None
        if incoming is None and isinstance(payload.get("delta"), dict):
            incoming = {**(visible or {}), **(payload["delta"].get("set") or {})}
        if not isinstance(incoming, dict):
            raise ValueError("Formato de datos inválido.")
        merged = dict(visible or {})
        for name, number in incoming.items():
            try:
                merged[name] = max(int(merged.get(name) or 0), int(number or 0))
            except (TypeError, ValueError):
                raise ValueError("Contadores inválidos.")
        return merged
    if "delta" in payload:
        return apply(visible, payload["delta"], normalize)
    if "baseValue" not in payload:
        raise MergeConflict("Actualiza la página antes de guardar; falta la versión original.")
    value, base = payload.get("value"), payload.get("baseValue")
    change_set = diff(base, value, normalize) if (key in LIST_KEYS or key in MAP_KEYS) else None
    if change_set is None:
        if _canon(visible, normalize) != _canon(base, normalize):
            raise MergeConflict("Otro usuario cambió estos datos. Actualiza la página antes de guardar.")
        return value
    return apply(visible, change_set, normalize)
