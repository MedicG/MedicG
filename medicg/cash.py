"""Atomic multi-item charges and append-only payments, stored in existing invoices."""
import datetime as dt
import hashlib
import json
import re
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

METHODS = {"Efectivo", "Tarjeta débito", "Tarjeta crédito", "Transferencia"}
CENT = Decimal("0.01")

class CashError(ValueError):
    pass

def amount(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0 or result > 10000000:
            raise CashError("Monto fuera de rango.")
        return result.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise CashError("Monto inválido.")

def effective_unit(item, kind, raw, user):
    price = amount(item.get("precio", 0))
    discount = amount(item.get("descuento", 0)) if kind == "examen" else Decimal(0)
    if discount > 100:
        raise CashError("Descuento inválido en el catálogo.")
    catalog_unit = amount(price * (1 - discount / 100))
    unit = catalog_unit
    if "unitPrice" in raw:
        if user.get("rol") not in ("admin", "recepcion", "secretaria"):
            raise CashError("Solo administración, recepción o secretaría pueden cambiar precios.")
        unit = amount(raw["unitPrice"])
    return price, discount, catalog_unit, unit


def cash_operation(conn, user, payload, action):
    from medicg_app import get_json_key, set_json_key, audit
    request_id = payload.get("requestId")
    if not isinstance(request_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{16,80}", request_id):
        raise CashError("Falta identificador de operación. Recarga la página.")
    key = str(user["id"]) + ":" + request_id
    digest = hashlib.sha256(json.dumps({"action": action, "payload": payload}, sort_keys=True).encode()).hexdigest()
    previous = conn.execute("select payload_hash, invoice_id from cash_requests where request_id = ?", (key,)).fetchone()
    invoices = get_json_key(conn, "facturas", []) or []
    if previous:
        if previous["payload_hash"] != digest:
            raise CashError("La operación ya se utilizó con otros datos.")
        invoice = next((f for f in invoices if f.get("id") == previous["invoice_id"]), None)
        return {"ok": True, "invoice": invoice, "replayed": True}
    boxes = get_json_key(conn, "cajas", []) or []
    box = next((c for c in boxes if c.get("estado") == "abierta"), None)
    if not box:
        raise CashError("Abre caja antes de registrar cobros o abonos.")
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).isoformat(timespec="seconds")
    if action == "charge":
        patients = get_json_key(conn, "pacientes", []) or []
        patient = next((p for p in patients if str(p.get("id")) == str(payload.get("patientId"))), None)
        if not patient:
            raise CashError("Selecciona un paciente válido.")
        raw_items = payload.get("items")
        if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 100:
            raise CashError("Agrega entre 1 y 100 servicios o exámenes.")
        items = []
        for raw in raw_items:
            if not isinstance(raw, dict) or raw.get("kind") not in ("servicio", "examen"):
                raise CashError("Concepto inválido.")
            source = "servicios" if raw["kind"] == "servicio" else "examenes"
            item = next((i for i in (get_json_key(conn, source, []) or []) if str(i.get("id")) == str(raw.get("id"))), None)
            if not item:
                raise CashError("El concepto ya no existe. Actualiza el catálogo.")
            quantity = raw.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= 1000:
                raise CashError("La cantidad debe ser un entero entre 1 y 1000.")
            price, discount, catalog_unit, unit = effective_unit(item, raw["kind"], raw, user)
            subtotal = amount(unit * quantity)
            items.append({"kind": raw["kind"], "id": item["id"], "nombre": item["nombre"], "cantidad": quantity,
                          "precioCatalogoNeto": float(catalog_unit), "precioAjustado": unit != catalog_unit, "precioAjustadoPor": user["id"] if unit != catalog_unit else None, "precio": float(price), "descuento": float(discount), "precioNeto": float(unit), "desc": item["nombre"], "cant": quantity, "unit": float(unit), "total": float(subtotal)})
        subtotal = amount(sum((amount(i["total"]) for i in items), Decimal(0)))
        # Medical services and diagnostic exams in this cash flow have zero VAT.
        rate = Decimal(0)
        tax = amount(subtotal * rate / 100)
        total = amount(subtotal + tax)
        if total <= 0:
            raise CashError("El total debe ser mayor a cero.")
        if amount(payload.get("expectedTotal")) != total:
            raise CashError("El precio o IVA cambió. Actualiza los conceptos antes de cobrar.")
        ids = get_json_key(conn, "nextIds", {}) or {}
        number = max(int(ids.get("fac") or 1), max((int(str(f.get("id", "")).split("-")[-1]) for f in invoices if re.fullmatch(r"\d{3}-\d{3}-\d{9}", str(f.get("id", "")))), default=0) + 1)
        if number > 999999999:
            raise CashError("Secuencia de facturas agotada.")
        cfg = get_json_key(conn, "config", {}) or {}
        prefix = str(cfg.get("sriEstab") or "001").zfill(3)[-3:] + "-" + str(cfg.get("sriPtoEmi") or "001").zfill(3)[-3:] + "-"
        invoice = {"id": prefix + str(number).zfill(9), "fecha": stamp[:10], "createdAt": stamp,
                   "pac": patient["id"], "esp": "General", "serv": "; ".join(i["nombre"] for i in items),
                   "items": items, "sub": float(subtotal), "iva": float(tax), "ivaRate": float(rate), "total": float(total),
                   "cobroVersion": 1, "pagos": [], "abonado": 0, "saldo": float(total)}
        ids["fac"] = number + 1
        invoices.insert(0, invoice)
    else:
        invoice = next((f for f in invoices if f.get("id") == payload.get("invoiceId") and f.get("cobroVersion") == 1), None)
        if not invoice:
            raise CashError("Cuenta no encontrada o registro anterior sin desglose de abonos.")
        if invoice.get("estado") == "Anulado":
            raise CashError("La cuenta está anulada.")
        total = amount(invoice["total"])
        paid = sum((amount(p["monto"]) for p in invoice.get("pagos", [])), Decimal(0))
        if amount(payload.get("expectedBalance")) != total - paid:
            raise CashError("El saldo cambió por otro abono. Actualiza la cuenta antes de continuar.")
    payments = payload.get("payments", [])
    if not isinstance(payments, list) or len(payments) > 20 or (action == "payment" and not payments):
        raise CashError("Agrega al menos un pago válido.")
    clean = []
    for payment in payments:
        if not isinstance(payment, dict) or payment.get("method") not in METHODS:
            raise CashError("Selecciona efectivo, tarjeta o transferencia.")
        value = amount(payment.get("amount"))
        if value <= 0:
            raise CashError("Cada pago debe ser mayor a cero.")
        reference = payment.get("reference", "")
        if not isinstance(reference, str) or len(reference) > 120:
            raise CashError("La referencia admite hasta 120 caracteres.")
        clean.append({"id": str(uuid.uuid4()), "fecha": stamp, "metodo": payment["method"], "monto": float(value),
                      "referencia": reference.strip(), "cajaId": box["id"], "userId": user["id"],
                      "registradoPor": (str(user.get("name", "")) + " " + str(user.get("last", ""))).strip()})
    paid_before = sum((amount(p["monto"]) for p in invoice.get("pagos", [])), Decimal(0))
    paid_now = sum((amount(p["monto"]) for p in clean), Decimal(0))
    if paid_before + paid_now > total:
        raise CashError("El pago supera el saldo pendiente. Registra solo el monto aplicado, sin incluir cambio.")
    invoice["pagos"].extend(clean)
    invoice["abonado"] = float(paid_before + paid_now)
    invoice["saldo"] = float(total - paid_before - paid_now)
    invoice["estadoPago"] = "Pagado" if invoice["saldo"] == 0 else "Abono" if invoice["abonado"] else "Pendiente"
    if not invoice.get("sri"):
        invoice["estado"] = invoice["estadoPago"]
    methods = list(dict.fromkeys(p["metodo"] for p in invoice["pagos"]))
    invoice["pago"] = methods[0] if len(methods) == 1 else "Mixto" if methods else "Pendiente"
    patient = next((p for p in (get_json_key(conn, "pacientes", []) or []) if p.get("id") == invoice["pac"]), {})
    for payment in clean:
        box.setdefault("movimientos", []).insert(0, {"id": payment["id"], "fecha": stamp[:10], "hora": stamp[11:16],
             "pacId": invoice["pac"], "pac": (patient.get("nombres", "") + " " + patient.get("apellidos", "")).strip(),
             "concepto": ("Abono · " if action == "payment" else "Cobro · ") + invoice["serv"],
             "monto": payment["monto"], "pago": payment["metodo"], "referencia": payment["referencia"],
             "factura": invoice["id"], "cobroVersion": 1})
    if action == "charge":
        set_json_key(conn, "nextIds", ids)
    set_json_key(conn, "facturas", invoices)
    set_json_key(conn, "cajas", boxes)
    conn.execute("insert into cash_requests(request_id,payload_hash,invoice_id,created_at) values(?,?,?,?)", (key, digest, invoice["id"], stamp))
    audit(conn, user, "cash_" + action, "facturas", {"invoiceId": invoice["id"], "received": float(paid_now), "balance": invoice["saldo"]})
    return {"ok": True, "invoice": invoice, "replayed": False}

def delete_movement(conn, user, payload):
    from medicg_app import get_json_key, set_json_key, audit
    if user.get('rol') != 'admin':
        raise CashError('Solo el administrador puede eliminar movimientos.')
    reason = payload.get('reason', '')
    if not isinstance(reason, str) or not 5 <= len(reason.strip()) <= 500:
        raise CashError('Indica el motivo de eliminación (5 a 500 caracteres).')
    boxes = get_json_key(conn, 'cajas', []) or []
    box = next((b for b in boxes if str(b.get('id')) == str(payload.get('boxId'))), None)
    index = payload.get('index')
    if not box or isinstance(index, bool) or not isinstance(index, int) or index < 0 or index >= len(box.get('movimientos', [])):
        raise CashError('El movimiento cambió. Actualiza caja.')
    movement = box['movimientos'][index]
    if movement != payload.get('base'):
        raise CashError('El movimiento cambió. Actualiza caja antes de eliminar.')
    invoices = get_json_key(conn, 'facturas', []) or []
    invoice = None
    if movement.get('factura'):
        invoice = next((f for f in invoices if f.get('id') == movement['factura']), None)
        if not invoice or invoice.get('cobroVersion') != 1:
            raise CashError('Este movimiento tiene un comprobante anterior vinculado. Debe revisarse antes de eliminarlo.')
        payments = invoice.get('pagos', [])
        matches = [p for p in payments if p.get('id') == movement.get('id')]
        if len(matches) != 1 or amount(matches[0]['monto']) != amount(movement['monto']):
            raise CashError('El pago vinculado no coincide. Revisa la cuenta antes de eliminar.')
        invoice['pagos'] = [p for p in payments if p.get('id') != movement['id']]
        paid = sum((amount(p['monto']) for p in invoice['pagos']), Decimal(0))
        invoice['abonado'] = float(paid)
        invoice['saldo'] = float(amount(invoice['total']) - paid)
        invoice['estadoPago'] = 'Pagado' if invoice['saldo'] == 0 else 'Abono' if paid else 'Pendiente'
        if not invoice.get('sri') and invoice.get('estado') != 'Anulado':
            invoice['estado'] = invoice['estadoPago']
        methods = list(dict.fromkeys(p['metodo'] for p in invoice['pagos']))
        invoice['pago'] = methods[0] if len(methods) == 1 else 'Mixto' if methods else 'Pendiente'
        set_json_key(conn, 'facturas', invoices)
    elif movement.get('cobroVersion') == 1:
        raise CashError('Falta la cuenta vinculada a este pago.')
    box['movimientos'].pop(index)
    set_json_key(conn, 'cajas', boxes)
    audit(conn, user, 'cash_delete_movement', 'cajas', {'boxId':box['id'], 'movement':movement, 'reason':reason.strip(), 'invoiceId':invoice['id'] if invoice else None})
    return {'ok': True}


CASH_STAFF = ("admin", "recepcion", "secretaria")


def _staff_name(user):
    return (str(user.get("name", "")) + " " + str(user.get("last", ""))).strip() or user.get("email", "")


def can_manage_box(user):
    from medicg_app import can_save_key
    return user.get("rol") in CASH_STAFF and can_save_key(user, "cajas")


def open_box(conn, user, payload):
    """Open the daily cash box (reception, secretary or administrator)."""
    from medicg_app import get_json_key, set_json_key, audit
    if not can_manage_box(user):
        raise CashError("No tienes permiso para abrir caja.")
    boxes = get_json_key(conn, "cajas", []) or []
    if any(c.get("estado") == "abierta" for c in boxes):
        raise CashError("Ya hay una caja abierta. Ciérrala antes de abrir otra.")
    opening = amount(payload.get("montoApertura") or 0)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))
    ids = get_json_key(conn, "nextIds", {}) or {}
    number = max(int(ids.get("caja") or 1), max((int(c.get("id") or 0) for c in boxes if str(c.get("id") or "").isdigit()), default=0) + 1)
    ids["caja"] = number + 1
    box = {"id": number, "fecha": stamp.date().isoformat(), "horaApertura": stamp.strftime("%H:%M"), "estado": "abierta",
           "cajero": _staff_name(user), "cajeroId": user.get("id"), "montoApertura": float(opening), "movimientos": []}
    boxes.append(box)
    set_json_key(conn, "nextIds", ids)
    set_json_key(conn, "cajas", boxes)
    audit(conn, user, "cash_open", "cajas", {"boxId": number, "montoApertura": float(opening)})
    return {"ok": True, "box": box}


