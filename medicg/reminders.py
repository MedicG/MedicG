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
MAX_PER_RUN = 6
TIME_BUDGET_SECONDS = 7  # stay well inside the serverless function time limit
WINDOW_24H = 36  # hours: the 07:00 daily run covers every appointment of the next day
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
    try:
        delta = (dt.date.fromisoformat(str(cita.get("fecha"))) - now().date()).days
    except ValueError:
        delta = None
    relative = {0: "de hoy", 1: "de mañana"}.get(delta, "")
    intro = "su cita quedó agendada" if kind == "confirmacion" else ("le recordamos su cita " + relative).strip()
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


HANDLED = ("sent", "manual", "sending")


def already_sent(conn, cita_id, channel, kind, slot):
    """True when the message was sent, sent by hand, or reserved by a run that may have sent it."""
    marks = ",".join("?" for _ in HANDLED)
    row = conn.execute(f"select id from reminder_log where cita_id = ? and channel = ? and kind = ? and slot = ? and status in ({marks})",
                       (str(cita_id), channel, kind, slot, *HANDLED)).fetchone()
    return bool(row)


def log(conn, cita_id, channel, kind, slot, status, detail="", user_name="Sistema", entry_id=None):
    entry_id = entry_id or str(uuid.uuid4())
    conn.execute("insert into reminder_log(id,cita_id,channel,kind,slot,status,detail,ts,user_name) values(?,?,?,?,?,?,?,?,?)",
                 (entry_id, str(cita_id), channel, kind, slot, status, str(detail)[:500], now().isoformat(timespec="seconds"), user_name))
    return entry_id


def finish(entry_id, status, detail):
    from medicg_app import db
    with db(lock=None) as conn:
        conn.execute("update reminder_log set status = ?, detail = ?, ts = ? where id = ?",
                     (status, str(detail)[:500], now().isoformat(timespec="seconds"), entry_id))


def prepare(conn, cita, channel, kind):
    """Build the message (inside a transaction). Network sending happens later, outside it."""
    patient, doctor, cfg = context(conn, cita)
    text, params = message(cita, patient, doctor, cfg, kind)
    job = {"cita_id": cita["id"], "channel": channel, "kind": kind, "slot": f"{cita.get('fecha')} {cita.get('hora')}", "text": text, "params": params}
    if channel == "email":
        job["address"] = (patient.get("email") or "").strip()
        job["subject"] = ("Cita agendada" if kind == "confirmacion" else "Recordatorio de cita") + f" · {long_date(cita.get('fecha'))} {cita.get('hora')}"
        job["html"] = email_html(text, cfg)
        if not job["address"]:
            job["skip"] = "El paciente no tiene correo registrado."
    else:
        job["phone"] = phone_e164(patient.get("tel"))
        if not job["phone"]:
            job["skip"] = "El paciente no tiene un celular válido."
        else:
            job["link"] = "https://wa.me/" + job["phone"] + "?text=" + urllib.parse.quote(text)
    return job


def execute(job, mail_cfg, rem_cfg):
    """Send one prepared message. Returns (status, detail). No database access."""
    from medicg.mailer import send as send_mail
    if job["channel"] == "email":
        ok, error = send_mail(job["address"], job["subject"], job["text"], job["html"], config=mail_cfg, conn=None)
        return ("sent", f"Enviado a {job['address']}") if ok else ("error", error or "No se pudo enviar el correo.")
    ok, detail = send_whatsapp_cloud(rem_cfg, job["phone"], job["params"])
    return ("sent", "Enviado por WhatsApp Business") if ok else ("error", detail)


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
        window = WINDOW_24H if lead == 24 else 2.5
        if hours <= window and (lead == 2 or hours > 2.5 or 2 not in leads):
            for channel in channels:
                result.append((channel, f"{lead}h"))
    return result


