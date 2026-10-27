"""Vital signs (editable with history), medical certificates and laboratory orders.

Each collection is stored per patient in app_data ("signosVitales", "certificados",
"ordenesLab") and is written only through /api/clinical/docs, never through the
generic /api/data save, so every change is validated and audited.
"""
import datetime as dt
import re
import uuid

KEYS = ("signosVitales", "certificados", "ordenesLab")
TZ = dt.timezone(dt.timedelta(hours=-5))
CERT_TYPES = ("Reposo médico", "Asistencia a consulta", "Certificado de salud", "Otro")
ORDER_STATES = ("Pendiente", "Muestra tomada", "Resultados recibidos", "Anulada")
PRIORITIES = ("Rutina", "Urgente")
VITAL_LIMITS = {
    "fc": (20, 250, "Frecuencia cardiaca"),
    "fr": (4, 80, "Frecuencia respiratoria"),
    "temp": (30, 45, "Temperatura"),
    "spo2": (50, 100, "Saturación de oxígeno"),
    "peso": (0.3, 400, "Peso"),
    "talla": (20, 250, "Talla"),
    "glucosa": (10, 1000, "Glucosa capilar"),
    "perimetroAbdominal": (20, 250, "Perímetro abdominal"),
}


class DocsError(ValueError):
    pass


def now():
    return dt.datetime.now(TZ)


def user_name(user):
    return (str(user.get("name", "")) + " " + str(user.get("last", ""))).strip() or user.get("email", "")


def text(payload, key, maxlen=1000, required=False, label=None):
    value = payload.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise DocsError("Revisa el campo " + (label or key) + ".")
    value = str(value).strip()
    if len(value) > maxlen:
        raise DocsError((label or key) + " supera " + str(maxlen) + " caracteres.")
    if required and not value:
        raise DocsError("Completa " + (label or key) + ".")
    return value


def parse_date(value, label, allow_future=False):
    try:
        day = dt.date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise DocsError("Fecha inválida en " + label + ".")
    if not allow_future and day > now().date():
        raise DocsError(label + " no puede ser una fecha futura.")
    return day


def is_doctor(user):
    return user.get("rol") == "medico" or (user.get("rol") == "admin" and bool(user.get("medicoId")))


def can_read(user):
    from medicg_app import can_save_key
    return user.get("rol") == "admin" or can_save_key(user, "notas") or "hce" in set(user.get("permissions") or [])


CERT_ACTIONS = ("certificate_create", "certificate_void", "certificate_list")
ORDER_ACTIONS = ("lab_order_create", "lab_order_status", "lab_order_list")
STAFF_ACTIONS = {**{a: "certificados" for a in CERT_ACTIONS}, **{a: "ordenes" for a in ORDER_ACTIONS}}


def perms_of(user):
    from medicg_app import clean_permissions
    return set(clean_permissions(user.get("permissions"), user.get("rol", "recepcion")))


def is_staff(user, perm):
    """Reception/secretary users who prepare documents on a doctor's request (no access to the medical record)."""
    return user.get("rol") in ("recepcion", "secretaria") and perm in perms_of(user)


def is_cert_staff(user):
    return is_staff(user, "certificados")


def is_order_staff(user):
    return is_staff(user, "ordenes")


def check_access(conn, user, patient_id, write=True, action=None):
    from medicg_app import get_json_key
    from medicg.doctor_scope import check_patient
    perms = perms_of(user)
    if user.get("rol") != "admin" and "hce" not in perms and not (action in STAFF_ACTIONS and is_staff(user, STAFF_ACTIONS[action])):
        raise DocsError("No tienes permiso para la historia clínica.")
    patient = next((p for p in get_json_key(conn, "pacientes", []) or [] if str(p.get("id")) == str(patient_id) and not p.get("deletedAt")), None)
    if not patient:
        raise DocsError("Paciente no disponible.")
    try:
        check_patient(conn, user, patient_id)
    except ValueError as exc:
        raise DocsError(str(exc))
    return patient


