"""Establishments (sedes): patients belong to one sede; staff can be limited to one sede.

config.sedes = [{"id": "gye", "nombre": "Guayaquil", "principal": true, ...}, {"id": "balzar", ...}]
Patients without a sede belong to the main one. Users without a sede (and administrators) see every sede.
A user limited to a sede only receives, and can only change, the patients of that sede and their records
(appointments, clinical records, accounts). Enforced on the server for reads and writes.
"""

PATIENT_MAPS = ("notas", "recetas", "archivosClinicos", "signosVitales", "certificados", "ordenesLab")
PATIENT_LISTS = {"citas": "pac", "facturas": "pac", "cotizaciones": "pac"}


class SedeError(ValueError):
    pass


def sedes_of(config):
    items = (config or {}).get("sedes") if isinstance(config, dict) else None
    return [s for s in (items or []) if isinstance(s, dict) and s.get("id")]


def main_sede(config):
    items = sedes_of(config)
    main = next((s for s in items if s.get("principal")), items[0] if items else None)
    return str(main["id"]) if main else ""


def user_sede(user):
    """Sede a user is limited to ('' = all). Administrators are never limited."""
    if not user or user.get("rol") == "admin":
        return ""
    return str(user.get("sede") or "").strip()


def patient_sede(patient, default):
    return str((patient or {}).get("sede") or default or "")


def own_ids(patients, sede, default):
    return {str(p.get("id")) for p in patients or [] if isinstance(p, dict) and patient_sede(p, default) == sede}


def filter_data(data, user):
    sede = user_sede(user)
    if not sede:
        return data
    default = main_sede(data.get("config"))
    result = dict(data)
    patients = data.get("pacientes")
    if patients is None:
        return result
    ids = own_ids(patients, sede, default)
    result["pacientes"] = [p for p in patients if str(p.get("id")) in ids]
    for key in PATIENT_MAPS:
        if isinstance(data.get(key), dict):
            result[key] = {k: v for k, v in data[key].items() if str(k) in ids}
    for key, field in PATIENT_LISTS.items():
        if isinstance(data.get(key), list):
            result[key] = [x for x in data[key] if not isinstance(x, dict) or str(x.get(field)) in ids]
    return result


def keep_positions(visible, current, hidden_rule):
    """Put the hidden records back at their original positions among the ones the user saved."""
    result = list(visible)
    for index, item in enumerate(current or []):
        if isinstance(item, dict) and hidden_rule(item):
            result.insert(min(index, len(result)), item)
    return result


def merge_write(conn, user, key, value, current):
    """Recombine what a sede-limited user saved (their sede only) with the records of other sedes."""
    sede = user_sede(user)
    if not sede:
        return value
    from medicg_app import get_json_key
    default = main_sede(get_json_key(conn, "config", {}) or {})
    patients = get_json_key(conn, "pacientes", []) or []
    ids = own_ids(patients, sede, default)
    if key == "pacientes":
        known = {str(p.get("id")): p for p in patients if isinstance(p, dict)}
        out = []
        for p in value:
            pid = str(p.get("id"))
            if pid in known and pid not in ids:
                raise SedeError("No puedes modificar pacientes de otro establecimiento.")
            if pid not in known:
                p["sede"] = sede  # new patients are registered in the user's sede
            elif patient_sede(p, default) != sede:
                raise SedeError("No puedes mover pacientes a otro establecimiento.")
            out.append(p)
        return keep_positions(out, current, lambda p: str(p.get("id")) not in ids)
    if key in PATIENT_MAPS and isinstance(value, dict):
        if any(str(k) not in ids for k in value):
            raise SedeError("No puedes modificar historias de otro establecimiento.")
        return {**{k: v for k, v in (current or {}).items() if str(k) not in ids}, **value}
    if key in PATIENT_LISTS and isinstance(value, list):
        field = PATIENT_LISTS[key]
        if any(isinstance(x, dict) and str(x.get(field)) not in ids for x in value):
            raise SedeError("Solo puedes registrar datos de pacientes de tu establecimiento.")
        return keep_positions(value, current, lambda x: str(x.get(field)) not in ids)
    return value


def check_patient(conn, user, patient_id):
    sede = user_sede(user)
    if not sede:
        return
    from medicg_app import get_json_key
    default = main_sede(get_json_key(conn, "config", {}) or {})
    if str(patient_id) not in own_ids(get_json_key(conn, "pacientes", []) or [], sede, default):
        raise ValueError("Paciente de otro establecimiento.")


def valid_sede(conn, sede):
    if not sede:
        return ""
    from medicg_app import get_json_key
    if not any(str(s.get("id")) == str(sede) for s in sedes_of(get_json_key(conn, "config", {}) or {})):
        raise SedeError("Establecimiento no válido.")
    return str(sede)
