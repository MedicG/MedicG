"""Appointment confirmations and reminders by e-mail and WhatsApp.

- E-mail goes through the configured outgoing mail (Gmail/Outlook/SMTP/Resend).
- WhatsApp: with WhatsApp Business Cloud API credentials (Meta) messages are sent
  automatically using an approved template; otherwise the system prepares a
  wa.me link so reception sends the prepared message with one click.
- Every attempt is stored in reminder_log; a message is never sent twice for the
  same appointment, channel, reminder type and date/time.
- Due reminders are processed by /api/reminders/run (called every few minutes while
  staff use the app) and by a daily Vercel cron.
"""
import datetime as dt
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

TZ = dt.timezone(dt.timedelta(hours=-5))
ACTIVE_STATES = {"pendiente", "confirmada", "solicitada online", "pospuesta"}
MAX_PER_RUN = 12
RUN_INTERVAL_SECONDS = 240
DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
NOTIF_OPTIONS = (
    "WhatsApp + Correo (24h antes)",
    "WhatsApp + Correo (24h y 2h antes)",
    "Solo WhatsApp (24h antes)",
    "Solo WhatsApp (2h antes)",
    "Solo correo (24h antes)",
    "Solo correo",
    "Sin recordatorio",
)


class ReminderError(ValueError):
    pass


def now():
    return dt.datetime.now(TZ)


def table_sql():
    return ("create table if not exists reminder_log(id text primary key, cita_id text not null, channel text not null, "
            "kind text not null, slot text not null, status text not null, detail text, ts text not null, user_name text)")


def norm(value):
    import unicodedata
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().strip().lower()


def plan(notif):
    """Channels and lead times (hours) from the appointment's reminder option."""
    text = norm(notif)
    if not text or "sin recordatorio" in text:
        return set(), []
    channels = set()
    if "whatsapp" in text:
        channels.add("whatsapp")
    if "correo" in text or "email" in text:
        channels.add("email")
    leads = []
    if "24" in text:
        leads.append(24)
    if re.search(r"\b2\s*h", text):
        leads.append(2)
    if not leads:
        leads = [24]
    return channels, leads


def settings(conn):
    from medicg_app import get_json_key
    cfg = get_json_key(conn, "remindersPrivate", {}) or {}
    return {"enabled": cfg.get("enabled", True), "whatsappMode": cfg.get("whatsappMode", "manual"),
            "phoneNumberId": cfg.get("phoneNumberId", ""), "token": cfg.get("token", ""),
            "templateName": cfg.get("templateName", ""), "templateLang": cfg.get("templateLang", "es"),
            "lastRun": cfg.get("lastRun", 0)}


def public_settings(conn):
    cfg = settings(conn)
    from medicg.mailer import public_settings as mail_public
    mail = mail_public(conn)
    return {"enabled": cfg["enabled"], "whatsappMode": cfg["whatsappMode"], "phoneNumberId": cfg["phoneNumberId"],
            "templateName": cfg["templateName"], "templateLang": cfg["templateLang"], "hasToken": bool(cfg["token"]),
            "whatsappAutomatic": whatsapp_ready(cfg), "emailConfigured": bool(mail.get("configured")), "emailFrom": mail.get("from", "")}


def save_settings(conn, user, payload):
    from medicg_app import set_json_key, audit
    if user.get("rol") != "admin":
        raise ReminderError("Solo el administrador configura los recordatorios.")
    current = settings(conn)
    mode = payload.get("whatsappMode", "manual")
    if mode not in ("manual", "cloud"):
        raise ReminderError("Modo de WhatsApp inválido.")
    cfg = {"enabled": bool(payload.get("enabled", True)), "whatsappMode": mode, "lastRun": current["lastRun"],
           "phoneNumberId": str(payload.get("phoneNumberId") or "").strip(), "templateName": str(payload.get("templateName") or "").strip(),
           "templateLang": str(payload.get("templateLang") or "es").strip() or "es",
           "token": str(payload.get("token") or "").strip() or current["token"]}
    if mode == "cloud":
        if not re.fullmatch(r"\d{6,30}", cfg["phoneNumberId"]):
            raise ReminderError("Ingresa el Phone Number ID de WhatsApp Business (solo números).")
        if not cfg["token"]:
            raise ReminderError("Ingresa el token de acceso de WhatsApp Business.")
        if not re.fullmatch(r"[a-z0-9_]{1,512}", cfg["templateName"]):
            raise ReminderError("Ingresa el nombre de la plantilla aprobada (minúsculas, números y guion bajo).")
    set_json_key(conn, "remindersPrivate", cfg)
    audit(conn, user, "reminder_settings_saved", "remindersPrivate", {"whatsappMode": mode, "enabled": cfg["enabled"]})
    return public_settings(conn)


