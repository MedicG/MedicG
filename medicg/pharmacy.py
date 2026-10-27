"""Pharmacy: products, lots (batch + expiry), kardex, electronic prescriptions and dispensing.

- Products and lots live in app_data ("farmaciaProductos", "farmaciaLotes").
- Every stock change writes an append-only row in the pharmacy_moves table (kardex),
  with lot, user, prescription, patient and resulting balance: full traceability.
- Doctors prescribe from the inventory (receta electrónica, MSP format). Pharmacy
  dispenses it FEFO (first expiry, first out) and the same transaction creates the
  patient's account in Caja (paid now or left pending), ready for SRI invoicing.
"""
import datetime as dt
import hashlib
import json
import re
import uuid
from decimal import Decimal

TZ = dt.timezone(dt.timedelta(hours=-5))
FORMS = ("Tableta", "Cápsula", "Jarabe", "Suspensión", "Solución oral", "Gotas", "Inyectable", "Crema", "Ungüento",
         "Gel", "Óvulo", "Supositorio", "Inhalador", "Polvo", "Parche", "Solución oftálmica", "Insumo", "Otro")
CATEGORIES = ("Medicamento", "Insumo médico", "Dispositivo médico", "Suplemento", "Otro")
IVA_RATES = (0, 15)
ADJUST_REASONS = ("Conteo físico", "Corrección de ingreso", "Devolución de paciente", "Otro")
WRITE_OFF_REASONS = ("Caducado", "Dañado / roto", "Retiro sanitario (ARCSA)", "Pérdida", "Otro")


class PharmacyError(ValueError):
    pass


def now():
    return dt.datetime.now(TZ)


def table_sql():
    return ("create table if not exists pharmacy_moves(id text primary key, ts text not null, product_id text not null, "
            "lot_id text, lot text, kind text not null, qty double precision not null, balance double precision not null, "
            "ref text, patient_id text, user_id integer, user_name text, detail text)")


def user_name(user):
    return (str(user.get("name", "")) + " " + str(user.get("last", ""))).strip() or user.get("email", "")


def money(value, label="Precio"):
    try:
        number = Decimal(str(value if value not in (None, "") else 0))
    except Exception:
        raise PharmacyError(label + " inválido.")
    if not number.is_finite() or number < 0 or number > 100000:
        raise PharmacyError(label + " fuera de rango.")
    return number.quantize(Decimal("0.01"))


def qty(value, label="Cantidad", allow_negative=False):
    try:
        number = Decimal(str(value))
    except Exception:
        raise PharmacyError(label + " inválida.")
    if not number.is_finite() or number != number.to_integral_value():
        raise PharmacyError(label + " debe ser un número entero.")
    number = int(number)
    if (number == 0) or (number < 0 and not allow_negative) or abs(number) > 100000:
        raise PharmacyError(label + " fuera de rango.")
    return number


def text(payload, key, maxlen=200, required=False, label=None):
    value = payload.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise PharmacyError("Revisa " + (label or key) + ".")
    value = str(value).strip()
    if len(value) > maxlen:
        raise PharmacyError((label or key) + " supera " + str(maxlen) + " caracteres.")
    if required and not value:
        raise PharmacyError("Completa " + (label or key) + ".")
    return value


def perms(user):
    from medicg_app import clean_permissions
    return set(clean_permissions(user.get("permissions"), user.get("rol", "recepcion")))


def require_pharmacy(user):
    if user.get("rol") != "admin" and "farmacia" not in perms(user):
        raise PharmacyError("No tienes permiso para farmacia.")


def is_prescriber(user):
    return user.get("rol") == "medico" or (user.get("rol") == "admin" and bool(user.get("medicoId"))) or user.get("rol") == "admin"


def load(conn):
    from medicg_app import get_json_key
    return get_json_key(conn, "farmaciaProductos", []) or [], get_json_key(conn, "farmaciaLotes", []) or []


def save(conn, products=None, lots=None):
    from medicg_app import set_json_key
    if products is not None:
        set_json_key(conn, "farmaciaProductos", products)
    if lots is not None:
        set_json_key(conn, "farmaciaLotes", lots)