EXPENSE_CATEGORIES = ("Proveedores", "Insumos médicos", "Laboratorio externo", "Honorarios médicos", "Sueldos y anticipos",
                      "Servicios básicos", "Movilización", "Alimentación", "Limpieza y mantenimiento", "Retiro del dueño", "Otros")
EXPENSE_METHODS = ("Efectivo", "Transferencia", "Tarjeta débito", "Tarjeta crédito")


def _text(payload, key, maxlen, label, required=False):
    value = payload.get(key, "")
    if value is None:
        value = ""
    if not isinstance(value, str) or len(value.strip()) > maxlen:
        raise CashError(f"{label}: máximo {maxlen} caracteres.")
    value = value.strip()
    if required and len(value) < 3:
        raise CashError(f"Indica {label.lower()}.")
    return value


def active_expenses(box):
    return [e for e in box.get("egresos", []) if e.get("estado") != "Anulado"]


def add_expense(conn, user, payload):
    """Cash paid out of the open box (supplier, transport, advances...). Cash expenses lower the expected cash."""
    from medicg_app import get_json_key, set_json_key, audit
    if not can_manage_box(user):
        raise CashError("No tienes permiso para registrar egresos de caja.")
    boxes = get_json_key(conn, "cajas", []) or []
    box = next((c for c in boxes if c.get("estado") == "abierta"), None)
    if not box:
        raise CashError("No hay una caja abierta.")
    if payload.get("boxId") is not None and str(payload.get("boxId")) != str(box.get("id")):
        raise CashError("La caja cambió. Actualiza la pantalla.")
    value = amount(payload.get("monto"))
    if value <= 0 or value > Decimal("100000"):
        raise CashError("Ingresa un monto mayor a cero.")
    concept = _text(payload, "concepto", 200, "El concepto del pago", required=True)
    category = payload.get("categoria") or "Otros"
    if category not in EXPENSE_CATEGORIES:
        raise CashError("Categoría de egreso inválida.")
    method = payload.get("metodo") or "Efectivo"
    if method not in EXPENSE_METHODS:
        raise CashError("Forma de pago del egreso inválida.")
    if method == "Efectivo":
        available = amount(box_summary(box)["efectivoEsperado"])
        if value > available:
            raise CashError(f"No hay suficiente efectivo en caja: disponible {available:.2f}.")
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))
    expense = {"id": str(uuid.uuid4()), "fecha": stamp.date().isoformat(), "hora": stamp.strftime("%H:%M"),
               "monto": float(value), "concepto": concept, "categoria": category, "metodo": method,
               "beneficiario": _text(payload, "beneficiario", 120, "El beneficiario"),
               "comprobante": _text(payload, "comprobante", 60, "El número de comprobante"),
               "registradoPor": _staff_name(user), "registradoPorId": user.get("id"), "estado": "Vigente"}
    box.setdefault("egresos", []).insert(0, expense)
    set_json_key(conn, "cajas", boxes)
    audit(conn, user, "cash_expense", "cajas", {"boxId": box["id"], "monto": expense["monto"], "concepto": concept, "metodo": method})
    return {"ok": True, "box": box, "expense": expense}