def whatsapp_ready(cfg):
    return cfg.get("whatsappMode") == "cloud" and bool(cfg.get("phoneNumberId") and cfg.get("token") and cfg.get("templateName"))


def phone_e164(value):
    """Ecuador-friendly normalisation: 0991234567 -> 593991234567."""
    digits = re.sub(r"\D", "", str(value or ""))
    if digits.startswith("00"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 10:
        digits = "593" + digits[1:]
    elif len(digits) == 9 and digits.startswith("9"):
        digits = "593" + digits
    return digits if 10 <= len(digits) <= 15 else ""


def long_date(value):
    try:
        day = dt.date.fromisoformat(str(value))
    except ValueError:
        return str(value)
    return f"{DAYS[day.weekday()]} {day.day} de {MONTHS[day.month - 1]} de {day.year}"


def context(conn, cita):
    from medicg_app import get_json_key
    patient = next((p for p in get_json_key(conn, "pacientes", []) or [] if str(p.get("id")) == str(cita.get("pac"))), {}) or {}
    doctor = next((m for m in get_json_key(conn, "medicos", []) or [] if str(m.get("id")) == str(cita.get("med"))), {}) or {}
    cfg = get_json_key(conn, "config", {}) or {}
    return patient, doctor, cfg


def message(cita, patient, doctor, cfg, kind):
    name = (patient.get("nombres") or "").split(" ")[0].title() or "paciente"
    center = cfg.get("nombre") or "nuestro centro médico"
    online = cita.get("modalidad") == "online"
    when = f"{long_date(cita.get('fecha'))} a las {cita.get('hora')}"
    doctor_name = doctor.get("nombre") or "su médico"
    intro = {"confirmacion": "su cita quedó agendada", "manual": "le recordamos su cita", "24h": "le recordamos su cita de mañana", "2h": "le recordamos su cita de hoy"}.get(kind, "le recordamos su cita")
    lines = [f"Hola {name}, {intro} en {center}:", f"📅 {when}", f"👩‍⚕️ {doctor_name} · {cita.get('esp') or ''}".strip(" ·")]
    if online:
        lines.append("💻 Consulta en línea: ingrese al portal del paciente 30 minutos antes.")
    elif cfg.get("dir"):
        lines.append(f"📍 {cfg.get('dir')}")
    contact = cfg.get("wa") or cfg.get("tel")
    lines.append("Si no puede asistir, por favor avísenos" + (f" al {contact}" if contact else "") + ". ¡Gracias!")
    return "\n".join(lines), {"paciente": name, "fecha": long_date(cita.get("fecha")), "hora": str(cita.get("hora")), "medico": doctor_name, "centro": center}


def email_html(text, cfg):
    from html import escape
    body = "<br>".join(escape(line) for line in text.split("\n"))
    color = cfg.get("color") or "#0d7a6b"
    return (f"<div style='font-family:Arial,sans-serif;max-width:560px;margin:auto;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden'>"
            f"<div style='background:{escape(color)};color:#fff;padding:14px 18px;font-weight:bold'>{escape(cfg.get('nombre') or 'Centro médico')}</div>"
            f"<div style='padding:18px;font-size:15px;line-height:1.6;color:#111'>{body}</div>"
            f"<div style='padding:10px 18px;font-size:12px;color:#6b7280;background:#f9fafb'>Mensaje automático de recordatorio de cita.</div></div>")


def send_whatsapp_cloud(cfg, phone, params):
    url = f"https://graph.facebook.com/v20.0/{urllib.parse.quote(cfg['phoneNumberId'])}/messages"
    body = {"messaging_product": "whatsapp", "to": phone, "type": "template",
            "template": {"name": cfg["templateName"], "language": {"code": cfg.get("templateLang") or "es"},
                         "components": [{"type": "body", "parameters": [{"type": "text", "text": params[k][:200]} for k in ("paciente", "fecha", "hora", "medico", "centro")]}]}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": "Bearer " + cfg["token"], "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.load(response)
            return True, (data.get("messages") or [{}])[0].get("id", "")
    except urllib.error.HTTPError as exc:
        try:
            detail = json.load(exc).get("error", {}).get("message", "")
        except Exception:
            detail = ""
        return False, f"WhatsApp rechazó el envío (HTTP {exc.code}). {detail}".strip()
    except Exception:
        return False, "No se pudo conectar con WhatsApp Business."


def already_sent(conn, cita_id, channel, kind, slot):
    row = conn.execute("select id from reminder_log where cita_id = ? and channel = ? and kind = ? and slot = ? and status in ('sent','manual')",
                       (str(cita_id), channel, kind, slot)).fetchone()
    return bool(row)


def log(conn, cita_id, channel, kind, slot, status, detail="", user_name="Sistema"):
    conn.execute("insert into reminder_log(id,cita_id,channel,kind,slot,status,detail,ts,user_name) values(?,?,?,?,?,?,?,?,?)",
                 (str(uuid.uuid4()), str(cita_id), channel, kind, slot, status, str(detail)[:500], now().isoformat(timespec="seconds"), user_name))


def deliver(conn, cita, channel, kind, user_name="Sistema", mail_cfg=None, rem_cfg=None):
    """Send one message. Returns dict with status sent/manual/skipped/error and optional waLink."""
    from medicg.mailer import send as send_mail, settings as mail_settings
    patient, doctor, cfg = context(conn, cita)
    slot = f"{cita.get('fecha')} {cita.get('hora')}"
    text, params = message(cita, patient, doctor, cfg, kind)
    rem_cfg = rem_cfg or settings(conn)
    if channel == "email":
        address = (patient.get("email") or "").strip()
        if not address:
            log(conn, cita["id"], channel, kind, slot, "skipped", "El paciente no tiene correo.", user_name)
            return {"status": "skipped", "detail": "El paciente no tiene correo registrado."}
        subject = ("Cita agendada" if kind == "confirmacion" else "Recordatorio de cita") + f" · {long_date(cita.get('fecha'))} {cita.get('hora')}"
        ok, error = send_mail(address, subject, text, email_html(text, cfg), config=mail_cfg or mail_settings(conn), conn=None)
        log(conn, cita["id"], channel, kind, slot, "sent" if ok else "error", error or address, user_name)
        return {"status": "sent" if ok else "error", "detail": error or f"Enviado a {address}"}
    phone = phone_e164(patient.get("tel"))
    if not phone:
        log(conn, cita["id"], channel, kind, slot, "skipped", "Teléfono inválido o vacío.", user_name)
        return {"status": "skipped", "detail": "El paciente no tiene un celular válido."}
    link = "https://wa.me/" + phone + "?text=" + urllib.parse.quote(text)
    if whatsapp_ready(rem_cfg):
        ok, detail = send_whatsapp_cloud(rem_cfg, phone, params)
        log(conn, cita["id"], channel, kind, slot, "sent" if ok else "error", detail, user_name)
        return {"status": "sent" if ok else "error", "detail": detail if not ok else "Enviado por WhatsApp Business", "waLink": None if ok else link}
    return {"status": "pending_manual", "detail": "Abre WhatsApp para enviar el mensaje preparado.", "waLink": link}


def due(cita, current):
    """(channel, kind) pairs due now for an appointment."""
    if norm(cita.get("estado")) not in ACTIVE_STATES:
        return []
    try:
        start = dt.datetime.fromisoformat(f"{cita['fecha']}T{cita['hora']}").replace(tzinfo=TZ)
    except (KeyError, ValueError, TypeError):
        return []
    hours = (start - current).total_seconds() / 3600
    if hours <= 0:
        return []
    channels, leads = plan(cita.get("notif"))
    result = []
    for lead in leads:
        window = 26 if lead == 24 else 2.5
        if hours <= window and (lead == 2 or hours > 2.5 or 2 not in leads):
            for channel in channels:
                result.append((channel, f"{lead}h"))
    return result


def run(conn, force=False):
    """Send due automatic reminders (e-mail always; WhatsApp only with Business API)."""
    from medicg_app import get_json_key, set_json_key
    from medicg.mailer import settings as mail_settings
    cfg = settings(conn)
    if not cfg["enabled"]:
        return {"ok": True, "sent": 0, "disabled": True}
    if not force and time.time() - float(cfg.get("lastRun") or 0) < RUN_INTERVAL_SECONDS:
        return {"ok": True, "sent": 0, "throttled": True}
    raw = get_json_key(conn, "remindersPrivate", {}) or {}
    raw["lastRun"] = time.time()
    set_json_key(conn, "remindersPrivate", raw)
    current = now()
    mail_cfg = mail_settings(conn)
    sent, errors, attempts = 0, [], 0
    for cita in get_json_key(conn, "citas", []) or []:
        for channel, kind in due(cita, current):
            if channel == "whatsapp" and not whatsapp_ready(cfg):
                continue
            slot = f"{cita.get('fecha')} {cita.get('hora')}"
            if already_sent(conn, cita["id"], channel, kind, slot):
                continue
            recent_error = conn.execute("select ts from reminder_log where cita_id = ? and channel = ? and kind = ? and slot = ? and status = 'error' order by ts desc limit 1",
                                        (str(cita["id"]), channel, kind, slot)).fetchone()
            if recent_error and (current - dt.datetime.fromisoformat(recent_error["ts"])).total_seconds() < 1800:
                continue
            if attempts >= MAX_PER_RUN:
                return {"ok": True, "sent": sent, "errors": errors, "more": True}
            attempts += 1
            result = deliver(conn, cita, channel, kind, mail_cfg=mail_cfg, rem_cfg=cfg)
            if result["status"] == "sent":
                sent += 1
            elif result["status"] == "error":
                errors.append({"cita": cita["id"], "channel": channel, "detail": result["detail"]})
    return {"ok": True, "sent": sent, "errors": errors}


def send_now(conn, user, payload):
    from medicg_app import get_json_key, can_save_key, user_display_name
    if not can_save_key(user, "citas"):
        raise ReminderError("No tienes permiso para enviar recordatorios.")
    cita = next((c for c in get_json_key(conn, "citas", []) or [] if str(c.get("id")) == str(payload.get("citaId"))), None)
    if not cita:
        raise ReminderError("Cita no encontrada.")
    channels = payload.get("channels") or [payload.get("channel")]
    kind = payload.get("kind") if payload.get("kind") in ("confirmacion", "manual") else "manual"
    results = {}
    for channel in channels:
        if channel not in ("email", "whatsapp"):
            raise ReminderError("Canal inválido.")
        results[channel] = deliver(conn, cita, channel, kind, user_display_name(user))
    return {"ok": True, "results": results}


def mark_manual(conn, user, payload):
    from medicg_app import get_json_key, can_save_key, user_display_name
    if not can_save_key(user, "citas"):
        raise ReminderError("No tienes permiso.")
    cita = next((c for c in get_json_key(conn, "citas", []) or [] if str(c.get("id")) == str(payload.get("citaId"))), None)
    if not cita:
        raise ReminderError("Cita no encontrada.")
    kind = payload.get("kind") if payload.get("kind") in ("confirmacion", "manual", "24h", "2h") else "manual"
    log(conn, cita["id"], "whatsapp", kind, f"{cita.get('fecha')} {cita.get('hora')}", "manual", "Enviado desde WhatsApp por el usuario", user_display_name(user))
    return {"ok": True}


def status(conn, cita_ids):
    if not cita_ids:
        return {}
    marks = ",".join("?" for _ in cita_ids)
    rows = conn.execute(f"select cita_id, channel, kind, slot, status, detail, ts, user_name from reminder_log where cita_id in ({marks}) order by ts", tuple(str(i) for i in cita_ids)).fetchall()
    result = {}
    for row in rows:
        result.setdefault(row["cita_id"], []).append({k: row[k] for k in ("channel", "kind", "slot", "status", "detail", "ts", "user_name")})
    return result