def stock_of(lots, product_id, usable_only=False):
    today = now().date().isoformat()
    return sum(int(l.get("cantidad") or 0) for l in lots if str(l.get("productoId")) == str(product_id)
               and (not usable_only or (l.get("caducidad") or "9999") >= today))


def record_move(conn, user, product, lot, kind, quantity, balance, ref="", patient_id="", detail=None):
    conn.execute(
        "insert into pharmacy_moves(id,ts,product_id,lot_id,lot,kind,qty,balance,ref,patient_id,user_id,user_name,detail) values(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), now().isoformat(timespec="seconds"), str(product["id"]), str(lot.get("id")) if lot else None,
         lot.get("lote") if lot else None, kind, float(quantity), float(balance), ref, str(patient_id or ""),
         user.get("id"), user_name(user), json.dumps(detail or {}, ensure_ascii=False)),
    )


def find_product(products, product_id):
    product = next((p for p in products if str(p.get("id")) == str(product_id)), None)
    if not product:
        raise PharmacyError("Producto no encontrado. Actualiza la página.")
    return product


# ---------------------------------------------------------------- inventory
def product_save(conn, user, payload):
    from medicg_app import get_json_key, set_json_key, audit
    require_pharmacy(user)
    products, _lots = load(conn)
    data = {
        "nombre": text(payload, "nombre", 160, True, "el nombre genérico (DCI)"),
        "comercial": text(payload, "comercial", 160),
        "concentracion": text(payload, "concentracion", 60),
        "forma": text(payload, "forma", 40) or "Tableta",
        "presentacion": text(payload, "presentacion", 120),
        "via": text(payload, "via", 40),
        "registroSanitario": text(payload, "registroSanitario", 60),
        "codigo": text(payload, "codigo", 40),
        "categoria": text(payload, "categoria", 40) or "Medicamento",
        "controlado": bool(payload.get("controlado")),
        "precioVenta": float(money(payload.get("precioVenta"), "Precio de venta")),
        "stockMinimo": qty(payload.get("stockMinimo") or 1, "Stock mínimo") if str(payload.get("stockMinimo") or "") not in ("", "0") else 0,
        "estado": "inactivo" if payload.get("estado") == "inactivo" else "activo",
    }
    if data["forma"] not in FORMS:
        raise PharmacyError("Forma farmacéutica inválida.")
    if data["categoria"] not in CATEGORIES:
        raise PharmacyError("Categoría inválida.")
    try:
        rate = int(payload.get("ivaTarifa", 0 if data["categoria"] == "Medicamento" else 15))
    except (TypeError, ValueError):
        raise PharmacyError("Tarifa de IVA inválida.")
    if rate not in IVA_RATES:
        raise PharmacyError("La tarifa de IVA debe ser 0% o 15%.")
    data["ivaTarifa"] = rate
    if data["codigo"] and any(p.get("codigo") == data["codigo"] and str(p.get("id")) != str(payload.get("id")) for p in products):
        raise PharmacyError("Ya existe un producto con ese código.")
    stamp = now().isoformat(timespec="seconds")
    if payload.get("id"):
        product = find_product(products, payload["id"])
        product.update(data, actualizadoEn=stamp, actualizadoPor=user_name(user))
        action = "pharmacy_product_update"
    else:
        ids = get_json_key(conn, "nextIds", {}) or {}
        number = max(int(ids.get("farm") or 1), max((int(p.get("id") or 0) for p in products), default=0) + 1)
        ids["farm"] = number + 1
        set_json_key(conn, "nextIds", ids)
        product = {"id": number, **data, "codigo": data["codigo"] or f"FAR{number:05d}", "creadoEn": stamp, "creadoPor": user_name(user)}
        products.append(product)
        action = "pharmacy_product_create"
    save(conn, products=products)
    audit(conn, user, action, "farmaciaProductos", {"productId": product["id"], "nombre": product["nombre"]})
    return {"product": product}