def void_expense(conn, user, payload):
    from medicg_app import get_json_key, set_json_key, audit
    if not can_manage_box(user):
        raise CashError("No tienes permiso para anular egresos.")
    boxes = get_json_key(conn, "cajas", []) or []
    box = next((c for c in boxes if c.get("estado") == "abierta" and str(c.get("id")) == str(payload.get("boxId"))), None)
    if not box:
        raise CashError("Solo se anulan egresos de la caja abierta.")
    expense = next((e for e in box.get("egresos", []) if e.get("id") == payload.get("id")), None)
    if not expense or expense.get("estado") == "Anulado":
        raise CashError("El egreso no existe o ya fue anulado.")
    if user.get("rol") != "admin" and str(expense.get("registradoPorId")) != str(user.get("id")):
        raise CashError("Solo quien registró el egreso o el administrador puede anularlo.")
    reason = _text(payload, "motivo", 300, "El motivo de anulación", required=True)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))
    expense.update(estado="Anulado", motivoAnulacion=reason, anuladoPor=_staff_name(user), anuladoEn=stamp.isoformat(timespec="seconds"))
    set_json_key(conn, "cajas", boxes)
    audit(conn, user, "cash_expense_void", "cajas", {"boxId": box["id"], "expense": expense["id"], "monto": expense["monto"], "motivo": reason})
    return {"ok": True, "box": box}