def resolve_doctor(conn, user, payload):
    from medicg_app import get_json_key
    medicos = get_json_key(conn, "medicos", []) or []
    if user.get("rol") == "medico":
        wanted = user.get("medicoId")
    else:
        wanted = payload.get("doctorId") or user.get("medicoId")
    doctor = next((m for m in medicos if str(m.get("id")) == str(wanted) and m.get("estado") != "inactivo"), None)
    if not doctor:
        raise DocsError("Selecciona el médico que firma el documento.")
    return doctor


def doctor_snapshot(doctor):
    return {
        "id": doctor.get("id"),
        "nombre": doctor.get("nombre", ""),
        "especialidad": doctor.get("esp", ""),
        "cedula": doctor.get("cedula", ""),
        "registro": doctor.get("sen", ""),
    }


def next_number(conn, key, prefix):
    from medicg_app import get_json_key, set_json_key
    ids = get_json_key(conn, "nextIds", {}) or {}
    number = int(ids.get(key) or 1)
    ids[key] = number + 1
    set_json_key(conn, "nextIds", ids)
    return f"{prefix}-{number:06d}"


def store(conn, key):
    from medicg_app import get_json_key
    data = get_json_key(conn, key, {}) or {}
    return data if isinstance(data, dict) else {}


# ---------------------------------------------------------------- vital signs
def clean_vitals(payload):
    values = {}
    pa = text(payload, "pa", 9, label="Presión arterial")
    if pa:
        match = re.fullmatch(r"(\d{2,3})\s*/\s*(\d{2,3})", pa)
        if not match or not (50 <= int(match.group(1)) <= 300 and 20 <= int(match.group(2)) <= 200) or int(match.group(1)) <= int(match.group(2)):
            raise DocsError("Presión arterial inválida. Usa el formato 120/80.")
        values["pa"] = f"{int(match.group(1))}/{int(match.group(2))}"
    for key, (low, high, label) in VITAL_LIMITS.items():
        raw = payload.get(key, "")
        if raw in ("", None):
            continue
        try:
            number = float(str(raw).replace(",", "."))
        except (TypeError, ValueError):
            raise DocsError(label + " debe ser un número.")
        if not low <= number <= high:
            raise DocsError(f"{label} fuera de rango ({low}–{high}).")
        values[key] = round(number, 1)
    if not values:
        raise DocsError("Registra al menos un signo vital.")
    if values.get("peso") and values.get("talla"):
        meters = values["talla"] / 100
        values["imc"] = round(values["peso"] / (meters * meters), 1)
    return values


def save_vitals(conn, user, payload, patient_id):
    from medicg_app import set_json_key, audit
    data = store(conn, "signosVitales")
    records = data.get(str(patient_id), [])
    values = clean_vitals(payload)
    notes = text(payload, "observaciones", 1000, label="Observaciones")
    record_id = text(payload, "id", 64)
    stamp = now().isoformat(timespec="seconds")
    if record_id:
        if not is_doctor(user):
            raise DocsError("Solo los médicos pueden editar signos vitales registrados.")
        record = next((r for r in records if r.get("id") == record_id), None)
        if not record:
            raise DocsError("El registro de signos vitales ya no existe. Actualiza la página.")
        reason = text(payload, "motivo", 500, True, "el motivo de la corrección")
        history = record.setdefault("historial", [])
        history.append({"valores": record.get("valores", {}), "observaciones": record.get("observaciones", ""),
                        "editadoPor": user_name(user), "editadoPorId": user.get("id"), "editadoEn": stamp, "motivo": reason})
        record.update(valores=values, observaciones=notes, actualizadoEn=stamp, actualizadoPor=user_name(user))
        action = "vitals_edit"
    else:
        day = parse_date(payload.get("fecha") or now().date().isoformat(), "la fecha")
        hour = text(payload, "hora", 5) or now().strftime("%H:%M")
        if not re.fullmatch(r"\d{2}:\d{2}", hour):
            raise DocsError("Hora inválida.")
        record = {"id": str(uuid.uuid4()), "fecha": day.isoformat(), "hora": hour, "valores": values,
                  "observaciones": notes, "registradoPor": user_name(user), "registradoPorId": user.get("id"),
                  "registradoEn": stamp, "historial": []}
        records.insert(0, record)
        action = "vitals_create"
    data[str(patient_id)] = records
    set_json_key(conn, "signosVitales", data)
    audit(conn, user, action, "signosVitales", {"patientId": str(patient_id), "id": record["id"]})
    return "signosVitales", records