def lot_receive(conn, user, payload):
    from medicg_app import audit
    require_pharmacy(user)
    products, lots = load(conn)
    product = find_product(products, payload.get("productId"))
    lot_code = text(payload, "lote", 60, True, "el número de lote")
    try:
        expiry = dt.date.fromisoformat(str(payload.get("caducidad")))
    except (TypeError, ValueError):
        raise PharmacyError("Fecha de caducidad inválida.")
    if expiry <= now().date():
        raise PharmacyError("No se puede ingresar un lote caducado.")
    quantity = qty(payload.get("cantidad"))
    cost = money(payload.get("costoUnitario"), "Costo unitario")
    lot = next((l for l in lots if str(l.get("productoId")) == str(product["id"]) and l.get("lote") == lot_code), None)
    if lot and lot.get("caducidad") != expiry.isoformat():
        raise PharmacyError("Ese lote ya existe con otra fecha de caducidad. Revisa los datos.")
    if not lot:
        lot = {"id": str(uuid.uuid4()), "productoId": product["id"], "lote": lot_code, "caducidad": expiry.isoformat(), "cantidad": 0,
               "costoUnitario": float(cost), "proveedor": text(payload, "proveedor", 160), "documento": text(payload, "documento", 60),
               "ingresadoEn": now().isoformat(timespec="seconds"), "ingresadoPor": user_name(user)}
        lots.append(lot)
    lot["cantidad"] = int(lot.get("cantidad") or 0) + quantity
    save(conn, lots=lots)
    record_move(conn, user, product, lot, "Ingreso", quantity, stock_of(lots, product["id"]),
                ref=text(payload, "documento", 60), detail={"proveedor": text(payload, "proveedor", 160), "costoUnitario": float(cost)})
    audit(conn, user, "pharmacy_lot_receive", "farmaciaLotes", {"productId": product["id"], "lote": lot_code, "cantidad": quantity})
    return {"lot": lot}


def lot_adjust(conn, user, payload, write_off=False):
    from medicg_app import audit
    require_pharmacy(user)
    products, lots = load(conn)
    lot = next((l for l in lots if l.get("id") == payload.get("lotId")), None)
    if not lot:
        raise PharmacyError("Lote no encontrado.")
    product = find_product(products, lot["productoId"])
    reasons = WRITE_OFF_REASONS if write_off else ADJUST_REASONS
    reason = text(payload, "motivo", 60, True, "el motivo")
    if reason not in reasons:
        raise PharmacyError("Motivo inválido.")
    note = text(payload, "observacion", 500, reason == "Otro", "la observación")
    change = -qty(payload.get("cantidad")) if write_off else qty(payload.get("cantidad"), allow_negative=True)
    if int(lot.get("cantidad") or 0) + change < 0:
        raise PharmacyError(f"El lote {lot['lote']} solo tiene {lot.get('cantidad')} unidades.")
    lot["cantidad"] = int(lot.get("cantidad") or 0) + change
    save(conn, lots=lots)
    kind = "Baja: " + reason if write_off else "Ajuste: " + reason
    record_move(conn, user, product, lot, kind, change, stock_of(lots, product["id"]), detail={"observacion": note})
    audit(conn, user, "pharmacy_write_off" if write_off else "pharmacy_adjust", "farmaciaLotes",
          {"productId": product["id"], "lote": lot["lote"], "cantidad": change, "motivo": reason})
    return {"lot": lot}