def box_summary(box):
    movements = [m for m in box.get("movimientos", []) if m.get("pago") != "Pendiente"]
    def total(rule):
        return float(sum((amount(m.get("monto") or 0) for m in movements if rule(str(m.get("pago") or ""))), Decimal(0)))
    totals = {
        "Efectivo": total(lambda p: p == "Efectivo"),
        "Tarjeta débito": total(lambda p: p == "Tarjeta débito"),
        "Tarjeta crédito": total(lambda p: p == "Tarjeta crédito" or p == "Tarjeta"),
        "Transferencia": total(lambda p: p == "Transferencia"),
        "Otros": total(lambda p: p not in ("Efectivo", "Tarjeta débito", "Tarjeta crédito", "Tarjeta", "Transferencia")),
    }
    received = float(sum((amount(v) for v in totals.values()), Decimal(0)))
    expenses = active_expenses(box)
    cash_out = sum((amount(e.get("monto")) for e in expenses if e.get("metodo", "Efectivo") == "Efectivo"), Decimal(0))
    other_out = sum((amount(e.get("monto")) for e in expenses if e.get("metodo", "Efectivo") != "Efectivo"), Decimal(0))
    expected_cash = float(amount(box.get("montoApertura") or 0) + amount(totals["Efectivo"]) - cash_out)
    return {"totales": totals, "totalRecibido": received, "efectivoEsperado": expected_cash, "movimientos": len(movements),
            "egresosEfectivo": float(cash_out), "egresosOtros": float(other_out), "totalEgresos": float(cash_out + other_out),
            "egresos": [{k: e.get(k) for k in ("hora", "monto", "concepto", "categoria", "metodo", "beneficiario", "comprobante", "registradoPor")} for e in expenses],
            "netoDelDia": float(amount(received) - cash_out - other_out)}