def edit_note_vitals(conn, user, payload, patient_id):
    """Correct the vital signs of a saved HCU note, keeping the previous values."""
    from medicg_app import get_json_key, set_json_key, audit
    if not is_doctor(user):
        raise DocsError("Solo los médicos pueden editar signos vitales registrados.")
    notes = get_json_key(conn, "notas", {}) or {}
    entries = notes.get(str(patient_id), [])
    note = next((n for n in entries if str(n.get("id")) == str(payload.get("noteId"))), None)
    if not note or note.get("clinicalVersion"):
        raise DocsError("No se encontró la HCU. Las evoluciones de bitácora se corrigen con una adenda.")
    values = clean_vitals(payload)
    reason = text(payload, "motivo", 500, True, "el motivo de la corrección")
    fields = ("pa", "fc", "fr", "temp", "spo2", "peso", "talla", "imc")
    note.setdefault("signosHistorial", []).append({
        "valores": {k: note.get(k, "") for k in fields}, "editadoPor": user_name(user),
        "editadoPorId": user.get("id"), "editadoEn": now().isoformat(timespec="seconds"), "motivo": reason})
    for key in fields:
        note[key] = str(values[key]) if key in values else ""
    notes[str(patient_id)] = entries
    set_json_key(conn, "notas", notes)
    audit(conn, user, "note_vitals_edit", "notas", {"patientId": str(patient_id), "noteId": str(note.get("id"))})
    return "notas", entries


# ---------------------------------------------------------- medical certificates
def create_certificate(conn, user, payload, patient, patient_id):
    from medicg_app import set_json_key, audit
    if not is_doctor(user) and user.get("rol") != "admin" and not is_cert_staff(user):
        raise DocsError("No tienes permiso para emitir certificados.")
    if is_cert_staff(user) and not payload.get("doctorId"):
        raise DocsError("Selecciona el médico que solicitó el certificado.")
    doctor = resolve_doctor(conn, user, payload)
    kind = text(payload, "tipo", 40, True, "el tipo de certificado")
    if kind not in CERT_TYPES:
        raise DocsError("Tipo de certificado inválido.")
    attention = parse_date(payload.get("fechaAtencion") or now().date().isoformat(), "la fecha de atención")
    diagnosis = text(payload, "diagnostico", 300, kind == "Reposo médico", "el diagnóstico")
    cie = text(payload, "cie10", 12).upper()
    content = text(payload, "contenido", 3000, kind in ("Certificado de salud", "Otro"), "el contenido del certificado")
    recommendations = text(payload, "recomendaciones", 1000)
    home = text(payload, "domicilio", 300)
    company = text(payload, "empresa", 200)
    position = text(payload, "cargo", 150)
    rest = None
    if kind == "Reposo médico":
        try:
            days = int(payload.get("diasReposo"))
        except (TypeError, ValueError):
            raise DocsError("Indica los días de reposo.")
        if not 1 <= days <= 365:
            raise DocsError("Los días de reposo deben estar entre 1 y 365.")
        start = parse_date(payload.get("desde") or attention.isoformat(), "el inicio del reposo", allow_future=True)
        if start < attention - dt.timedelta(days=3):
            raise DocsError("El reposo no puede iniciar más de 3 días antes de la atención.")
        rest = {"dias": days, "desde": start.isoformat(), "hasta": (start + dt.timedelta(days=days - 1)).isoformat()}
    data = store(conn, "certificados")
    records = data.get(str(patient_id), [])
    record = {
        "id": str(uuid.uuid4()), "numero": next_number(conn, "cert", "CERT"), "tipo": kind,
        "fechaEmision": now().date().isoformat(), "fechaAtencion": attention.isoformat(),
        "diagnostico": diagnosis, "cie10": cie, "reposo": rest, "contenido": content,
        "domicilio": home, "empresa": company, "cargo": position,
        "recomendaciones": recommendations, "medico": doctor_snapshot(doctor),
        "paciente": {"nombre": (patient.get("nombres", "") + " " + patient.get("apellidos", "")).strip(), "cedula": patient.get("cedula", "")},
        "estado": "Vigente", "emitidoPor": user_name(user), "emitidoPorId": user.get("id"),
        "emitidoPorRol": user.get("rol"),
        "emitidoEn": now().isoformat(timespec="seconds"),
    }
    records.insert(0, record)
    data[str(patient_id)] = records
    set_json_key(conn, "certificados", data)
    audit(conn, user, "certificate_create", "certificados", {"patientId": str(patient_id), "numero": record["numero"]})
    return "certificados", records