# ------------------------------------------------------ electronic prescription
def rx_create(conn, user, payload):
    from medicg_app import get_json_key, set_json_key, audit
    from medicg.clinical_docs import check_access, resolve_doctor, doctor_snapshot, DocsError
    if not is_prescriber(user):
        raise PharmacyError("Solo médicos emiten recetas.")
    patient_id = str(payload.get("patientId") or "")
    try:
        patient = check_access(conn, user, patient_id)
        doctor = resolve_doctor(conn, user, payload)
    except DocsError as exc:
        raise PharmacyError(str(exc))
    products, lots = load(conn)
    raw = payload.get("items")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 30:
        raise PharmacyError("Agrega entre 1 y 30 medicamentos.")
    items = []
    for row in raw:
        if not isinstance(row, dict):
            raise PharmacyError("Medicamento inválido.")
        product = find_product(products, row["productoId"]) if row.get("productoId") else None
        item = {
            "productoId": product["id"] if product else None,
            "nombre": product["nombre"] if product else text(row, "nombre", 160, True, "el medicamento"),
            "comercial": product.get("comercial", "") if product else text(row, "comercial", 160),
            "concentracion": product.get("concentracion", "") if product else text(row, "concentracion", 60),
            "forma": product.get("forma", "") if product else text(row, "forma", 40),
            "via": text(row, "via", 40) or (product.get("via", "") if product else ""),
            "cantidad": qty(row.get("cantidad"), "Cantidad a dispensar"),
            "posologia": text(row, "posologia", 300, True, "la posología (dosis y frecuencia)"),
            "duracion": text(row, "duracion", 80),
            "indicacion": text(row, "indicacion", 300),
            "controlado": bool(product.get("controlado")) if product else False,
        }
        items.append(item)
    diagnosis = text(payload, "diagnostico", 300, True, "el diagnóstico")
    try:
        validity = int(payload.get("validezDias") or 30)
    except (TypeError, ValueError):
        raise PharmacyError("Validez inválida.")
    if not 1 <= validity <= 180:
        raise PharmacyError("La validez debe estar entre 1 y 180 días.")
    ids = get_json_key(conn, "nextIds", {}) or {}
    number = int(ids.get("rx") or 1)
    ids["rx"] = number + 1
    set_json_key(conn, "nextIds", ids)
    stamp = now()
    summary = "\n".join(f"{i['nombre']} {i['concentracion']} {i['forma']} #{i['cantidad']} — {i['posologia']}{(' por ' + i['duracion']) if i['duracion'] else ''}".replace("  ", " ") for i in items)
    receta = {
        "id": int(stamp.timestamp() * 1000), "rxVersion": 1, "numero": f"RX-{number:06d}", "formato": "Receta médica electrónica - MSP",
        "fecha": stamp.date().isoformat(), "hora": stamp.strftime("%H:%M"), "validezDias": validity,
        "vence": (stamp.date() + dt.timedelta(days=validity - 1)).isoformat(),
        "medico": doctor.get("nombre", ""), "registro": doctor.get("sen", "") or doctor.get("cedula", ""), "medicoInfo": doctor_snapshot(doctor),
        "diagnostico": diagnosis, "cie10": text(payload, "cie10", 12).upper(), "alergias": text(payload, "alergias", 300) or (patient.get("alergias") or ""),
        "items": items, "medicamentos": summary, "indicaciones": text(payload, "indicaciones", 1500),
        "paciente": {"nombre": (patient.get("nombres", "") + " " + patient.get("apellidos", "")).strip(), "cedula": patient.get("cedula", "")},
        "dispensacion": {"estado": "Pendiente", "lineas": [{"dispensado": 0} for _ in items], "entregas": []},
        "creadoPor": user_name(user), "creadoPorId": user.get("id"), "creadoEn": stamp.isoformat(timespec="seconds"),
    }
    recetas = get_json_key(conn, "recetas", {}) or {}
    recetas.setdefault(patient_id, []).insert(0, receta)
    set_json_key(conn, "recetas", recetas)
    audit(conn, user, "rx_create", "recetas", {"patientId": patient_id, "numero": receta["numero"], "items": len(items)})
    stock = {str(i["productoId"]): stock_of(lots, i["productoId"], True) for i in items if i["productoId"]}
    return {"receta": receta, "patientId": patient_id, "records": recetas[patient_id], "stock": stock}


def queue(conn, user):
    """Pending e-prescriptions for the pharmacy (minimal patient data, no full clinical record)."""
    from medicg_app import get_json_key
    require_pharmacy(user)
    patients = {str(p.get("id")): p for p in get_json_key(conn, "pacientes", []) or [] if not p.get("deletedAt")}
    result = []
    today = now().date().isoformat()
    for pid, rows in (get_json_key(conn, "recetas", {}) or {}).items():
        if str(pid) not in patients:
            continue
        for r in rows or []:
            if r.get("rxVersion") != 1 or (r.get("dispensacion") or {}).get("estado") in ("Dispensada", "Anulada"):
                continue
            result.append({"patientId": str(pid), "rxId": r["id"], "numero": r["numero"], "fecha": r["fecha"], "vence": r.get("vence"),
                           "vencida": (r.get("vence") or "9999") < today, "medico": r.get("medico"), "paciente": r.get("paciente"),
                           "diagnostico": r.get("diagnostico"), "cie10": r.get("cie10"), "items": r.get("items"),
                           "dispensacion": r.get("dispensacion")})
    result.sort(key=lambda r: (r["vencida"], r["fecha"]), reverse=False)
    return {"queue": result}


