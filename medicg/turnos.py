"""Turn (queue) system: reception gives numbered turns per area, staff call them to a room/window,
a waiting-room screen shows and announces the call.

Turns live in their own table (one row per turn) and are numbered per day, sede and area.
config.turnos = {"areas": [{"letra": "C", "nombre": "Consulta médica"}, ...], "mostrarNombre": false, "displayKey": "..."}
"""
import datetime as dt
import secrets
import time
import uuid

TZ = dt.timezone(dt.timedelta(hours=-5))
DEFAULT_AREAS = [
    {"letra": "C", "nombre": "Consulta médica"},
    {"letra": "L", "nombre": "Laboratorio"},
    {"letra": "K", "nombre": "Caja"},
]
STATES = ("espera", "llamado", "atendido", "ausente", "cancelado")


class TurnoError(ValueError):
    pass


def table_sql():
    return ("create table if not exists turnos(id text primary key, fecha text not null, sede text not null, area text not null, "
            "numero integer not null, codigo text not null, prioridad integer not null, paciente_id text, nombre text, alias text, "
            "estado text not null, destino text, llamadas integer not null, llamado_en double precision, llamado_por text, "
            "creado_en text not null, creado_por text, cerrado_en text)")


def index_sql():
    return "create index if not exists turnos_dia_idx on turnos(fecha, sede, area, numero)"


def today():
    return dt.datetime.now(TZ).date().isoformat()


def stamp():
    # Microseconds keep the arrival order exact across areas (turns given in the same second).
    return dt.datetime.now(TZ).isoformat(timespec="microseconds")


def settings(config):
    raw = (config or {}).get("turnos") if isinstance((config or {}).get("turnos"), dict) else {}
    areas = [a for a in (raw.get("areas") or []) if isinstance(a, dict) and str(a.get("letra") or "").strip()]
    return {"areas": areas or DEFAULT_AREAS, "mostrarNombre": bool(raw.get("mostrarNombre")),
            "displayKey": str(raw.get("displayKey") or ""), "voz": raw.get("voz", True) is not False}


def can_use(user):
    from medicg_app import clean_permissions
    if not user:
        return False
    if user.get("rol") == "admin":
        return True
    perms = set(clean_permissions(user.get("permissions"), user.get("rol", "recepcion")))
    return bool({"agenda", "caja", "hce"} & perms)


def resolve_sede(conn, user, wanted):
    from medicg_app import get_json_key
    from medicg.sedes import sedes_of, user_sede, home_sede, valid_or_default, SedeError
    config = get_json_key(conn, "config", {}) or {}
    if not sedes_of(config):
        return ""
    limited = user_sede(user)
    if limited:
        if wanted and str(wanted) != limited:
            raise TurnoError("Solo puedes manejar los turnos de tu establecimiento.")
        return limited
    try:
        return valid_or_default(config, wanted, home_sede(user, config))
    except SedeError as exc:
        raise TurnoError(str(exc))


def row_dict(row):
    return {k: row[k] for k in ("id", "fecha", "sede", "area", "numero", "codigo", "prioridad", "paciente_id", "nombre", "alias", "estado",
                                "destino", "llamadas", "llamado_en", "llamado_por", "creado_en", "creado_por", "cerrado_en")}


def list_day(conn, sede, fecha=None):
    rows = conn.execute("select * from turnos where fecha = ? and sede = ? order by creado_en, numero", (fecha or today(), sede)).fetchall()
    return [row_dict(r) for r in rows]


def short_name(name):
    parts = [p for p in str(name or "").split() if p]
    if not parts:
        return ""
    return parts[0].capitalize() + (" " + parts[-1][0].upper() + "." if len(parts) > 1 else "")


def create(conn, user, payload, config):
    from medicg_app import get_json_key
    cfg = settings(config)
    letra = str(payload.get("area") or "").strip().upper()
    area = next((a for a in cfg["areas"] if str(a["letra"]).upper() == letra), None)
    if not area:
        raise TurnoError("Elige el área del turno.")
    sede = resolve_sede(conn, user, payload.get("sede"))
    fecha = today()
    patient_id, name, alias = None, str(payload.get("nombre") or "").strip()[:80], ""
    if payload.get("pacienteId"):
        from medicg.sedes import check_patient
        patient = next((p for p in get_json_key(conn, "pacientes", []) or [] if str(p.get("id")) == str(payload.get("pacienteId")) and not p.get("deletedAt")), None)
        if not patient:
            raise TurnoError("Paciente no encontrado.")
        try:
            check_patient(conn, user, patient.get("id"))
        except ValueError as exc:
            raise TurnoError(str(exc))
        patient_id = str(patient.get("id"))
        name = (str(patient.get("nombres", "")) + " " + str(patient.get("apellidos", ""))).strip()
        first, last = str(patient.get("nombres") or "").split(), str(patient.get("apellidos") or "").split()
        alias = ((first[0].capitalize() if first else "") + (" " + last[0][0].upper() + "." if last else "")).strip()
    else:
        alias = short_name(name)
    row = conn.execute("select max(numero) as n from turnos where fecha = ? and sede = ? and area = ?", (fecha, sede, letra)).fetchone()
    numero = int((row["n"] if row and row["n"] is not None else 0)) + 1
    turno = {"id": str(uuid.uuid4()), "fecha": fecha, "sede": sede, "area": letra, "numero": numero,
             "codigo": f"{letra}-{numero:03d}", "prioridad": 1 if payload.get("prioridad") else 0, "paciente_id": patient_id,
             "nombre": name, "alias": alias, "estado": "espera", "destino": "", "llamadas": 0, "llamado_en": None, "llamado_por": "",
             "creado_en": stamp(), "creado_por": staff_name(user), "cerrado_en": None}
    cols = list(turno)
    conn.execute(f"insert into turnos({','.join(cols)}) values({','.join('?' for _ in cols)})", tuple(turno[c] for c in cols))
    return turno