def void_certificate(conn, user, payload, patient_id):
    from medicg_app import set_json_key, audit
    data = store(conn, "certificados")
    records = data.get(str(patient_id), [])
    record = next((r for r in records if r.get("id") == payload.get("id")), None)
    if not record:
        raise DocsError("Certificado no encontrado.")
    own_doctor = user.get("medicoId") and str((record.get("medico") or {}).get("id")) == str(user.get("medicoId"))
    own_staff = is_cert_staff(user) and str(record.get("emitidoPorId")) == str(user.get("id"))
    if user.get("rol") != "admin" and not own_doctor and not own_staff:
        raise DocsError("Solo quien lo emitió, el médico firmante o el administrador puede anularlo.")
    if record.get("estado") == "Anulado":
        return "certificados", records
    record.update(estado="Anulado", anuladoPor=user_name(user), anuladoEn=now().isoformat(timespec="seconds"),
                  motivoAnulacion=text(payload, "motivo", 500, True, "el motivo de anulación"))
    set_json_key(conn, "certificados", data)
    audit(conn, user, "certificate_void", "certificados", {"patientId": str(patient_id), "numero": record.get("numero")})
    return "certificados", records


# ------------------------------------------------------------- laboratory orders
def create_lab_order(conn, user, payload, patient, patient_id):
    from medicg_app import get_json_key, set_json_key, audit
    if not is_doctor(user) and user.get("rol") != "admin" and not is_order_staff(user):
        raise DocsError("No tienes permiso para crear órdenes de exámenes.")
    if is_order_staff(user) and not payload.get("doctorId"):
        raise DocsError("Selecciona el médico que solicitó los exámenes.")
    doctor = resolve_doctor(conn, user, payload)
    catalog = {str(e.get("id")): e for e in get_json_key(conn, "examenes", []) or []}
    raw_items = payload.get("examenes")
    if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 80:
        raise DocsError("Selecciona entre 1 y 80 exámenes.")
    items, seen = [], set()
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise DocsError("Examen inválido.")
        exam_id = str(raw.get("id") or "")
        if exam_id:
            exam = catalog.get(exam_id)
            if not exam:
                raise DocsError("Un examen ya no existe en el catálogo. Actualiza la página.")
            item = {"id": exam.get("id"), "nombre": exam.get("nombre", ""), "categoria": exam.get("categoria", "")}
        else:
            name = text(raw, "nombre", 120, True, "el nombre del examen")
            item = {"id": None, "nombre": name, "categoria": "Otro"}
        key = (str(item["id"]), item["nombre"].lower())
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    priority = text(payload, "prioridad", 20) or "Rutina"
    if priority not in PRIORITIES:
        raise DocsError("Prioridad inválida.")
    data = store(conn, "ordenesLab")
    records = data.get(str(patient_id), [])
    stamp = now().isoformat(timespec="seconds")
    record = {
        "id": str(uuid.uuid4()), "numero": next_number(conn, "ordLab", "LAB"), "fecha": now().date().isoformat(),
        "examenes": items, "diagnostico": text(payload, "diagnostico", 300, label="el diagnóstico presuntivo"),
        "cie10": text(payload, "cie10", 12).upper(), "indicaciones": text(payload, "indicaciones", 1000, label="las indicaciones"),
        "prioridad": priority, "medico": doctor_snapshot(doctor),
        "paciente": {"nombre": (patient.get("nombres", "") + " " + patient.get("apellidos", "")).strip(), "cedula": patient.get("cedula", "")},
        "estado": "Pendiente", "historialEstado": [{"estado": "Pendiente", "por": user_name(user), "en": stamp}],
        "creadoPor": user_name(user), "creadoPorId": user.get("id"), "creadoPorRol": user.get("rol"), "creadoEn": stamp,
    }
    records.insert(0, record)
    data[str(patient_id)] = records
    set_json_key(conn, "ordenesLab", data)
    audit(conn, user, "lab_order_create", "ordenesLab", {"patientId": str(patient_id), "numero": record["numero"], "examenes": len(items)})
    return "ordenesLab", records