# ------------------------------------------------------------------ dispensing
def dispense(conn, user, payload):
    """Dispense (from a prescription or as an over-the-counter sale), FEFO by expiry,
    and create the patient's account in Caja in the same transaction."""
    from medicg_app import get_json_key, set_json_key, audit
    from medicg.cash import create_account, CashError
    require_pharmacy(user)
    request_id = payload.get("requestId")
    if not isinstance(request_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{16,80}", request_id):
        raise PharmacyError("Falta identificador de operación. Recarga la página.")
    key = "farm:" + str(user["id"]) + ":" + request_id
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    previous = conn.execute("select payload_hash, invoice_id from cash_requests where request_id = ?", (key,)).fetchone()
    if previous:
        if previous["payload_hash"] != digest:
            raise PharmacyError("La operación ya se utilizó con otros datos.")
        invoice = next((f for f in get_json_key(conn, "facturas", []) or [] if f.get("id") == previous["invoice_id"]), None)
        return {"ok": True, "invoice": invoice, "replayed": True}
    patients = get_json_key(conn, "pacientes", []) or []
    patient = next((p for p in patients if str(p.get("id")) == str(payload.get("patientId")) and not p.get("deletedAt")), None)
    if not patient:
        raise PharmacyError("Selecciona un paciente activo.")
    products, lots = load(conn)
    recetas = get_json_key(conn, "recetas", {}) or {}
    receta = None
    if payload.get("rxId"):
        receta = next((r for r in recetas.get(str(patient["id"]), []) if str(r.get("id")) == str(payload["rxId"]) and r.get("rxVersion") == 1), None)
        if not receta:
            raise PharmacyError("Receta no encontrada para este paciente.")
        state = (receta.get("dispensacion") or {}).get("estado")
        if state in ("Dispensada", "Anulada"):
            raise PharmacyError("La receta ya fue dispensada o está anulada.")
        if (receta.get("vence") or "9999") < now().date().isoformat():
            raise PharmacyError("La receta está vencida. El médico debe emitir una nueva.")
    raw = payload.get("lines")
    if not isinstance(raw, list) or not 1 <= len(raw) <= 60:
        raise PharmacyError("Agrega entre 1 y 60 productos.")
    today = now().date().isoformat()
    lines, charge_items, moves = [], [], []
    for row in raw:
        if not isinstance(row, dict):
            raise PharmacyError("Producto inválido.")
        product = find_product(products, row.get("productId"))
        if product.get("estado") == "inactivo":
            raise PharmacyError(f"{product['nombre']} está inactivo.")
        quantity = qty(row.get("cantidad"))
        rx_index = row.get("rxIndex")
        if receta is not None and rx_index is not None:
            if isinstance(rx_index, bool) or not isinstance(rx_index, int) or not 0 <= rx_index < len(receta["items"]):
                raise PharmacyError("Línea de receta inválida.")
            prescribed = receta["items"][rx_index]
            done = receta["dispensacion"]["lineas"][rx_index]["dispensado"]
            if quantity > prescribed["cantidad"] - done:
                raise PharmacyError(f"{prescribed['nombre']}: quedan {prescribed['cantidad'] - done} unidades por dispensar en la receta.")
            if prescribed.get("productoId") and str(prescribed["productoId"]) != str(product["id"]) and not row.get("sustituto"):
                raise PharmacyError(f"{prescribed['nombre']}: el producto no coincide con la receta.")
        elif product.get("controlado"):
            raise PharmacyError(f"{product['nombre']} es de control especial: solo se dispensa con receta.")
        available = sorted((l for l in lots if str(l.get("productoId")) == str(product["id"]) and int(l.get("cantidad") or 0) > 0
                            and (l.get("caducidad") or "9999") >= today), key=lambda l: (l.get("caducidad") or "9999", l.get("ingresadoEn") or ""))
        if sum(int(l["cantidad"]) for l in available) < quantity:
            raise PharmacyError(f"Stock insuficiente de {product['nombre']}: hay {sum(int(l['cantidad']) for l in available)} unidades vigentes.")
        remaining, taken = quantity, []
        for lot in available:
            if not remaining:
                break
            use = min(remaining, int(lot["cantidad"]))
            lot["cantidad"] = int(lot["cantidad"]) - use
            remaining -= use
            taken.append({"lotId": lot["id"], "lote": lot["lote"], "caducidad": lot["caducidad"], "cantidad": use})
            moves.append((product, lot, use))
        unit = money(row["precio"], "Precio") if "precio" in row and user.get("rol") in ("admin", "recepcion", "secretaria") else money(product.get("precioVenta"))
        lines.append({"productId": product["id"], "nombre": product["nombre"], "cantidad": quantity, "lotes": taken, "rxIndex": rx_index})
        charge_items.append({"kind": "medicamento", "id": product["id"], "codigo": product.get("codigo") or f"FAR{product['id']}",
                             "nombre": " ".join(x for x in (product["nombre"], product.get("concentracion"), product.get("forma")) if x),
                             "cantidad": quantity, "unit": float(unit), "ivaRate": int(product.get("ivaTarifa") or 0),
                             "lotes": [t["lote"] for t in taken]})
    try:
        invoice = create_account(conn, user, patient, charge_items, payload.get("payments") or [],
                                 "Farmacia" + (" · " + receta["numero"] if receta else ""))
    except CashError as exc:
        raise PharmacyError(str(exc))
    if receta is not None:
        stamp = now().isoformat(timespec="seconds")
        for line in lines:
            if line["rxIndex"] is not None:
                receta["dispensacion"]["lineas"][line["rxIndex"]]["dispensado"] += line["cantidad"]
        complete = all(l["dispensado"] >= i["cantidad"] for l, i in zip(receta["dispensacion"]["lineas"], receta["items"]))
        receta["dispensacion"]["estado"] = "Dispensada" if complete or payload.get("cerrarReceta") else "Parcial"
        receta["dispensacion"]["entregas"].append({"fecha": stamp, "por": user_name(user), "factura": invoice["id"],
                                                    "lineas": [{k: l[k] for k in ("nombre", "cantidad", "lotes")} for l in lines]})
        set_json_key(conn, "recetas", recetas)
    save(conn, lots=lots)
    reference = (receta["numero"] + " · " if receta else "") + invoice["id"]
    for product, lot, use in moves:
        record_move(conn, user, product, lot, "Dispensación" if receta else "Venta sin receta", -use,
                    stock_of(lots, product["id"]), ref=reference, patient_id=patient["id"])
    conn.execute("insert into cash_requests(request_id,payload_hash,invoice_id,created_at) values(?,?,?,?)",
                 (key, digest, invoice["id"], now().isoformat(timespec="seconds")))
    audit(conn, user, "pharmacy_dispense", "farmaciaLotes", {"invoiceId": invoice["id"], "receta": receta["numero"] if receta else None,
                                                             "lines": [{"producto": l["nombre"], "cantidad": l["cantidad"]} for l in lines]})
    return {"ok": True, "invoice": invoice, "lines": lines, "receta": receta, "replayed": False}


def kardex(conn, user, product_id="", limit=300):
    require_pharmacy(user)
    limit = max(1, min(2000, int(limit or 300)))
    if product_id:
        rows = conn.execute("select * from pharmacy_moves where product_id = ? order by ts desc limit ?", (str(product_id), limit)).fetchall()
    else:
        rows = conn.execute("select * from pharmacy_moves order by ts desc limit ?", (limit,)).fetchall()
    return {"moves": [{k: row[k] for k in ("id", "ts", "product_id", "lot_id", "lot", "kind", "qty", "balance", "ref", "patient_id", "user_name", "detail")} for row in rows]}


def operation(conn, user, payload):
    action = payload.get("action")
    handlers = {
        "product_save": product_save,
        "lot_receive": lot_receive,
        "lot_adjust": lambda c, u, p: lot_adjust(c, u, p, False),
        "lot_write_off": lambda c, u, p: lot_adjust(c, u, p, True),
        "rx_create": rx_create,
        "dispense": dispense,
    }
    if action not in handlers:
        raise PharmacyError("Acción inválida.")
    result = handlers[action](conn, user, payload)
    products, lots = load(conn)
    return {"ok": True, **result, "farmaciaProductos": products, "farmaciaLotes": lots}