def close_box(conn, user, payload):
    """Daily close with cash count (arqueo). The summary is stored and can't be edited later."""
    from medicg_app import get_json_key, set_json_key, audit
    if not can_manage_box(user):
        raise CashError("No tienes permiso para cerrar caja.")
    boxes = get_json_key(conn, "cajas", []) or []
    box = next((c for c in boxes if c.get("estado") == "abierta"), None)
    if not box:
        raise CashError("No hay una caja abierta.")
    if str(payload.get("boxId")) != str(box.get("id")):
        raise CashError("La caja cambió. Actualiza la pantalla antes de cerrar.")
    summary = box_summary(box)
    if amount(payload.get("expectedTotal")) != amount(summary["totalRecibido"]):
        raise CashError("Se registraron nuevos pagos. Revisa el resumen actualizado antes de cerrar.")
    if payload.get("expectedCash") is not None and amount(payload.get("expectedCash")) != amount(summary["efectivoEsperado"]):
        raise CashError("Se registraron o anularon egresos. Revisa el resumen actualizado antes de cerrar.")
    counted = amount(payload.get("efectivoContado"))
    notes = payload.get("observaciones", "")
    if not isinstance(notes, str) or len(notes) > 1000:
        raise CashError("Las observaciones admiten hasta 1000 caracteres.")
    difference = counted - amount(summary["efectivoEsperado"])
    if difference != 0 and len(notes.strip()) < 5:
        raise CashError("Hay diferencia en el efectivo: explica el motivo en observaciones.")
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5)))
    box["cierre"] = {**summary, "montoApertura": float(amount(box.get("montoApertura") or 0)),
                     "efectivoContado": float(counted), "diferencia": float(difference),
                     "observaciones": notes.strip(), "fecha": stamp.date().isoformat(), "hora": stamp.strftime("%H:%M"),
                     "cerradoPor": _staff_name(user), "cerradoPorId": user.get("id")}
    box.update(estado="cerrada", horaCierre=stamp.strftime("%H:%M"), fechaCierre=stamp.date().isoformat(), cerradoPor=_staff_name(user))
    set_json_key(conn, "cajas", boxes)
    audit(conn, user, "cash_close", "cajas", {"boxId": box["id"], "totalRecibido": summary["totalRecibido"], "diferencia": float(difference)})
    return {"ok": True, "box": box}