def staff_name(user):
    return (str(user.get("name", "")) + " " + str(user.get("last", ""))).strip() or user.get("email", "")


def call(conn, user, payload):
    sede = resolve_sede(conn, user, payload.get("sede"))
    destino = str(payload.get("destino") or "").strip()[:40]
    if not destino:
        raise TurnoError("Indica a dónde pasa el paciente (consultorio, ventanilla…).")
    if payload.get("id"):
        row = conn.execute("select * from turnos where id = ? and sede = ? and fecha = ?", (payload["id"], sede, today())).fetchone()
        if not row:
            raise TurnoError("Turno no encontrado.")
        if row["estado"] in ("atendido", "cancelado"):
            raise TurnoError("Ese turno ya fue cerrado.")
    else:
        areas = [str(a).upper() for a in (payload.get("areas") or [payload.get("area")]) if a]
        if not areas:
            raise TurnoError("Elige el área a llamar.")
        marks = ",".join("?" for _ in areas)
        # Preferential turns first, then by arrival.
        row = conn.execute(f"select * from turnos where fecha = ? and sede = ? and estado = 'espera' and area in ({marks}) "
                           "order by prioridad desc, creado_en, numero limit 1", (today(), sede, *areas)).fetchone()
        if not row:
            raise TurnoError("No hay turnos en espera.")
        # Calling the next turn to the same room closes the one that was being attended there.
        conn.execute("update turnos set estado = 'atendido', cerrado_en = ? where fecha = ? and sede = ? and estado = 'llamado' and destino = ? and id <> ?",
                     (stamp(), today(), sede, destino, row["id"]))
    conn.execute("update turnos set estado = 'llamado', destino = ?, llamadas = llamadas + 1, llamado_en = ?, llamado_por = ? where id = ?",
                 (destino, time.time(), staff_name(user), row["id"]))
    return row_dict(conn.execute("select * from turnos where id = ?", (row["id"],)).fetchone())


def close(conn, user, payload):
    sede = resolve_sede(conn, user, payload.get("sede"))
    estado = payload.get("estado")
    if estado not in ("atendido", "ausente", "cancelado", "espera"):
        raise TurnoError("Estado inválido.")
    row = conn.execute("select * from turnos where id = ? and sede = ?", (payload.get("id"), sede)).fetchone()
    if not row:
        raise TurnoError("Turno no encontrado.")
    conn.execute("update turnos set estado = ?, cerrado_en = ? where id = ?", (estado, None if estado == "espera" else stamp(), row["id"]))
    return row_dict(conn.execute("select * from turnos where id = ?", (row["id"],)).fetchone())


def display_payload(conn, config, sede):
    """What the waiting-room screen shows: no personal data unless the clinic enables short names."""
    cfg = settings(config)
    rows = list_day(conn, sede)
    called = sorted([r for r in rows if r["llamado_en"]], key=lambda r: r["llamado_en"], reverse=True)
    show = cfg["mostrarNombre"]

    def public(r):
        return {"codigo": r["codigo"], "destino": r["destino"], "area": r["area"], "llamadas": r["llamadas"], "llamadoEn": r["llamado_en"],
                "nombre": (r.get("alias") or short_name(r["nombre"])) if show else "", "estado": r["estado"]}
    waiting = {}
    for r in rows:
        if r["estado"] == "espera":
            waiting[r["area"]] = waiting.get(r["area"], 0) + 1
    from medicg.sedes import sedes_of
    sede_name = next((s.get("nombre") for s in sedes_of(config) if str(s.get("id")) == str(sede)), "")
    return {"ok": True, "now": time.time(), "fecha": today(), "sede": sede, "sedeNombre": sede_name,
            "clinica": (config or {}).get("nombre") or "Centro médico", "logo": (config or {}).get("logo") or "",
            "areas": cfg["areas"], "voz": cfg["voz"], "actual": public(called[0]) if called else None,
            "recientes": [public(r) for r in called[1:7]], "espera": waiting}


def new_display_key():
    return secrets.token_urlsafe(18)
