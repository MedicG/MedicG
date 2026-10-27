"""Clinical file contents live in their own table, not inside the JSON blob.

Previously every uploaded document (up to 8 MB, base64) was embedded in the
``archivosClinicos`` JSON. Each page load downloaded every file of every
patient, and each new upload resent all of them, so once the total passed the
12 MB request limit no more files could be uploaded at all.

Now only metadata stays in ``archivosClinicos`` (with ``hasFile: true``); the
content is stored once in ``clinical_files`` and downloaded only when
someone opens it.
"""
import time

HEAVY_INVOICE_FIELDS = ("xml", "signedXml", "authorizedXml", "sriRecepcion", "sriAutorizacion", "sriSendingAt", "emailSendingAt")


def table_sql():
    return (
        "create table if not exists clinical_files("
        "file_key text primary key, patient_id text not null, file_id text not null, "
        "mime text, size integer, data_url text not null, created_at double precision not null)"
    )


def file_key(patient_id, file_id):
    return f"{patient_id}:{file_id}"


def strip_entry(entry):
    if not isinstance(entry, dict):
        return entry
    if "dataUrl" not in entry:
        return entry
    result = {k: v for k, v in entry.items() if k != "dataUrl"}
    if entry.get("dataUrl"):
        result["hasFile"] = True
    return result


def strip_map(files):
    """Return archivosClinicos without embedded contents (for comparisons and reads)."""
    if not isinstance(files, dict):
        return files
    return {pid: [strip_entry(e) for e in (entries or [])] if isinstance(entries, list) else entries
            for pid, entries in files.items()}


def extract_contents(conn, files):
    """Store any embedded dataUrl in clinical_files and return the stripped map."""
    if not isinstance(files, dict):
        return files
    now = time.time()
    for pid, entries in files.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            data_url = entry.get("dataUrl")
            if isinstance(data_url, str) and data_url.startswith("data:"):
                key = file_key(pid, entry.get("id"))
                conn.execute(
                    "insert into clinical_files(file_key,patient_id,file_id,mime,size,data_url,created_at) values(?,?,?,?,?,?,?) "
                    "on conflict(file_key) do update set data_url=excluded.data_url, mime=excluded.mime, size=excluded.size",
                    (key, str(pid), str(entry.get("id")), str(entry.get("mime") or ""), int(entry.get("size") or 0), data_url, now),
                )
    return strip_map(files)


def load_content(conn, patient_id, file_id):
    row = conn.execute("select data_url, mime from clinical_files where file_key = ?", (file_key(patient_id, file_id),)).fetchone()
    return (row["data_url"], row["mime"]) if row else (None, None)


def strip_invoice(invoice):
    if not isinstance(invoice, dict):
        return invoice
    return {k: v for k, v in invoice.items() if k not in HEAVY_INVOICE_FIELDS}


def strip_invoices(invoices):
    if not isinstance(invoices, list):
        return invoices
    return [strip_invoice(f) for f in invoices]


def restore_invoice_fields(current, value):
    """Keep server-only XML/SRI payloads for invoices saved from the browser."""
    if not isinstance(value, list):
        return value
    previous = {str(f.get("id")): f for f in (current or []) if isinstance(f, dict)}
    restored = []
    for invoice in value:
        if isinstance(invoice, dict):
            original = previous.get(str(invoice.get("id")))
            if original:
                invoice = dict(invoice)
                for field in HEAVY_INVOICE_FIELDS:
                    if field in original and field not in invoice:
                        invoice[field] = original[field]
        restored.append(invoice)
    return restored