def run(conn=None, force=False):
    """Send due automatic reminders (e-mail always; WhatsApp only with Business API).

    1) a short transaction reserves the due messages ("sending"), 2) messages are sent
    outside any transaction within a time budget, 3) each result is recorded at once.
    A message reserved by a run that was interrupted is never sent twice.
    """
    from medicg_app import db, get_json_key, set_json_key
    from medicg.mailer import settings as mail_settings
    started = time.time()
    with db(lock="reminders") as tx:
        cfg = settings(tx)
        if not cfg["enabled"]:
            return {"ok": True, "sent": 0, "disabled": True}
        if not force and time.time() - float(cfg.get("lastRun") or 0) < RUN_INTERVAL_SECONDS:
            return {"ok": True, "sent": 0, "throttled": True}
        raw = get_json_key(tx, "remindersPrivate", {}) or {}
        raw["lastRun"] = time.time()
        set_json_key(tx, "remindersPrivate", raw)
        current = now()
        mail_cfg = mail_settings(tx)
        jobs, more = [], False
        for cita in get_json_key(tx, "citas", []) or []:
            for channel, kind in due(cita, current):
                if channel == "whatsapp" and not whatsapp_ready(cfg):
                    continue
                slot = f"{cita.get('fecha')} {cita.get('hora')}"
                if already_sent(tx, cita["id"], channel, kind, slot):
                    continue
                recent_error = tx.execute("select ts from reminder_log where cita_id = ? and channel = ? and kind = ? and slot = ? and status in ('error','skipped') order by ts desc limit 1",
                                          (str(cita["id"]), channel, kind, slot)).fetchone()
                if recent_error and (current - dt.datetime.fromisoformat(recent_error["ts"])).total_seconds() < 1800:
                    continue
                if len(jobs) >= MAX_PER_RUN:
                    more = True
                    continue
                job = prepare(tx, cita, channel, kind)
                if job.get("skip"):
                    log(tx, cita["id"], channel, kind, slot, "skipped", job["skip"])
                    continue
                job["entry"] = log(tx, cita["id"], channel, kind, slot, "sending", "Reservado para envío")
                jobs.append(job)
    sent, errors = 0, []
    for index, job in enumerate(jobs):
        if time.time() - started > TIME_BUDGET_SECONDS:
            # Release what was not attempted so the next run picks it up.
            with db(lock=None) as tx:
                for pending in jobs[index:]:
                    tx.execute("delete from reminder_log where id = ? and status = 'sending'", (pending["entry"],))
            more = True
            break
        try:
            status_, detail = execute(job, mail_cfg, cfg)
        except Exception:
            status_, detail = "error", "Error inesperado al enviar."
        finish(job["entry"], status_, detail)
        if status_ == "sent":
            sent += 1
        else:
            errors.append({"cita": job["cita_id"], "channel": job["channel"], "detail": detail})
    result = {"ok": True, "sent": sent, "errors": errors}
    if more:
        result["more"] = True
    return result


def send_now(conn, user, payload):
    """Manual send from the agenda. ``conn`` is ignored; short transactions are used internally."""
    from medicg_app import db, get_json_key, can_save_key, user_display_name
    from medicg.mailer import settings as mail_settings
    if not can_save_key(user, "citas"):
        raise ReminderError("No tienes permiso para enviar recordatorios.")
    channels = payload.get("channels") or [payload.get("channel")]
    if any(channel not in ("email", "whatsapp") for channel in channels):
        raise ReminderError("Canal inválido.")
    kind = payload.get("kind") if payload.get("kind") in ("confirmacion", "manual") else "manual"
    name = user_display_name(user)
    with db(read_only=True) as tx:
        cita = next((c for c in get_json_key(tx, "citas", []) or [] if str(c.get("id")) == str(payload.get("citaId"))), None)
        if not cita:
            raise ReminderError("Cita no encontrada.")
        rem_cfg, mail_cfg = settings(tx), mail_settings(tx)
        jobs = [prepare(tx, cita, channel, kind) for channel in channels]
    results = {}
    for job in jobs:
        if job.get("skip"):
            outcome = {"status": "skipped", "detail": job["skip"]}
        elif job["channel"] == "whatsapp" and not whatsapp_ready(rem_cfg):
            results["whatsapp"] = {"status": "pending_manual", "detail": "Abre WhatsApp para enviar el mensaje preparado.", "waLink": job["link"]}
            continue
        else:
            status_, detail = execute(job, mail_cfg, rem_cfg)
            outcome = {"status": status_, "detail": detail, "waLink": job.get("link") if status_ == "error" else None}
        with db(lock=None) as tx:
            log(tx, job["cita_id"], job["channel"], kind, job["slot"], outcome["status"], outcome["detail"], name)
        results[job["channel"]] = outcome
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