def update_lab_order(conn, user, payload, patient_id):
    from medicg_app import set_json_key, audit
    data = store(conn, "ordenesLab")
    records = data.get(str(patient_id), [])
    record = next((r for r in records if r.get("id") == payload.get("id")), None)
    if not record:
        raise DocsError("Orden no encontrada.")
    state = text(payload, "estado", 30, True, "el estado")
    if state not in ORDER_STATES:
        raise DocsError("Estado inválido.")
    if record.get("estado") == "Anulada":
        raise DocsError("La orden está anulada.")
    entry = {"estado": state, "por": user_name(user), "en": now().isoformat(timespec="seconds")}
    if state == "Anulada":
        own_staff = is_order_staff(user) and str(record.get("creadoPorId")) == str(user.get("id"))
        if not is_doctor(user) and user.get("rol") != "admin" and not own_staff:
            raise DocsError("Solo quien creó la orden, un médico o el administrador puede anularla.")
        entry["motivo"] = text(payload, "motivo", 500, True, "el motivo de anulación")
    record["estado"] = state
    record.setdefault("historialEstado", []).append(entry)
    set_json_key(conn, "ordenesLab", data)
    audit(conn, user, "lab_order_status", "ordenesLab", {"patientId": str(patient_id), "numero": record.get("numero"), "estado": state})
    return "ordenesLab", records


def operation(conn, user, payload):
    action = payload.get("action")
    patient_id = str(payload.get("patientId") or "")
    if not patient_id:
        raise DocsError("Selecciona un paciente.")
    patient = check_access(conn, user, patient_id, action=action)
    if user.get("rol") in ("recepcion", "secretaria") and "hce" not in perms_of(user) and action not in STAFF_ACTIONS:
        raise DocsError("No tienes permiso para la historia clínica.")
    if action == "certificate_list":
        key, records = "certificados", store(conn, "certificados").get(str(patient_id), [])
    elif action == "lab_order_list":
        key, records = "ordenesLab", store(conn, "ordenesLab").get(str(patient_id), [])
    elif action == "vitals_save":
        key, records = save_vitals(conn, user, payload, patient_id)
    elif action == "note_vitals":
        key, records = edit_note_vitals(conn, user, payload, patient_id)
    elif action == "certificate_create":
        key, records = create_certificate(conn, user, payload, patient, patient_id)
    elif action == "certificate_void":
        key, records = void_certificate(conn, user, payload, patient_id)
    elif action == "lab_order_create":
        key, records = create_lab_order(conn, user, payload, patient, patient_id)
    elif action == "lab_order_status":
        key, records = update_lab_order(conn, user, payload, patient_id)
    else:
        raise DocsError("Acción inválida.")
    return {"ok": True, "key": key, "patientId": patient_id, "records": records}