def clean_payments(payments, user, box, stamp):
    if not isinstance(payments, list) or len(payments) > 20:
        raise CashError("Revisa las formas de pago.")
    clean = []
    for payment in payments:
        if not isinstance(payment, dict) or payment.get("method") not in METHODS:
            raise CashError("Selecciona efectivo, tarjeta o transferencia.")
        value = amount(payment.get("amount"))
        if value <= 0:
            raise CashError("Cada pago debe ser mayor a cero.")
        reference = payment.get("reference", "")
        if not isinstance(reference, str) or len(reference) > 120:
            raise CashError("La referencia admite hasta 120 caracteres.")
        clean.append({"id": str(uuid.uuid4()), "fecha": stamp, "metodo": payment["method"], "monto": float(value),
                      "referencia": reference.strip(), "cajaId": box["id"] if box else None, "userId": user["id"],
                      "registradoPor": (str(user.get("name", "")) + " " + str(user.get("last", ""))).strip()})
    return clean


def create_account(conn, user, patient, items, payments, concept, esp="Farmacia"):
    """Create a patient account (cobroVersion 1) with per-line VAT and optional payments.

    ``items`` need nombre, cantidad, unit (net unit price), ivaRate and may carry kind/id/codigo.
    Payments go to the open cash box; without payments the balance stays pending in Caja.
    """
    from medicg_app import get_json_key, set_json_key
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).isoformat(timespec="seconds")
    invoices = get_json_key(conn, "facturas", []) or []
    boxes = get_json_key(conn, "cajas", []) or []
    box = next((c for c in boxes if c.get("estado") == "abierta"), None)
    lines, subtotal, tax = [], Decimal(0), Decimal(0)
    for item in items:
        quantity = Decimal(str(item["cantidad"]))
        unit = amount(item["unit"])
        base = amount(unit * quantity)
        rate = Decimal(str(item.get("ivaRate") or 0))
        line_tax = amount(base * rate / 100)
        subtotal += base
        tax += line_tax
        lines.append({**item, "desc": item["nombre"], "cant": float(quantity), "unit": float(unit), "total": float(base),
                      "ivaRate": float(rate), "iva": float(line_tax), "precioNeto": float(unit)})
    total = amount(subtotal + tax)
    if total <= 0:
        raise CashError("El total debe ser mayor a cero.")
    clean = clean_payments(payments or [], user, box, stamp)
    if clean and not box:
        raise CashError("Abre caja antes de registrar pagos. También puedes dejar la cuenta pendiente.")
    paid = sum((amount(p["monto"]) for p in clean), Decimal(0))
    if paid > total:
        raise CashError("El pago supera el total. Registra solo el monto aplicado, sin incluir cambio.")
    ids = get_json_key(conn, "nextIds", {}) or {}
    number = max(int(ids.get("fac") or 1), max((int(str(f.get("id", "")).split("-")[-1]) for f in invoices if re.fullmatch(r"\d{3}-\d{3}-\d{9}", str(f.get("id", "")))), default=0) + 1)
    ids["fac"] = number + 1
    rates = {l["ivaRate"] for l in lines}
    cfg = get_json_key(conn, "config", {}) or {}
    prefix = str(cfg.get("sriEstab") or "001").zfill(3)[-3:] + "-" + str(cfg.get("sriPtoEmi") or "001").zfill(3)[-3:] + "-"
    invoice = {"id": prefix + str(number).zfill(9), "fecha": stamp[:10], "createdAt": stamp, "pac": patient["id"], "esp": esp,
               "serv": "; ".join(f"{l['cant']:g} × {l['nombre']}" for l in lines), "items": lines,
               "sub": float(amount(subtotal)), "iva": float(amount(tax)), "ivaRate": float(rates.pop()) if len(rates) == 1 else None,
               "total": float(total), "cobroVersion": 1, "pagos": clean, "abonado": float(paid), "saldo": float(total - paid)}
    invoice["estadoPago"] = "Pagado" if invoice["saldo"] == 0 else "Abono" if paid else "Pendiente"
    invoice["estado"] = invoice["estadoPago"]
    methods = list(dict.fromkeys(p["metodo"] for p in clean))
    invoice["pago"] = methods[0] if len(methods) == 1 else "Mixto" if methods else "Pendiente"
    invoices.insert(0, invoice)
    name = (patient.get("nombres", "") + " " + patient.get("apellidos", "")).strip()
    for payment in clean:
        box.setdefault("movimientos", []).insert(0, {"id": payment["id"], "fecha": stamp[:10], "hora": stamp[11:16], "pacId": patient["id"],
                                                     "pac": name, "concepto": concept + " · " + invoice["serv"], "monto": payment["monto"],
                                                     "pago": payment["metodo"], "referencia": payment["referencia"], "factura": invoice["id"], "cobroVersion": 1})
    set_json_key(conn, "nextIds", ids)
    set_json_key(conn, "facturas", invoices)
    if clean:
        set_json_key(conn, "cajas", boxes)
    return invoice
