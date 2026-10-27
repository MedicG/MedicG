from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from email.message import EmailMessage
from email.utils import formataddr
import base64
import datetime as dt
import gzip
import logging
import hashlib
import json
import os
import re
import secrets
import smtplib
import sqlite3
import time
import unicodedata
import urllib.error
import urllib.request
from decimal import Decimal, ROUND_HALF_UP
from html import escape as html_escape
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("MEDICG_DB_PATH", BASE_DIR / "medicg.sqlite3"))
DATABASE_URL = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("POSTGRES_URL")
    or os.environ.get("POSTGRES_URL_NON_POOLING")
    or os.environ.get("POSTGRES_PRISMA_URL")
    or os.environ.get("POSTGRES_DATABASE_URL")
    or os.environ.get("NEON_DATABASE_URL")
)
DB_DRIVER = "postgres" if DATABASE_URL else "sqlite"
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@medicg.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123")
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", str(12 * 1024 * 1024)))
PUBLIC_APP_URL = os.environ.get("PUBLIC_APP_URL", "").rstrip("/")
PUBLIC_API_URL = os.environ.get("PUBLIC_API_URL", "").rstrip("/")
VERCEL_URL = os.environ.get("VERCEL_URL", "").rstrip("/")
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or ADMIN_EMAIL)
SMTP_FROM_NAME = os.environ.get("SMTP_FROM_NAME", "Medic G")
SMTP_TLS = os.environ.get("SMTP_TLS", "true").lower() not in ("0", "false", "no")
SMTP_SSL = os.environ.get("SMTP_SSL", "false").lower() in ("1", "true", "yes")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", SMTP_FROM)
RESEND_ENDPOINT = os.environ.get("RESEND_ENDPOINT", "https://api.resend.com/emails")
SRI_CERT_P12_BASE64 = os.environ.get("SRI_CERT_P12_BASE64", "")
SRI_CERT_P12_PATH = os.environ.get("SRI_CERT_P12_PATH", "")
SRI_CERT_PASSWORD = os.environ.get("SRI_CERT_PASSWORD", "")
SRI_AUTH_RETRIES = int(os.environ.get("SRI_AUTH_RETRIES", "4"))
SRI_AUTH_SLEEP_SECONDS = float(os.environ.get("SRI_AUTH_SLEEP_SECONDS", "1.2"))
SRI_TIMEOUT_SECONDS = int(os.environ.get("SRI_TIMEOUT_SECONDS", "18"))
SHOW_VERIFICATION_LINK = os.environ.get("SHOW_VERIFICATION_LINK", "false").lower() in ("1", "true", "yes")
SESSIONS = {}
ALLOWED_PERMISSIONS = {
    "dashboard", "agenda", "hce", "facturacion", "reportes", "pacientes",
    "medicos", "especialidades", "seguros", "quirofanos", "servicios",
    "examenes", "caja", "config", "farmacia", "certificados",
}
ROLE_DEFAULT_PERMISSIONS = {
    "admin": sorted(ALLOWED_PERMISSIONS),
    "recepcion": ["dashboard", "agenda", "caja", "servicios", "examenes", "certificados"],
    "secretaria": ["dashboard", "agenda", "caja", "servicios", "examenes", "certificados"],
    "asistente": ["agenda", "caja"],
    "medico": ["dashboard", "agenda", "hce"],
    "paciente": [],
    "pendiente": [],
}
MOJIBAKE_REPLACEMENTS = {
    "\u00e2\u20ac\u20ac": "\u2000",
    "\u00e2\u0080\u0080": "\u2000",
    "\u00e2\u20ac\u0081": "\u2001",
    "\u00e2\u0080\u0081": "\u2001",
    "\u00e2\u20ac\u201a": "\u2002",
    "\u00e2\u0080\u0082": "\u2002",
    "\u00e2\u20ac\u0192": "\u2003",
    "\u00e2\u0080\u0083": "\u2003",
    "\u00e2\u20ac\u201e": "\u2004",
    "\u00e2\u0080\u0084": "\u2004",
    "\u00e2\u20ac\u2026": "\u2005",
    "\u00e2\u0080\u0085": "\u2005",
    "\u00e2\u20ac\u2020": "\u2006",
    "\u00e2\u0080\u0086": "\u2006",
    "\u00e2\u20ac\u2021": "\u2007",
    "\u00e2\u0080\u0087": "\u2007",
    "\u00e2\u20ac\u02c6": "\u2008",
    "\u00e2\u0080\u0088": "\u2008",
    "\u00e2\u20ac\u2030": "\u2009",
    "\u00e2\u0080\u0089": "\u2009",
    "\u00e2\u20ac\u0160": "\u200a",
    "\u00e2\u0080\u008a": "\u200a",
    "\u00e2\u20ac\u2039": "\u200b",
    "\u00e2\u0080\u008b": "\u200b",
    "\u00e2\u20ac\u0152": "\u200c",
    "\u00e2\u0080\u008c": "\u200c",
    "\u00e2\u20ac\u008d": "\u200d",
    "\u00e2\u0080\u008d": "\u200d",
    "\u00e2\u20ac\u017d": "\u200e",
    "\u00e2\u0080\u008e": "\u200e",
    "\u00e2\u20ac\u008f": "\u200f",
    "\u00e2\u0080\u008f": "\u200f",
    "\u00e2\u20ac\u0090": "\u2010",
    "\u00e2\u0080\u0090": "\u2010",
    "\u00e2\u20ac\u2018": "\u2011",
    "\u00e2\u0080\u0091": "\u2011",
    "\u00e2\u20ac\u2019": "\u2012",
    "\u00e2\u0080\u0092": "\u2012",
    "\u00e2\u20ac\u201c": "\u2013",
    "\u00e2\u0080\u0093": "\u2013",
    "\u00e2\u20ac\u201d": "\u2014",
    "\u00e2\u0080\u0094": "\u2014",
    "\u00e2\u20ac\u2022": "\u2015",
    "\u00e2\u0080\u0095": "\u2015",
    "\u00e2\u20ac\u2013": "\u2016",
    "\u00e2\u0080\u0096": "\u2016",
    "\u00e2\u20ac\u2014": "\u2017",
    "\u00e2\u0080\u0097": "\u2017",
    "\u00e2\u20ac\u02dc": "\u2018",
    "\u00e2\u0080\u0098": "\u2018",
    "\u00e2\u20ac\u2122": "\u2019",
    "\u00e2\u0080\u0099": "\u2019",
    "\u00e2\u20ac\u0161": "\u201a",
    "\u00e2\u0080\u009a": "\u201a",
    "\u00e2\u20ac\u203a": "\u201b",
    "\u00e2\u0080\u009b": "\u201b",
    "\u00e2\u20ac\u0153": "\u201c",
    "\u00e2\u0080\u009c": "\u201c",
    "\u00e2\u20ac\u009d": "\u201d",
    "\u00e2\u0080\u009d": "\u201d",
    "\u00e2\u20ac\u017e": "\u201e",
    "\u00e2\u0080\u009e": "\u201e",
    "\u00e2\u20ac\u0178": "\u201f",
    "\u00e2\u0080\u009f": "\u201f",
    "\u00e2\u20ac\u00a0": "\u2020",
    "\u00e2\u0080\u00a0": "\u2020",
    "\u00e2\u20ac\u00a1": "\u2021",
    "\u00e2\u0080\u00a1": "\u2021",
    "\u00e2\u20ac\u00a2": "\u2022",
    "\u00e2\u0080\u00a2": "\u2022",
    "\u00e2\u20ac\u00a3": "\u2023",
    "\u00e2\u0080\u00a3": "\u2023",
    "\u00e2\u20ac\u00a4": "\u2024",
    "\u00e2\u0080\u00a4": "\u2024",
    "\u00e2\u20ac\u00a5": "\u2025",
    "\u00e2\u0080\u00a5": "\u2025",
    "\u00e2\u20ac\u00a6": "\u2026",
    "\u00e2\u0080\u00a6": "\u2026",
    "\u00e2\u20ac\u00a7": "\u2027",
    "\u00e2\u0080\u00a7": "\u2027",
    "\u00e2\u20ac\u00a8": "\u2028",
    "\u00e2\u0080\u00a8": "\u2028",
    "\u00e2\u20ac\u00a9": "\u2029",
    "\u00e2\u0080\u00a9": "\u2029",
    "\u00e2\u20ac\u00aa": "\u202a",
    "\u00e2\u0080\u00aa": "\u202a",
    "\u00e2\u20ac\u00ab": "\u202b",
    "\u00e2\u0080\u00ab": "\u202b",
    "\u00e2\u20ac\u00ac": "\u202c",
    "\u00e2\u0080\u00ac": "\u202c",
    "\u00e2\u20ac\u00ad": "\u202d",
    "\u00e2\u0080\u00ad": "\u202d",
    "\u00e2\u20ac\u00ae": "\u202e",
    "\u00e2\u0080\u00ae": "\u202e",
    "\u00e2\u20ac\u00af": "\u202f",
    "\u00e2\u0080\u00af": "\u202f",
    "\u00e2\u20ac\u00b0": "\u2030",
    "\u00e2\u0080\u00b0": "\u2030",
    "\u00e2\u20ac\u00b1": "\u2031",
    "\u00e2\u0080\u00b1": "\u2031",
    "\u00e2\u20ac\u00b2": "\u2032",
    "\u00e2\u0080\u00b2": "\u2032",
    "\u00e2\u20ac\u00b3": "\u2033",
    "\u00e2\u0080\u00b3": "\u2033",
    "\u00e2\u20ac\u00b4": "\u2034",
    "\u00e2\u0080\u00b4": "\u2034",
    "\u00e2\u20ac\u00b5": "\u2035",
    "\u00e2\u0080\u00b5": "\u2035",
    "\u00e2\u20ac\u00b6": "\u2036",
    "\u00e2\u0080\u00b6": "\u2036",
    "\u00e2\u20ac\u00b7": "\u2037",
    "\u00e2\u0080\u00b7": "\u2037",
    "\u00e2\u20ac\u00b8": "\u2038",
    "\u00e2\u0080\u00b8": "\u2038",
    "\u00e2\u20ac\u00b9": "\u2039",
    "\u00e2\u0080\u00b9": "\u2039",
    "\u00e2\u20ac\u00ba": "\u203a",
    "\u00e2\u0080\u00ba": "\u203a",
    "\u00e2\u20ac\u00bb": "\u203b",
    "\u00e2\u0080\u00bb": "\u203b",
    "\u00e2\u20ac\u00bc": "\u203c",
    "\u00e2\u0080\u00bc": "\u203c",
    "\u00e2\u20ac\u00bd": "\u203d",
    "\u00e2\u0080\u00bd": "\u203d",
    "\u00e2\u20ac\u00be": "\u203e",
    "\u00e2\u0080\u00be": "\u203e",
    "\u00e2\u20ac\u00bf": "\u203f",
    "\u00e2\u0080\u00bf": "\u203f",
    "\u00e2\u0081\u20ac": "\u2040",
    "\u00e2\u0081\u0080": "\u2040",
    "\u00e2\u0081\u0081": "\u2041",
    "\u00e2\u0081\u201a": "\u2042",
    "\u00e2\u0081\u0082": "\u2042",
    "\u00e2\u0081\u0192": "\u2043",
    "\u00e2\u0081\u0083": "\u2043",
    "\u00e2\u0081\u201e": "\u2044",
    "\u00e2\u0081\u0084": "\u2044",
    "\u00e2\u0081\u2026": "\u2045",
    "\u00e2\u0081\u0085": "\u2045",
    "\u00e2\u0081\u2020": "\u2046",
    "\u00e2\u0081\u0086": "\u2046",
    "\u00e2\u0081\u2021": "\u2047",
    "\u00e2\u0081\u0087": "\u2047",
    "\u00e2\u0081\u02c6": "\u2048",
    "\u00e2\u0081\u0088": "\u2048",
    "\u00e2\u0081\u2030": "\u2049",
    "\u00e2\u0081\u0089": "\u2049",
    "\u00e2\u0081\u0160": "\u204a",
    "\u00e2\u0081\u008a": "\u204a",
    "\u00e2\u0081\u2039": "\u204b",
    "\u00e2\u0081\u008b": "\u204b",
    "\u00e2\u0081\u0152": "\u204c",
    "\u00e2\u0081\u008c": "\u204c",
    "\u00e2\u0081\u008d": "\u204d",
    "\u00e2\u0081\u017d": "\u204e",
    "\u00e2\u0081\u008e": "\u204e",
    "\u00e2\u0081\u008f": "\u204f",
    "\u00e2\u0081\u0090": "\u2050",
    "\u00e2\u0081\u2018": "\u2051",
    "\u00e2\u0081\u0091": "\u2051",
    "\u00e2\u0081\u2019": "\u2052",
    "\u00e2\u0081\u0092": "\u2052",
    "\u00e2\u0081\u201c": "\u2053",
    "\u00e2\u0081\u0093": "\u2053",
    "\u00e2\u0081\u201d": "\u2054",
    "\u00e2\u0081\u0094": "\u2054",
    "\u00e2\u0081\u2022": "\u2055",
    "\u00e2\u0081\u0095": "\u2055",
    "\u00e2\u0081\u2013": "\u2056",
    "\u00e2\u0081\u0096": "\u2056",
    "\u00e2\u0081\u2014": "\u2057",
    "\u00e2\u0081\u0097": "\u2057",
    "\u00e2\u0081\u02dc": "\u2058",
    "\u00e2\u0081\u0098": "\u2058",
    "\u00e2\u0081\u2122": "\u2059",
    "\u00e2\u0081\u0099": "\u2059",
    "\u00e2\u0081\u0161": "\u205a",
    "\u00e2\u0081\u009a": "\u205a",
    "\u00e2\u0081\u203a": "\u205b",
    "\u00e2\u0081\u009b": "\u205b",
    "\u00e2\u0081\u0153": "\u205c",
    "\u00e2\u0081\u009c": "\u205c",
    "\u00e2\u0081\u009d": "\u205d",
    "\u00e2\u0081\u017e": "\u205e",
    "\u00e2\u0081\u009e": "\u205e",
    "\u00e2\u0081\u0178": "\u205f",
    "\u00e2\u0081\u009f": "\u205f",
    "\u00e2\u0081\u00a0": "\u2060",
    "\u00e2\u0081\u00a1": "\u2061",
    "\u00e2\u0081\u00a2": "\u2062",
    "\u00e2\u0081\u00a3": "\u2063",
    "\u00e2\u0081\u00a4": "\u2064",
    "\u00e2\u0081\u00a5": "\u2065",
    "\u00e2\u0081\u00a6": "\u2066",
    "\u00e2\u0081\u00a7": "\u2067",
    "\u00e2\u0081\u00a8": "\u2068",
    "\u00e2\u0081\u00a9": "\u2069",
    "\u00e2\u0081\u00aa": "\u206a",
    "\u00e2\u0081\u00ab": "\u206b",
    "\u00e2\u0081\u00ac": "\u206c",
    "\u00e2\u0081\u00ad": "\u206d",
    "\u00e2\u0081\u00ae": "\u206e",
    "\u00e2\u0081\u00af": "\u206f",
    "\u00e2\u201a\u00ac": "\u20ac",
    "\u00e2\u0082\u00ac": "\u20ac",
    "\u00c2\u00a0": "\u00a0",
    "\u00c2\u00a1": "\u00a1",
    "\u00c2\u00a2": "\u00a2",
    "\u00c2\u00a3": "\u00a3",
    "\u00c2\u00a4": "\u00a4",
    "\u00c2\u00a5": "\u00a5",
    "\u00c2\u00a6": "\u00a6",
    "\u00c2\u00a7": "\u00a7",
    "\u00c2\u00a8": "\u00a8",
    "\u00c2\u00a9": "\u00a9",
    "\u00c2\u00aa": "\u00aa",
    "\u00c2\u00ab": "\u00ab",
    "\u00c2\u00ac": "\u00ac",
    "\u00c2\u00ad": "\u00ad",
    "\u00c2\u00ae": "\u00ae",
    "\u00c2\u00af": "\u00af",
    "\u00c2\u00b0": "\u00b0",
    "\u00c2\u00b1": "\u00b1",
    "\u00c2\u00b2": "\u00b2",
    "\u00c2\u00b3": "\u00b3",
    "\u00c2\u00b4": "\u00b4",
    "\u00c2\u00b5": "\u00b5",
    "\u00c2\u00b6": "\u00b6",
    "\u00c2\u00b7": "\u00b7",
    "\u00c2\u00b8": "\u00b8",
    "\u00c2\u00b9": "\u00b9",
    "\u00c2\u00ba": "\u00ba",
    "\u00c2\u00bb": "\u00bb",
    "\u00c2\u00bc": "\u00bc",
    "\u00c2\u00bd": "\u00bd",
    "\u00c2\u00be": "\u00be",
    "\u00c2\u00bf": "\u00bf",
    "\u00c3\u20ac": "\u00c0",
    "\u00c3\u0080": "\u00c0",
    "\u00c3\u0081": "\u00c1",
    "\u00c3\u201a": "\u00c2",
    "\u00c3\u0082": "\u00c2",
    "\u00c3\u0192": "\u00c3",
    "\u00c3\u0083": "\u00c3",
    "\u00c3\u201e": "\u00c4",
    "\u00c3\u0084": "\u00c4",
    "\u00c3\u2026": "\u00c5",
    "\u00c3\u0085": "\u00c5",
    "\u00c3\u2020": "\u00c6",
    "\u00c3\u0086": "\u00c6",
    "\u00c3\u2021": "\u00c7",
    "\u00c3\u0087": "\u00c7",
    "\u00c3\u02c6": "\u00c8",
    "\u00c3\u0088": "\u00c8",
    "\u00c3\u2030": "\u00c9",
    "\u00c3\u0089": "\u00c9",
    "\u00c3\u0160": "\u00ca",
    "\u00c3\u008a": "\u00ca",
    "\u00c3\u2039": "\u00cb",
    "\u00c3\u008b": "\u00cb",
    "\u00c3\u0152": "\u00cc",
    "\u00c3\u008c": "\u00cc",
    "\u00c3\u008d": "\u00cd",
    "\u00c3\u017d": "\u00ce",
    "\u00c3\u008e": "\u00ce",
    "\u00c3\u008f": "\u00cf",
    "\u00c3\u0090": "\u00d0",
    "\u00c3\u2018": "\u00d1",
    "\u00c3\u0091": "\u00d1",
    "\u00c3\u2019": "\u00d2",
    "\u00c3\u0092": "\u00d2",
    "\u00c3\u201c": "\u00d3",
    "\u00c3\u0093": "\u00d3",
    "\u00c3\u201d": "\u00d4",
    "\u00c3\u0094": "\u00d4",
    "\u00c3\u2022": "\u00d5",
    "\u00c3\u0095": "\u00d5",
    "\u00c3\u2013": "\u00d6",
    "\u00c3\u0096": "\u00d6",
    "\u00c3\u2014": "\u00d7",
    "\u00c3\u0097": "\u00d7",
    "\u00c3\u02dc": "\u00d8",
    "\u00c3\u0098": "\u00d8",
    "\u00c3\u2122": "\u00d9",
    "\u00c3\u0099": "\u00d9",
    "\u00c3\u0161": "\u00da",
    "\u00c3\u009a": "\u00da",
    "\u00c3\u203a": "\u00db",
    "\u00c3\u009b": "\u00db",
    "\u00c3\u0153": "\u00dc",
    "\u00c3\u009c": "\u00dc",
    "\u00c3\u009d": "\u00dd",
    "\u00c3\u017e": "\u00de",
    "\u00c3\u009e": "\u00de",
    "\u00c3\u0178": "\u00df",
    "\u00c3\u009f": "\u00df",
    "\u00c3\u00a0": "\u00e0",
    "\u00c3\u00a1": "\u00e1",
    "\u00c3\u00a2": "\u00e2",
    "\u00c3\u00a3": "\u00e3",
    "\u00c3\u00a4": "\u00e4",
    "\u00c3\u00a5": "\u00e5",
    "\u00c3\u00a6": "\u00e6",
    "\u00c3\u00a7": "\u00e7",
    "\u00c3\u00a8": "\u00e8",
    "\u00c3\u00a9": "\u00e9",
    "\u00c3\u00aa": "\u00ea",
    "\u00c3\u00ab": "\u00eb",
    "\u00c3\u00ac": "\u00ec",
    "\u00c3\u00ad": "\u00ed",
    "\u00c3\u00ae": "\u00ee",
    "\u00c3\u00af": "\u00ef",
    "\u00c3\u00b0": "\u00f0",
    "\u00c3\u00b1": "\u00f1",
    "\u00c3\u00b2": "\u00f2",
    "\u00c3\u00b3": "\u00f3",
    "\u00c3\u00b4": "\u00f4",
    "\u00c3\u00b5": "\u00f5",
    "\u00c3\u00b6": "\u00f6",
    "\u00c3\u00b7": "\u00f7",
    "\u00c3\u00b8": "\u00f8",
    "\u00c3\u00b9": "\u00f9",
    "\u00c3\u00ba": "\u00fa",
    "\u00c3\u00bb": "\u00fb",
    "\u00c3\u00bc": "\u00fc",
    "\u00c3\u00bd": "\u00fd",
    "\u00c3\u00be": "\u00fe",
    "\u00c3\u00bf": "\u00ff",
    "\u00c4\u20ac": "\u0100",
    "\u00c4\u0080": "\u0100",
    "\u00c4\u0081": "\u0101",
    "\u00c4\u201a": "\u0102",
    "\u00c4\u0082": "\u0102",
    "\u00c4\u0192": "\u0103",
    "\u00c4\u0083": "\u0103",
    "\u00c4\u201e": "\u0104",
    "\u00c4\u0084": "\u0104",
    "\u00c4\u2026": "\u0105",
    "\u00c4\u0085": "\u0105",
    "\u00c4\u2020": "\u0106",
    "\u00c4\u0086": "\u0106",
    "\u00c4\u2021": "\u0107",
    "\u00c4\u0087": "\u0107",
    "\u00c4\u02c6": "\u0108",
    "\u00c4\u0088": "\u0108",
    "\u00c4\u2030": "\u0109",
    "\u00c4\u0089": "\u0109",
    "\u00c4\u0160": "\u010a",
    "\u00c4\u008a": "\u010a",
    "\u00c4\u2039": "\u010b",
    "\u00c4\u008b": "\u010b",
    "\u00c4\u0152": "\u010c",
    "\u00c4\u008c": "\u010c",
    "\u00c4\u008d": "\u010d",
    "\u00c4\u017d": "\u010e",
    "\u00c4\u008e": "\u010e",
    "\u00c4\u008f": "\u010f",
    "\u00c4\u0090": "\u0110",
    "\u00c4\u2018": "\u0111",
    "\u00c4\u0091": "\u0111",
    "\u00c4\u2019": "\u0112",
    "\u00c4\u0092": "\u0112",
    "\u00c4\u201c": "\u0113",
    "\u00c4\u0093": "\u0113",
    "\u00c4\u201d": "\u0114",
    "\u00c4\u0094": "\u0114",
    "\u00c4\u2022": "\u0115",
    "\u00c4\u0095": "\u0115",
    "\u00c4\u2013": "\u0116",
    "\u00c4\u0096": "\u0116",
    "\u00c4\u2014": "\u0117",
    "\u00c4\u0097": "\u0117",
    "\u00c4\u02dc": "\u0118",
    "\u00c4\u0098": "\u0118",
    "\u00c4\u2122": "\u0119",
    "\u00c4\u0099": "\u0119",
    "\u00c4\u0161": "\u011a",
    "\u00c4\u009a": "\u011a",
    "\u00c4\u203a": "\u011b",
    "\u00c4\u009b": "\u011b",
    "\u00c4\u0153": "\u011c",
    "\u00c4\u009c": "\u011c",
    "\u00c4\u009d": "\u011d",
    "\u00c4\u017e": "\u011e",
    "\u00c4\u009e": "\u011e",
    "\u00c4\u0178": "\u011f",
    "\u00c4\u009f": "\u011f",
    "\u00c4\u00a0": "\u0120",
    "\u00c4\u00a1": "\u0121",
    "\u00c4\u00a2": "\u0122",
    "\u00c4\u00a3": "\u0123",
    "\u00c4\u00a4": "\u0124",
    "\u00c4\u00a5": "\u0125",
    "\u00c4\u00a6": "\u0126",
    "\u00c4\u00a7": "\u0127",
    "\u00c4\u00a8": "\u0128",
    "\u00c4\u00a9": "\u0129",
    "\u00c4\u00aa": "\u012a",
    "\u00c4\u00ab": "\u012b",
    "\u00c4\u00ac": "\u012c",
    "\u00c4\u00ad": "\u012d",
    "\u00c4\u00ae": "\u012e",
    "\u00c4\u00af": "\u012f",
    "\u00c4\u00b0": "\u0130",
    "\u00c4\u00b1": "\u0131",
    "\u00c4\u00b2": "\u0132",
    "\u00c4\u00b3": "\u0133",
    "\u00c4\u00b4": "\u0134",
    "\u00c4\u00b5": "\u0135",
    "\u00c4\u00b6": "\u0136",
    "\u00c4\u00b7": "\u0137",
    "\u00c4\u00b8": "\u0138",
    "\u00c4\u00b9": "\u0139",
    "\u00c4\u00ba": "\u013a",
    "\u00c4\u00bb": "\u013b",
    "\u00c4\u00bc": "\u013c",
    "\u00c4\u00bd": "\u013d",
    "\u00c4\u00be": "\u013e",
    "\u00c4\u00bf": "\u013f",
    "\u00c5\u20ac": "\u0140",
    "\u00c5\u0080": "\u0140",
    "\u00c5\u0081": "\u0141",
    "\u00c5\u201a": "\u0142",
    "\u00c5\u0082": "\u0142",
    "\u00c5\u0192": "\u0143",
    "\u00c5\u0083": "\u0143",
    "\u00c5\u201e": "\u0144",
    "\u00c5\u0084": "\u0144",
    "\u00c5\u2026": "\u0145",
    "\u00c5\u0085": "\u0145",
    "\u00c5\u2020": "\u0146",
    "\u00c5\u0086": "\u0146",
    "\u00c5\u2021": "\u0147",
    "\u00c5\u0087": "\u0147",
    "\u00c5\u02c6": "\u0148",
    "\u00c5\u0088": "\u0148",
    "\u00c5\u2030": "\u0149",
    "\u00c5\u0089": "\u0149",
    "\u00c5\u0160": "\u014a",
    "\u00c5\u008a": "\u014a",
    "\u00c5\u2039": "\u014b",
    "\u00c5\u008b": "\u014b",
    "\u00c5\u0152": "\u014c",
    "\u00c5\u008c": "\u014c",
    "\u00c5\u008d": "\u014d",
    "\u00c5\u017d": "\u014e",
    "\u00c5\u008e": "\u014e",
    "\u00c5\u008f": "\u014f",
    "\u00c5\u0090": "\u0150",
    "\u00c5\u2018": "\u0151",
    "\u00c5\u0091": "\u0151",
    "\u00c5\u2019": "\u0152",
    "\u00c5\u0092": "\u0152",
    "\u00c5\u201c": "\u0153",
    "\u00c5\u0093": "\u0153",
    "\u00c5\u201d": "\u0154",
    "\u00c5\u0094": "\u0154",
    "\u00c5\u2022": "\u0155",
    "\u00c5\u0095": "\u0155",
    "\u00c5\u2013": "\u0156",
    "\u00c5\u0096": "\u0156",
    "\u00c5\u2014": "\u0157",
    "\u00c5\u0097": "\u0157",
    "\u00c5\u02dc": "\u0158",
    "\u00c5\u0098": "\u0158",
    "\u00c5\u2122": "\u0159",
    "\u00c5\u0099": "\u0159",
    "\u00c5\u0161": "\u015a",
    "\u00c5\u009a": "\u015a",
    "\u00c5\u203a": "\u015b",
    "\u00c5\u009b": "\u015b",
    "\u00c5\u0153": "\u015c",
    "\u00c5\u009c": "\u015c",
    "\u00c5\u009d": "\u015d",
    "\u00c5\u017e": "\u015e",
    "\u00c5\u009e": "\u015e",
    "\u00c5\u0178": "\u015f",
    "\u00c5\u009f": "\u015f",
    "\u00c5\u00a0": "\u0160",
    "\u00c5\u00a1": "\u0161",
    "\u00c5\u00a2": "\u0162",
    "\u00c5\u00a3": "\u0163",
    "\u00c5\u00a4": "\u0164",
    "\u00c5\u00a5": "\u0165",
    "\u00c5\u00a6": "\u0166",
    "\u00c5\u00a7": "\u0167",
    "\u00c5\u00a8": "\u0168",
    "\u00c5\u00a9": "\u0169",
    "\u00c5\u00aa": "\u016a",
    "\u00c5\u00ab": "\u016b",
    "\u00c5\u00ac": "\u016c",
    "\u00c5\u00ad": "\u016d",
    "\u00c5\u00ae": "\u016e",
    "\u00c5\u00af": "\u016f",
    "\u00c5\u00b0": "\u0170",
    "\u00c5\u00b1": "\u0171",
    "\u00c5\u00b2": "\u0172",
    "\u00c5\u00b3": "\u0173",
    "\u00c5\u00b4": "\u0174",
    "\u00c5\u00b5": "\u0175",
    "\u00c5\u00b6": "\u0176",
    "\u00c5\u00b7": "\u0177",
    "\u00c5\u00b8": "\u0178",
    "\u00c5\u00b9": "\u0179",
    "\u00c5\u00ba": "\u017a",
    "\u00c5\u00bb": "\u017b",
    "\u00c5\u00bc": "\u017c",
    "\u00c5\u00bd": "\u017d",
    "\u00c5\u00be": "\u017e",
    "\u00c5\u00bf": "\u017f"
}


from medicg.storage import DatabaseConnection, connect as connect_database


SCHEMA_VERSION = "2026-10-reminders-v1"
LOGIN_MAX_FAILURES = int(os.environ.get("LOGIN_MAX_FAILURES", "8"))
LOGIN_WINDOW_SECONDS = int(os.environ.get("LOGIN_WINDOW_SECONDS", "900"))
log = logging.getLogger("medicg")


def db(read_only=False, lock="global"):
    """Open a transaction. Writes take the global app_data lock unless a narrower
    ``lock`` is given (``None`` for tables that never rewrite app_data)."""
    return connect_database(DB_DRIVER, DATABASE_URL, DB_PATH, read_only=read_only, lock=lock)


def table_sqlite_audit():
    return (
        "create table if not exists audit_log("
        "id integer primary key autoincrement, ts text not null, user_id integer, "
        "email text, action text not null, data_key text, detail text)"
    )


def table_postgres_audit():
    return (
        "create table if not exists audit_log("
        "id bigserial primary key, ts text not null, user_id integer, "
        "email text, action text not null, data_key text, detail text)"
    )


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${digest.hex()}"


def verify_password(password, stored):
    if not stored:
        return False
    if "$" not in stored:
        return password == stored
    salt, _digest = stored.split("$", 1)
    return secrets.compare_digest(hash_password(password, salt), stored)


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def user_email_verified(user):
    return bool(user.get("emailVerified", user.get("estado", "activo") == "activo"))


def app_base_url(handler):
    if PUBLIC_API_URL:
        return PUBLIC_API_URL
    if VERCEL_URL:
        return VERCEL_URL if VERCEL_URL.startswith("http") else f"https://{VERCEL_URL}"
    if PUBLIC_APP_URL:
        return PUBLIC_APP_URL
    origin = handler.headers.get("Origin", "").rstrip("/")
    if origin and not origin.endswith("github.io"):
        return origin
    proto = handler.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
    proto = "https" if proto == "https" else "http"
    host = handler.headers.get("Host", f"{HOST}:{PORT}")
    return f"{proto}://{host}".rstrip("/")


def email_sender_address(sender_email=None):
    sender = sender_email or SMTP_FROM
    return formataddr((SMTP_FROM_NAME, sender)) if SMTP_FROM_NAME else sender


def email_text(name, link):
    return (
        f"Hola {name},\n\n"
        "Gracias por registrarte en Medic G.\n\n"
        "Para activar tu cuenta y poder iniciar sesion, verifica tu correo en este enlace:\n"
        f"{link}\n\n"
        "Este enlace vence por seguridad. Si no solicitaste esta cuenta, puedes ignorar este mensaje."
    )


def email_html(name, link):
    safe_name = str(name or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe_link = str(link or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
    return f"""
    <div style="font-family:Arial,sans-serif;background:#f6f9fb;padding:24px;color:#1f2937;">
      <div style="max-width:560px;margin:auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:14px;padding:26px;">
        <h1 style="margin:0 0 12px;color:#0f766e;font-size:24px;">Verifica tu cuenta Medic G</h1>
        <p>Hola {safe_name},</p>
        <p>Gracias por registrarte en Medic G. Para activar tu cuenta y poder iniciar sesion, confirma tu correo.</p>
        <p style="margin:24px 0;"><a href="{safe_link}" style="background:#0f766e;color:#fff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:700;display:inline-block;">Verificar mi correo</a></p>
        <p style="font-size:13px;color:#6b7280;">Si el boton no funciona, copia este enlace en tu navegador:<br>{safe_link}</p>
        <p style="font-size:13px;color:#6b7280;">Si no solicitaste esta cuenta, puedes ignorar este mensaje.</p>
      </div>
    </div>
    """


def email_configured():
    from medicg.mailer import settings
    cfg = settings()
    return bool(cfg.get('refreshToken') or (cfg.get('secret') and cfg.get('from')))


def send_with_resend(to_email, subject, text_body, html_body):
    sender = RESEND_FROM if "<" in RESEND_FROM else email_sender_address(RESEND_FROM)
    payload = json.dumps({
        "from": sender,
        "to": [to_email],
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }).encode("utf-8")
    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        if resp.status < 200 or resp.status >= 300:
            return False, f"Resend respondio con estado {resp.status}"
    return True, ""


def send_with_smtp(to_email, subject, text_body, html_body):
    if not (SMTP_HOST and SMTP_FROM):
        return False, "SMTP no configurado"
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_sender_address()
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    if SMTP_SSL:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            if SMTP_USER and SMTP_PASSWORD:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as smtp:
            smtp.ehlo()
            if SMTP_TLS:
                smtp.starttls()
                smtp.ehlo()
            if SMTP_USER and SMTP_PASSWORD:
                smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(msg)
    return True, ""


def send_verification_email(to_email, name, link):
    return send_transaction_email(to_email, "Verifica tu cuenta Medic G", email_text(name, link), email_html(name, link))

class SRIIntegrationError(Exception):
    pass


SRI_RECEPTION_ENDPOINTS = {
    "1": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline",
    "2": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline",
}
SRI_AUTH_ENDPOINTS = {
    "1": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
    "2": "https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline",
}


def clean_digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def sri_bool(value, default=False):
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "si", "on", "prod", "produccion")


def money_decimal(value):
    try:
        return Decimal(str(value or "0")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def money_text(value):
    return f"{money_decimal(value):.2f}"


def parse_invoice_date(value):
    raw = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return dt.datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return dt.date.today()


def sri_config(config):
    cfg = config or {}
    ambiente_raw = os.environ.get("SRI_AMBIENTE") or cfg.get("sriAmbiente") or "1"
    ambiente = "2" if str(ambiente_raw).strip().lower() in ("2", "prod", "produccion", "production") else "1"
    iva_rate = money_decimal(os.environ.get("SRI_IVA_RATE") or cfg.get("sriIvaRate") or "15")
    iva_code = os.environ.get("SRI_IVA_CODE") or cfg.get("sriIvaCode") or ("4" if iva_rate == Decimal("15.00") else "2" if iva_rate == Decimal("12.00") else "0")
    auto_env = os.environ.get("SRI_AUTO_SEND")
    auto_send = sri_bool(auto_env, bool(cfg.get("sriAutoSend", True))) if auto_env is not None else bool(cfg.get("sriAutoSend", True))
    return {
        "ambiente": ambiente,
        "tipoEmision": "1",
        "ruc": clean_digits(os.environ.get("SRI_RUC") or cfg.get("sriRuc") or cfg.get("ruc")),
        "razonSocial": os.environ.get("SRI_RAZON_SOCIAL") or cfg.get("sriRazonSocial") or cfg.get("nombre") or "Centro Medico",
        "nombreComercial": os.environ.get("SRI_NOMBRE_COMERCIAL") or cfg.get("sriNombreComercial") or cfg.get("nombre") or "Medic G",
        "dirMatriz": os.environ.get("SRI_DIR_MATRIZ") or cfg.get("sriDirMatriz") or cfg.get("dir") or "",
        "dirEstablecimiento": os.environ.get("SRI_DIR_ESTABLECIMIENTO") or cfg.get("sriDirEstablecimiento") or cfg.get("dir") or "",
        "estab": (os.environ.get("SRI_ESTAB") or cfg.get("sriEstab") or "001").zfill(3)[:3],
        "ptoEmi": (os.environ.get("SRI_PTO_EMI") or cfg.get("sriPtoEmi") or "001").zfill(3)[:3],
        "obligadoContabilidad": (os.environ.get("SRI_OBLIGADO_CONTABILIDAD") or cfg.get("sriObligadoContabilidad") or "NO").upper(),
        "contribuyenteEspecial": os.environ.get("SRI_CONTRIBUYENTE_ESPECIAL") or cfg.get("sriContribuyenteEspecial") or "",
        "ivaRate": iva_rate,
        "ivaCode": str(iva_code),
        "autoSend": False,
    }


def sri_mod11(body):
    factors = [2, 3, 4, 5, 6, 7]
    total = 0
    for idx, digit in enumerate(reversed(body)):
        total += int(digit) * factors[idx % len(factors)]
    check = 11 - (total % 11)
    if check == 11:
        return "0"
    if check == 10:
        return "1"
    return str(check)


def build_access_key(fecha, sri, secuencial):
    ruc = clean_digits(sri.get("ruc"))
    if len(ruc) != 13:
        raise SRIIntegrationError("Configura un RUC valido de 13 digitos para facturacion electronica SRI")
    numeric_code = clean_digits(os.environ.get("SRI_NUMERIC_CODE") or f"{int(time.time()) % 100000000:08d}").zfill(8)[-8:]
    body = (
        fecha.strftime("%d%m%Y")
        + "01"
        + ruc
        + sri["ambiente"]
        + sri["estab"]
        + sri["ptoEmi"]
        + str(secuencial).zfill(9)[-9:]
        + numeric_code
        + sri["tipoEmision"]
    )
    return body + sri_mod11(body)


def id_type_for_patient(patient):
    doc = clean_digits(patient.get("cedula") or patient.get("ruc") or patient.get("documento"))
    if len(doc) == 13:
        return "04", doc
    if len(doc) == 10:
        return "05", doc
    if doc:
        return "06", doc
    return "07", "9999999999999"


def payment_code(payment):
    value = str(payment or "").lower()
    if "debito" in value or "debito" in value:
        return "16"
    if "credito" in value or "credito" in value or "tarjeta" in value:
        return "19"
    if "transfer" in value or "seguro" in value or "iess" in value:
        return "20"
    return "01"


def add_text(parent, name, text):
    child = ET.SubElement(parent, name)
    child.text = str(text if text is not None else "")
    return child


SRI_IVA_CODES = {Decimal("0.00"): "0", Decimal("12.00"): "2", Decimal("14.00"): "3", Decimal("15.00"): "4", Decimal("5.00"): "5", Decimal("13.00"): "10"}


def sri_iva_code(rate, sri):
    """SRI table 17 (codigoPorcentaje) for the IVA rate of a line."""
    rate = money_decimal(rate)
    if rate in SRI_IVA_CODES:
        return SRI_IVA_CODES[rate]
    return str(sri.get("ivaCode") or "4")


def build_invoice_xml(invoice, patient, config):
    sri = invoice["sri"]
    fecha = parse_invoice_date(invoice.get("fecha"))
    tipo_id, identificacion = id_type_for_patient(patient)
    subtotal = money_decimal(invoice.get("sub"))
    iva = money_decimal(invoice.get("iva"))
    total = money_decimal(invoice.get("total"))
    iva_rate = money_decimal(sri.get("ivaRate") or 15)
    # Cash-desk and pharmacy accounts record their own VAT (0% medical services and
    # medicines, 15% other goods). Use the rate of each line, not the global setting.
    invoice_rate = invoice.get("ivaRate")
    lines = []
    for idx, item in enumerate(invoice.get("items") or [], start=1):
        qty = money_decimal(item.get("cant") or 1)
        unit = money_decimal(item.get("unit"))
        line_base = money_decimal(item.get("total") or (qty * unit))
        if item.get("ivaRate") is not None:
            rate = money_decimal(item.get("ivaRate"))
        elif invoice_rate is not None:
            rate = money_decimal(invoice_rate)
        else:
            rate = iva_rate
        if item.get("iva") is not None and item.get("ivaRate") is not None:
            line_tax = money_decimal(item.get("iva"))
        else:
            line_tax = money_decimal(line_base * rate / Decimal("100"))
        lines.append((idx, item, qty, unit, line_base, rate, line_tax))
    groups = {}
    for _idx, _item, _qty, _unit, base, rate, line_tax in lines:
        group = groups.setdefault(rate, [Decimal(0), Decimal(0)])
        group[0] += base
        group[1] += line_tax
    if lines:
        iva = money_decimal(sum((g[1] for g in groups.values()), Decimal(0)))
    root = ET.Element("factura", {"id": "comprobante", "version": "1.1.0"})
    info_trib = ET.SubElement(root, "infoTributaria")
    add_text(info_trib, "ambiente", sri["ambiente"])
    add_text(info_trib, "tipoEmision", sri["tipoEmision"])
    add_text(info_trib, "razonSocial", sri["razonSocial"][:300])
    add_text(info_trib, "nombreComercial", sri["nombreComercial"][:300])
    add_text(info_trib, "ruc", sri["ruc"])
    add_text(info_trib, "claveAcceso", invoice["claveAcceso"])
    add_text(info_trib, "codDoc", "01")
    add_text(info_trib, "estab", sri["estab"])
    add_text(info_trib, "ptoEmi", sri["ptoEmi"])
    add_text(info_trib, "secuencial", invoice["secuencial"])
    add_text(info_trib, "dirMatriz", sri["dirMatriz"][:300])

    info_fact = ET.SubElement(root, "infoFactura")
    add_text(info_fact, "fechaEmision", fecha.strftime("%d/%m/%Y"))
    add_text(info_fact, "dirEstablecimiento", sri["dirEstablecimiento"][:300])
    if sri.get("contribuyenteEspecial"):
        add_text(info_fact, "contribuyenteEspecial", sri["contribuyenteEspecial"])
    add_text(info_fact, "obligadoContabilidad", sri["obligadoContabilidad"] if sri["obligadoContabilidad"] in ("SI", "NO") else "NO")
    add_text(info_fact, "tipoIdentificacionComprador", tipo_id)
    buyer_name = f"{patient.get('nombres','')} {patient.get('apellidos','')}".strip() or "CONSUMIDOR FINAL"
    add_text(info_fact, "razonSocialComprador", buyer_name[:300])
    add_text(info_fact, "identificacionComprador", identificacion)
    add_text(info_fact, "direccionComprador", (patient.get("dir") or "Consumidor final")[:300])
    add_text(info_fact, "totalSinImpuestos", money_text(subtotal))
    add_text(info_fact, "totalDescuento", "0.00")
    total_imp = ET.SubElement(info_fact, "totalConImpuestos")
    for rate, (base, value) in (sorted(groups.items()) if groups else [(iva_rate, (subtotal, iva))]):
        imp = ET.SubElement(total_imp, "totalImpuesto")
        add_text(imp, "codigo", "2")
        add_text(imp, "codigoPorcentaje", sri_iva_code(rate, sri))
        add_text(imp, "baseImponible", money_text(base))
        add_text(imp, "valor", money_text(value))
    add_text(info_fact, "propina", "0.00")
    add_text(info_fact, "importeTotal", money_text(total))
    add_text(info_fact, "moneda", "DOLAR")
    pagos = ET.SubElement(info_fact, "pagos")
    pago = ET.SubElement(pagos, "pago")
    add_text(pago, "formaPago", payment_code(invoice.get("pago")))
    add_text(pago, "total", money_text(total))
    add_text(pago, "plazo", "0")
    add_text(pago, "unidadTiempo", "dias")

    detalles = ET.SubElement(root, "detalles")
    for idx, item, qty, unit, line_base, line_rate, line_tax in lines:
        det = ET.SubElement(detalles, "detalle")
        add_text(det, "codigoPrincipal", str(item.get("codigo") or f"MED{idx:03d}"))
        add_text(det, "descripcion", str(item.get("desc") or "Servicio medico")[:300])
        add_text(det, "cantidad", money_text(qty))
        add_text(det, "precioUnitario", money_text(unit))
        add_text(det, "descuento", "0.00")
        add_text(det, "precioTotalSinImpuesto", money_text(line_base))
        impuestos = ET.SubElement(det, "impuestos")
        impuesto = ET.SubElement(impuestos, "impuesto")
        add_text(impuesto, "codigo", "2")
        add_text(impuesto, "codigoPorcentaje", sri_iva_code(line_rate, sri))
        add_text(impuesto, "tarifa", money_text(line_rate))
        add_text(impuesto, "baseImponible", money_text(line_base))
        add_text(impuesto, "valor", money_text(line_tax))

    info_ad = ET.SubElement(root, "infoAdicional")
    if patient.get("email"):
        add_text(info_ad, "campoAdicional", patient.get("email")).set("nombre", "Email")
    add_text(info_ad, "campoAdicional", buyer_name[:300]).set("nombre", "Paciente")
    add_text(info_ad, "campoAdicional", f"HCE-{str(patient.get('id') or 0).zfill(4)}").set("nombre", "HistoriaClinica")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode("utf-8")


def normalize_cert_base64(value):
    raw = str(value or "").strip()
    if raw.lower().startswith("data:") and "," in raw:
        raw = raw.split(",", 1)[1]
    return "".join(raw.split())


def saved_sri_certificate_status(cert):
    cert = cert if isinstance(cert, dict) else {}
    has_env_cert = bool(normalize_cert_base64(SRI_CERT_P12_BASE64))
    saved_b64 = normalize_cert_base64(cert.get("p12Base64"))
    configured = bool(has_env_cert or saved_b64)
    return {
        "configured": configured,
        "source": "Variables privadas de Vercel" if has_env_cert else ("Base de datos" if saved_b64 else "No configurado"),
        "filename": "SRI_CERT_P12_BASE64" if has_env_cert else cert.get("filename", ""),
        "updatedAt": "" if has_env_cert else cert.get("updatedAt", ""),
        "hasPassword": bool(SRI_CERT_PASSWORD or cert.get("password")),
        "envLocked": has_env_cert,
    }


def get_sri_certificate(conn):
    env_b64 = normalize_cert_base64(SRI_CERT_P12_BASE64)
    if env_b64:
        return {
            "p12Base64": env_b64,
            "password": SRI_CERT_PASSWORD,
            "filename": "SRI_CERT_P12_BASE64",
            "source": "Variables privadas de Vercel",
        }
    saved = get_json_key(conn, "sriCertificate", {}) or {}
    return {
        "p12Base64": normalize_cert_base64(saved.get("p12Base64")),
        "password": saved.get("password") or SRI_CERT_PASSWORD,
        "filename": saved.get("filename", ""),
        "updatedAt": saved.get("updatedAt", ""),
        "uploadedBy": saved.get("uploadedBy", ""),
        "source": "Base de datos" if saved.get("p12Base64") else "No configurado",
    }


def sri_certificate_status(conn):
    saved = get_json_key(conn, "sriCertificate", {}) or {}
    return saved_sri_certificate_status(saved)


def load_sri_certificate_bytes(cert_info=None):
    cert_info = cert_info or {}
    cert_b64 = normalize_cert_base64(cert_info.get("p12Base64") or SRI_CERT_P12_BASE64)
    if cert_b64:
        try:
            return base64.b64decode(cert_b64, validate=True)
        except Exception as exc:
            raise SRIIntegrationError("El certificado .p12/.pfx guardado no es valido. Vuelve a subirlo desde Configuracion.") from exc
    if SRI_CERT_P12_PATH:
        cert_path = Path(SRI_CERT_P12_PATH)
        if cert_path.exists():
            return cert_path.read_bytes()
    raise SRIIntegrationError("Sube el certificado .p12/.pfx y su clave en Configuracion > Facturacion electronica SRI, o configura SRI_CERT_P12_BASE64 y SRI_CERT_PASSWORD en Vercel")


def sign_invoice_xml(unsigned_xml, cert_info=None):
    try:
        from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, pkcs12
        from signxml import methods
        from signxml.xades import XAdESDataObjectFormat, XAdESSigner
        from lxml import etree
    except Exception as exc:
        raise SRIIntegrationError("Faltan dependencias para firma XAdES. Reinstala requirements.txt en Vercel.") from exc
    try:
        cert_info = cert_info or {}
        cert_password = cert_info.get("password") or SRI_CERT_PASSWORD
        key, cert, _extra = pkcs12.load_key_and_certificates(
            load_sri_certificate_bytes(cert_info),
            cert_password.encode("utf-8") if cert_password else None,
        )
        if not key or not cert:
            raise SRIIntegrationError("El certificado P12 no contiene clave privada o certificado valido")
        key_pem = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
        cert_pem = cert.public_bytes(Encoding.PEM)
        root = etree.fromstring(unsigned_xml.encode("utf-8"))
        signer = XAdESSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
            data_object_format=XAdESDataObjectFormat(Description="Factura electronica SRI", MimeType="text/xml"),
        )
        signer.use_deprecated_legacy_signing_certificate = True
        signed = signer.sign(root, key=key_pem, cert=cert_pem, reference_uri="#comprobante")
        return etree.tostring(signed, encoding="utf-8", xml_declaration=True).decode("utf-8")
    except SRIIntegrationError:
        raise
    except Exception as exc:
        raise SRIIntegrationError(f"No se pudo firmar el XML con el certificado digital: {exc}") from exc


def xml_local_name(tag):
    return str(tag).split("}", 1)[-1]


def xml_first_text(root, name):
    for node in root.iter():
        if xml_local_name(node.tag) == name and node.text:
            return node.text.strip()
    return ""


def xml_messages(root):
    messages = []
    for msg in root.iter():
        if xml_local_name(msg.tag) != "mensaje":
            continue
        detail = {}
        for child in list(msg):
            detail[xml_local_name(child.tag)] = (child.text or "").strip()
        if detail:
            messages.append(detail)
    return messages


def sri_soap_request(url, action_body):
    envelope = f'''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Header/>
  <soapenv:Body>{action_body}</soapenv:Body>
</soapenv:Envelope>'''.encode("utf-8")
    req = urllib.request.Request(
        url,
        data=envelope,
        method="POST",
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": ""},
    )
    try:
        with urllib.request.urlopen(req, timeout=SRI_TIMEOUT_SECONDS) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SRIIntegrationError(f"SRI respondio HTTP {exc.code}: {detail[:500]}") from exc
    except Exception as exc:
        raise SRIIntegrationError(f"No se pudo conectar con el SRI: {exc}") from exc


def sri_recepcion(signed_xml, ambiente):
    payload = base64.b64encode(signed_xml.encode("utf-8")).decode("ascii")
    body = f'''<validarComprobante xmlns="http://ec.gob.sri.ws.recepcion">
  <xml>{payload}</xml>
</validarComprobante>'''
    raw = sri_soap_request(SRI_RECEPTION_ENDPOINTS[ambiente], body)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SRIIntegrationError(f"Respuesta SRI recepcion invalida: {raw[:300]}") from exc
    return {"estado": xml_first_text(root, "estado") or "SIN_RESPUESTA", "mensajes": xml_messages(root), "raw": raw[:3000]}


def sri_autorizacion(clave, ambiente):
    body = f'''<autorizacionComprobante xmlns="http://ec.gob.sri.ws.autorizacion">
  <claveAccesoComprobante>{html_escape(clave)}</claveAccesoComprobante>
</autorizacionComprobante>'''
    raw = sri_soap_request(SRI_AUTH_ENDPOINTS[ambiente], body)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise SRIIntegrationError(f"Respuesta SRI autorizacion invalida: {raw[:300]}") from exc
    auth_node = None
    for node in root.iter():
        if xml_local_name(node.tag) == "autorizacion":
            auth_node = node
            break
    if auth_node is None:
        return {"estado": xml_first_text(root, "estado") or "EN_PROCESO", "mensajes": xml_messages(root), "raw": raw[:3000]}
    comprobante = xml_first_text(auth_node, "comprobante")
    return {
        "estado": xml_first_text(auth_node, "estado") or "EN_PROCESO",
        "numeroAutorizacion": xml_first_text(auth_node, "numeroAutorizacion"),
        "fechaAutorizacion": xml_first_text(auth_node, "fechaAutorizacion"),
        "ambiente": xml_first_text(auth_node, "ambiente"),
        "comprobante": comprobante,
        "mensajes": xml_messages(auth_node),
        "raw": raw[:3000],
    }


def ride_html(invoice, patient, config, ticket=False):
    cfg = config or {}
    rows = "".join(
        f"<tr><td>{html_escape(str(i.get('desc','')))}</td><td>{html_escape(str(i.get('cant',1)))}</td><td>{money_text(i.get('unit'))}</td><td>{money_text(i.get('total'))}</td></tr>"
        for i in (invoice.get("items") or [])
    )
    patient_name = f"{patient.get('nombres','')} {patient.get('apellidos','')}".strip()
    width = "width:80mm;font-size:11px;" if ticket else "max-width:760px;"
    return f"""<!doctype html><html lang='es'><meta charset='utf-8'><title>RIDE {html_escape(invoice.get('id',''))}</title>
<body style='font-family:Arial,sans-serif;color:#111;margin:0;padding:18px;{width}'>
  <div style='display:flex;gap:12px;align-items:center;border-bottom:2px solid #0f766e;padding-bottom:10px;margin-bottom:12px;'>
    <img src='{html_escape(cfg.get('logo') or 'assets/medicg-logo.jpg')}' style='width:72px;height:72px;object-fit:contain;'>
    <div><h2 style='margin:0;'>{html_escape(cfg.get('nombre') or 'Centro Medico')}</h2><div>RUC: {html_escape((invoice.get('sri') or {}).get('ruc') or cfg.get('ruc') or '')}</div><div>{html_escape(cfg.get('dir') or '')}</div></div>
  </div>
  <h3>RIDE - Factura electronica</h3>
  <p><b>No.:</b> {html_escape(invoice.get('id',''))}<br><b>Fecha:</b> {html_escape(invoice.get('fecha',''))}<br><b>Estado SRI:</b> {html_escape(invoice.get('sriEstado') or invoice.get('estado',''))}</p>
  <p><b>Cliente:</b> {html_escape(patient_name)}<br><b>Identificacion:</b> {html_escape(patient.get('cedula') or '9999999999999')}<br><b>Email:</b> {html_escape(patient.get('email') or '')}</p>
  <table width='100%' border='1' cellspacing='0' cellpadding='6'><thead><tr><th>Detalle</th><th>Cant.</th><th>P.Unit.</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>
  <div style='text-align:right;margin-top:12px;'><div>Subtotal: ${money_text(invoice.get('sub'))}</div><div>IVA: ${money_text(invoice.get('iva'))}</div><h3>Total: ${money_text(invoice.get('total'))}</h3></div>
  <p style='word-break:break-all;'><b>Clave de acceso:</b><br>{html_escape(invoice.get('claveAcceso') or '')}</p>
  <p style='word-break:break-all;'><b>Autorizacion:</b><br>{html_escape(invoice.get('autorizacion') or '')}</p>
</body></html>"""


def send_transaction_email(to_email, subject, text_body, html_body, attachments=None, mail_config=None, mail_conn=None):
    from medicg.mailer import send
    return send(to_email, subject, text_body, html_body, attachments, mail_config, mail_conn)


def send_invoice_email(invoice, patient, config, mail_config=None, mail_conn=None):
    to_email = (patient.get("email") or "").strip()
    if not to_email:
        return False, "El paciente no tiene correo registrado"
    subject = f"Factura electronica {invoice.get('id')} - {config.get('nombre','Medic G')}"
    text = (
        f"Adjuntamos tu factura electronica {invoice.get('id')}\n"
        f"Estado SRI: {invoice.get('sriEstado') or invoice.get('estado')}\n"
        f"Total: ${money_text(invoice.get('total'))}\n"
        f"Clave de acceso: {invoice.get('claveAcceso') or ''}\n"
    )
    html = ride_html(invoice, patient, config)
    xml_content = (invoice.get("authorizedXml") or invoice.get("signedXml") or invoice.get("xml") or "").encode("utf-8")
    attachments = [
        {"filename": f"RIDE-{invoice.get('id')}.html", "content": html.encode("utf-8"), "mime": "text/html"},
    ]
    if xml_content:
        attachments.append({"filename": f"{invoice.get('id')}.xml", "content": xml_content, "mime": "application/xml"})
    return send_transaction_email(to_email, subject, text, html, attachments, mail_config, mail_conn)


def can_invoice_sri(user):
    if not user:
        return False
    if user.get("rol") == "admin":
        return True
    perms = set(clean_permissions(user.get("permissions"), user.get("rol", "recepcion")))
    return bool({"facturacion", "caja"} & perms)


def prepare_invoice_from_payload(conn, user, payload):
    patients = get_json_key(conn, "pacientes", []) or []
    patient_id = int(payload.get("pac") or payload.get("patientId") or 0)
    patient = find_patient(patients, patient_id=patient_id)
    if not patient:
        raise SRIIntegrationError("Selecciona un paciente registrado para emitir factura")
    items = []
    for raw in payload.get("items") or []:
        desc = str(raw.get("desc") or raw.get("descripcion") or "").strip()
        qty = money_decimal(raw.get("cant") or raw.get("cantidad") or 1)
        unit = money_decimal(raw.get("unit") or raw.get("precio") or 0)
        if desc and qty > 0 and unit >= 0:
            items.append({"desc": desc, "cant": float(qty), "unit": float(unit), "total": float(money_decimal(qty * unit))})
    if not items:
        raise SRIIntegrationError("Agrega al menos un servicio o examen facturable")
    config = get_json_key(conn, "config", {}) or {}
    sri = sri_config(config)
    next_ids = get_json_key(conn, "nextIds", {}) or {}
    seq_int = next_id(next_ids, "fac", 1)
    secuencial = str(seq_int).zfill(9)[-9:]
    fecha = parse_invoice_date(payload.get("fecha"))
    subtotal = sum(money_decimal(i["total"]) for i in items)
    iva_rate = money_decimal(sri.get("ivaRate") or 15)
    iva = money_decimal(subtotal * iva_rate / Decimal("100"))
    total = money_decimal(subtotal + iva)
    clave = build_access_key(fecha, sri, secuencial)
    invoice = {
        "id": f"{sri['estab']}-{sri['ptoEmi']}-{secuencial}",
        "secuencial": secuencial,
        "claveAcceso": clave,
        "autorizacion": "",
        "fecha": fecha.isoformat(),
        "pac": patient_id,
        "esp": payload.get("esp") or patient.get("esp") or "General",
        "serv": ", ".join(i["desc"] for i in items),
        "items": items,
        "sub": float(subtotal),
        "iva": float(iva),
        "total": float(total),
        "pago": payload.get("pago") or "Efectivo",
        "estado": "Pendiente SRI",
        "sriEstado": "GENERADO",
        "sriMensaje": "XML generado pendiente de envio",
        "sri": {**sri, "ivaRate": float(iva_rate)},
        "emailAuto": False,
        "emailEnviado": False,
        "createdAt": now_iso(),
        "createdBy": user.get("email") if user else "sistema",
    }
    invoice["xml"] = build_invoice_xml(invoice, patient, config)
    set_json_key(conn, "nextIds", next_ids)
    return invoice, patient, config


def send_invoice_to_sri(invoice, cert_info=None):
    invoice["signedXml"] = sign_invoice_xml(invoice["xml"], cert_info)
    reception = sri_recepcion(invoice["signedXml"], invoice["sri"]["ambiente"])
    invoice["sriRecepcion"] = reception
    if reception.get("estado") != "RECIBIDA":
        invoice["estado"] = "Devuelta SRI"
        invoice["sriEstado"] = reception.get("estado") or "DEVUELTA"
        invoice["sriMensaje"] = "; ".join(m.get("mensaje", "") for m in reception.get("mensajes", [])) or "Comprobante devuelto por el SRI"
        return invoice
    invoice["estado"] = "Recibida SRI"
    invoice["sriEstado"] = "RECIBIDA"
    invoice["sriMensaje"] = "Comprobante recibido; consultando autorizacion"
    last_auth = None
    for _ in range(max(1, SRI_AUTH_RETRIES)):
        last_auth = sri_autorizacion(invoice["claveAcceso"], invoice["sri"]["ambiente"])
        if last_auth.get("estado") in ("AUTORIZADO", "NO AUTORIZADO"):
            break
        time.sleep(max(0.1, SRI_AUTH_SLEEP_SECONDS))
    invoice["sriAutorizacion"] = last_auth or {}
    if last_auth and last_auth.get("estado") == "AUTORIZADO":
        invoice["estado"] = "Autorizado SRI"
        invoice["sriEstado"] = "AUTORIZADO"
        invoice["autorizacion"] = last_auth.get("numeroAutorizacion") or invoice["claveAcceso"]
        invoice["fechaAutorizacion"] = last_auth.get("fechaAutorizacion") or now_iso()
        if last_auth.get("comprobante"):
            invoice["authorizedXml"] = last_auth["comprobante"]
        invoice["sriMensaje"] = "Autorizado por el SRI"
    elif last_auth and last_auth.get("estado") == "NO AUTORIZADO":
        invoice["estado"] = "No autorizado SRI"
        invoice["sriEstado"] = "NO AUTORIZADO"
        invoice["sriMensaje"] = "; ".join(m.get("mensaje", "") for m in last_auth.get("mensajes", [])) or "No autorizado por el SRI"
    else:
        invoice["estado"] = "En proceso SRI"
        invoice["sriEstado"] = "EN_PROCESO"
        invoice["sriMensaje"] = "El SRI aun no devuelve autorizacion; usa Reintentar SRI"
    return invoice


def save_invoice_record(conn, invoice):
    invoices = get_json_key(conn, "facturas", []) or []
    invoices = [f for f in invoices if f.get("id") != invoice.get("id")]
    invoices.insert(0, invoice)
    set_json_key(conn, "facturas", invoices)



def invoice_context(conn, invoice_id):
    invoices = get_json_key(conn, "facturas", []) or []
    invoice = next((f for f in invoices if str(f.get("id")) == str(invoice_id)), None)
    if not invoice:
        raise SRIIntegrationError("Factura no encontrada")
    patients = get_json_key(conn, "pacientes", []) or []
    patient = find_patient(patients, patient_id=int(invoice.get("pac") or 0)) or {}
    config = get_json_key(conn, "config", {}) or {}
    if not invoice.get("sri"):
        invoice["sri"] = sri_config(config)
    if not invoice.get("secuencial"):
        invoice["secuencial"] = clean_digits(invoice.get("id"))[-9:].zfill(9)
    if not invoice.get("xml"):
        invoice["xml"] = build_invoice_xml(invoice, patient, config)
    return invoice, patient, config


def persist_invoice_update(conn, invoice):
    invoices = get_json_key(conn, "facturas", []) or []
    for idx, item in enumerate(invoices):
        if str(item.get("id")) == str(invoice.get("id")):
            invoices[idx] = invoice
            set_json_key(conn, "facturas", invoices)
            return
    invoices.insert(0, invoice)
    set_json_key(conn, "facturas", invoices)
def fix_text(value):
    if isinstance(value, str):
        for bad, good in MOJIBAKE_REPLACEMENTS.items():
            value = value.replace(bad, good)
        return value
    if isinstance(value, list):
        return [fix_text(v) for v in value]
    if isinstance(value, dict):
        return {k: fix_text(v) for k, v in value.items()}
    return value


_MISSING = object()


def get_json_key(conn, key, default=None):
    cache = getattr(conn, "json_cache", None)
    text = cache.get(key, _MISSING) if cache is not None else _MISSING
    if text is _MISSING:
        row = conn.execute("select value from app_data where key = ?", (key,)).fetchone()
        text = row["value"] if row else None
        if cache is not None:
            cache[key] = text
    # A fresh object on every call: callers may mutate what they receive.
    return json.loads(text) if text is not None else default


def set_json_key(conn, key, value):
    value = fix_text(value)
    text = json.dumps(value, ensure_ascii=False)
    conn.execute(
        "insert into app_data(key,value,updated_at) values(?,?,?) "
        "on conflict(key) do update set value=excluded.value, updated_at=excluded.updated_at",
        (key, text, now_iso()),
    )
    cache = getattr(conn, "json_cache", None)
    if cache is not None:
        cache[key] = text


def audit(conn, user, action, key, detail=None):
    conn.execute(
        "insert into audit_log(ts,user_id,email,action,data_key,detail) values(?,?,?,?,?,?)",
        (
            now_iso(),
            user.get("id") if user else None,
            user.get("email") if user else "",
            action,
            key,
            json.dumps(detail or {}, ensure_ascii=False),
        ),
    )


def user_display_name(user):
    return (str(user.get("name", "")) + " " + str(user.get("last", ""))).strip() or user.get("email", "")


def public_user(user):
    return {
        "id": user.get("id"),
        "name": user.get("name", ""),
        "last": user.get("last", ""),
        "email": user.get("email", ""),
        "rol": user.get("rol", "recepcion"),
        "permissions": clean_permissions(user.get("permissions"), user.get("rol", "recepcion")),
        "patientId": user.get("patientId"),
        "medicoId": user.get("medicoId"),
        "superadminMedico": bool(user.get("superadminMedico")) and user.get("rol") == "admin",
        "createdAt": user.get("createdAt", ""),
        "estado": user.get("estado", "activo"),
        "emailVerified": user_email_verified(user),
    }


def clean_permissions(permissions, role):
    if role == "admin":
        return sorted(ALLOWED_PERMISSIONS)
    if role == "paciente":
        return []
    if not isinstance(permissions, list) or not permissions:
        permissions = ROLE_DEFAULT_PERMISSIONS.get(role, ROLE_DEFAULT_PERMISSIONS["recepcion"])
    if role in ("recepcion", "secretaria"):
        permissions = list(dict.fromkeys([*permissions, "servicios", "examenes", "certificados"]))
    return [p for p in permissions if p in ALLOWED_PERMISSIONS and p != "config"]



def lookup_key(value):
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def resolve_medico_id(conn, payload, name="", last="", email=""):
    medicos = get_json_key(conn, "medicos", []) or []
    raw_id = payload.get("medicoId") or payload.get("medico_id") or payload.get("med")
    if raw_id not in (None, ""):
        try:
            medico_id = int(raw_id)
        except (TypeError, ValueError):
            medico_id = 0
        if medico_id and any(int(m.get("id", 0)) == medico_id for m in medicos):
            return medico_id
        return 0
    email_key = (email or "").strip().lower()
    if email_key:
        match = next((m for m in medicos if (m.get("email") or "").strip().lower() == email_key), None)
        if match:
            return int(match.get("id") or 0)
    wanted = lookup_key(f"{name} {last}")
    if wanted:
        for medico in medicos:
            med_key = lookup_key(medico.get("nombre", ""))
            if wanted in med_key or med_key in wanted:
                return int(medico.get("id") or 0)
    return 0

def can_save_key(user, key):
    role = user.get("rol", "recepcion")
    if key not in {"citas","cajas","facturas","notas","recetas","archivosClinicos","pacientes","medicos","especialidades","seguros","quirofanos","equipos","stockQx","servicios","examenes","cotizaciones","cie10","config","nextIds"}:
        return False
    if role == "admin":
        return True
    if role == "medico" and key not in ("notas", "recetas", "archivosClinicos", "nextIds"):
        return False
    if key in ("servicios", "examenes"):
        return role in ("recepcion", "secretaria")
    perms = set(clean_permissions(user.get("permissions"), role))
    key_map = {
        "citas": "agenda",
        "cajas": "caja",
        "facturas": "facturacion",
        "notas": "hce",
        "recetas": "hce",
        "archivosClinicos": "hce",
        "pacientes": "pacientes",
        "medicos": "medicos",
        "especialidades": "especialidades",
        "seguros": "seguros",
        "quirofanos": "quirofanos",
        "equipos": "quirofanos",
        "stockQx": "quirofanos",
        "servicios": "servicios",
        "examenes": "examenes",
        "cotizaciones": "examenes",
    }
    if key == "pacientes" and ({"agenda", "hce"} & perms):
        return True
    if key == "facturas" and "caja" in perms:
        return True
    if key == "nextIds" and perms:
        return True
    return key in key_map and key_map[key] in perms


def remove_demo_revenue(conn):
    migration_key = "migration_demo_revenue_v1"
    if get_json_key(conn, migration_key):
        return
    invoices = get_json_key(conn, "facturas", []) or []
    seeds = {
        "001-001-000001842": (1, 85, 12.75, 97.75, "Pagado"),
        "001-001-000001843": (2, 85, 12.75, 97.75, "Seguro"),
        "001-001-000001844": (4, 70, 10.5, 80.5, "Pagado"),
    }
    def is_demo(invoice):
        signature = tuple(invoice.get(k) for k in ("pac", "sub", "iva", "total", "estado"))
        return (invoice.get("id") in seeds
                and signature == seeds[invoice["id"]]
                and invoice.get("fecha") == "2025-06-16"
                and not any(invoice.get(k) for k in ("sri", "claveAcceso", "createdAt", "signedXml")))
    removed = [invoice for invoice in invoices if is_demo(invoice)]
    if removed:
        set_json_key(conn, "backup_demo_revenue_v1", removed)
        set_json_key(conn, "facturas", [invoice for invoice in invoices if not is_demo(invoice)])
        audit(conn, None, "remove_demo_revenue", "facturas", {"count": len(removed)})
    set_json_key(conn, migration_key, {"completedAt": now_iso(), "removed": len(removed)})


def reset_requested_demo_data(conn):
    key = "migration_reset_demo_20260908_v1"
    if get_json_key(conn, key):
        return
    invoices = get_json_key(conn, "facturas", []) or []
    appointments = get_json_key(conn, "citas", []) or []
    examples = {
        "001-001-000001842": ("2025-06-16", 97.75),
        "001-001-000001843": ("2025-06-16", 97.75),
        "001-001-000001844": ("2025-06-16", 80.5),
        "001-001-000001845": ("2026-07-16", 46),
    }
    def is_example(invoice):
        expected = examples.get(str(invoice.get("id")))
        return bool(expected and (invoice.get("fecha"), invoice.get("total")) == expected
                    and invoice.get("estado") != "Autorizado SRI")
    removed = [f for f in invoices if is_example(f)]
    set_json_key(conn, "backup_reset_demo_20260908_v1", {"facturas": removed, "citas": appointments})
    set_json_key(conn, "facturas", [f for f in invoices if not is_example(f)])
    set_json_key(conn, "citas", [])
    summary = {"completedAt": now_iso(), "invoicesRemoved": len(removed), "appointmentsRemoved": len(appointments)}
    audit(conn, None, "reset_requested_demo_data", "citas", summary)
    set_json_key(conn, key, summary)


def schema_is_current():
    try:
        with db(read_only=True) as conn:
            row = conn.execute("select value from app_data where key = ?", ("migration_schema_version",)).fetchone()
            return bool(row) and json.loads(row["value"]).get("version") == SCHEMA_VERSION
    except Exception:
        return False


def migrate_clinical_files(conn):
    """Move embedded documents into clinical_files keeping a single copy in memory."""
    from medicg.files import file_key
    row = conn.execute("select value from app_data where key = ?", ("archivosClinicos",)).fetchone()
    if not row:
        set_json_key(conn, "archivosClinicos", {})
        return
    text = row["value"]
    row = None
    if '"dataUrl"' not in text:
        return
    files = json.loads(text)
    text = None
    moved = 0
    now = time.time()
    for pid, entries in (files.items() if isinstance(files, dict) else []):
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or "dataUrl" not in entry:
                continue
            data_url = entry.pop("dataUrl")
            if isinstance(data_url, str) and data_url.startswith("data:"):
                conn.execute(
                    "insert into clinical_files(file_key,patient_id,file_id,mime,size,data_url,created_at) values(?,?,?,?,?,?,?) "
                    "on conflict(file_key) do update set data_url=excluded.data_url",
                    (file_key(pid, entry.get("id")), str(pid), str(entry.get("id")), str(entry.get("mime") or ""), int(entry.get("size") or 0), data_url, now),
                )
                entry["hasFile"] = True
                moved += 1
            data_url = None
    conn.execute(
        "update app_data set value = ?, updated_at = ? where key = ?",
        (json.dumps(files, ensure_ascii=False), now_iso(), "archivosClinicos"),
    )
    conn.json_cache.pop("archivosClinicos", None)
    audit(conn, None, "migrate_clinical_files", "archivosClinicos", {"files": moved})


def init_db():
    """Create/upgrade the schema. Cold starts on an up-to-date database only run
    one read-only query instead of rewriting every stored collection."""
    if schema_is_current():
        return
    with db() as conn:
        conn.execute(
            "create table if not exists app_data("
            "key text primary key, value text not null, updated_at text not null)"
        )
        conn.execute(table_postgres_audit() if DB_DRIVER == "postgres" else table_sqlite_audit())
        conn.execute(
            "create table if not exists sessions("
            "token_hash text primary key, user_id integer not null, expires_at real not null, created_at text not null)"
        )
        conn.execute("create table if not exists telehealth_native(appointment_id text primary key, state text not null, expires_at integer not null)")
        conn.execute("create table if not exists cash_requests(request_id text primary key, payload_hash text not null, invoice_id text not null, created_at text not null)")
        from medicg.files import table_sql as clinical_files_table
        conn.execute(clinical_files_table())
        conn.execute("create index if not exists clinical_files_patient_idx on clinical_files(patient_id)")
        from medicg.pharmacy import table_sql as pharmacy_moves_table
        conn.execute(pharmacy_moves_table())
        conn.execute("create index if not exists pharmacy_moves_product_idx on pharmacy_moves(product_id, ts)")
        from medicg.reminders import table_sql as reminder_table
        conn.execute(reminder_table())
        conn.execute("create index if not exists reminder_log_cita_idx on reminder_log(cita_id, channel, kind)")
        conn.execute("create table if not exists login_attempts(attempt_key text primary key, failures integer not null, first_at double precision not null, locked_until double precision not null)")
        conn.execute("create index if not exists sessions_expires_idx on sessions(expires_at)")
        conn.execute("create index if not exists sessions_user_idx on sessions(user_id)")
        conn.execute("create index if not exists audit_ts_idx on audit_log(ts)")
        conn.execute("create index if not exists audit_key_idx on audit_log(data_key)")
        conn.execute("delete from sessions where expires_at < ?", (time.time(),))
        remove_demo_revenue(conn)
        reset_requested_demo_data(conn)
        users = get_json_key(conn, "users")
        if not users:
            users = [
                {
                    "id": 1,
                    "name": "Admin",
                    "last": "Sistema",
                    "email": ADMIN_EMAIL,
                    "passHash": hash_password(ADMIN_PASSWORD),
                    "rol": "admin",
                    "permissions": clean_permissions(None, "admin"),
                    "estado": "activo",
                    "emailVerified": True,
                    "createdAt": now_iso(),
                }
            ]
            set_json_key(conn, "users", users)
        else:
            changed = False
            for user in users:
                if user.get("pass") and not user.get("passHash"):
                    user["passHash"] = hash_password(user.pop("pass"))
                    changed = True
                if "emailVerified" not in user:
                    user["emailVerified"] = user.get("estado", "activo") == "activo"
                    changed = True
                cleaned_permissions = clean_permissions(user.get("permissions"), user.get("rol", "recepcion"))
                if user.get("permissions") != cleaned_permissions:
                    user["permissions"] = cleaned_permissions
                    changed = True
                if user.get("rol") == "medico" and not user.get("medicoId"):
                    medico_id = resolve_medico_id(conn, {}, user.get("name", ""), user.get("last", ""), user.get("email", ""))
                    if medico_id:
                        user["medicoId"] = medico_id
                        changed = True
            fixed_users = fix_text(users)
            if fixed_users != users:
                users = fixed_users
                changed = True
            if changed:
                set_json_key(conn, "users", users)
        # One collection at a time so large databases never sit in memory all at once.
        stored_keys = [r["key"] for r in conn.execute("select key from app_data").fetchall()]
        for stored_key in stored_keys:
            if stored_key == "archivosClinicos" or stored_key.startswith("backup_"):
                continue
            row = conn.execute("select value from app_data where key = ?", (stored_key,)).fetchone()
            if not row:
                continue
            value = json.loads(row["value"])
            row = None
            fixed_value = fix_text(value)
            if fixed_value != value:
                set_json_key(conn, stored_key, fixed_value)
            value = fixed_value = None
            conn.json_cache.clear()
        next_ids = get_json_key(conn, "nextIds")
        if not next_ids:
            set_json_key(conn, "nextIds", {"pac": 6, "med": 5, "cita": 6, "fac": 1845, "esp": 7, "seg": 5, "user": 2, "qx": 3, "eq": 3, "st": 3, "caja": 1, "serv": 6, "exam": 6, "cot": 1})
        else:
            changed_ids = False
            for key, value in {"qx": 3, "eq": 3, "st": 3, "caja": 1, "serv": 6, "exam": 6, "cot": 1}.items():
                if key not in next_ids:
                    next_ids[key] = value
                    changed_ids = True
            if changed_ids:
                set_json_key(conn, "nextIds", next_ids)
        migrate_clinical_files(conn)
        if get_json_key(conn, "notificaciones") is None:
            set_json_key(conn, "notificaciones", [])
        if get_json_key(conn, "sriCertificate") is None:
            set_json_key(conn, "sriCertificate", {})
        if not os.environ.get("ADMIN_PASSWORD") and os.environ.get("VERCEL"):
            log.warning("ADMIN_PASSWORD no está configurado; cambia la clave del administrador inicial.")
        set_json_key(conn, "migration_schema_version", {"version": SCHEMA_VERSION, "completedAt": now_iso()})


def make_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressed = len(body) > 1400 and "gzip" in (handler.headers.get("Accept-Encoding", "") or "").lower()
    if compressed:
        body = gzip.compress(body, compresslevel=5)
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    if compressed:
        handler.send_header("Content-Encoding", "gzip")
    handler.send_header("Cache-Control", "no-store")
    origin = handler.headers.get("Origin", "")
    if not ALLOWED_ORIGINS or origin in ALLOWED_ORIGINS:
        handler.send_header("Access-Control-Allow-Origin", origin or "*")
    handler.send_header("Vary", "Origin, Accept-Encoding")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def make_html_response(handler, status, html):
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("X-Content-Type-Options", "nosniff")
    handler.send_header("X-Frame-Options", "DENY")
    handler.send_header("Referrer-Policy", "no-referrer")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_body(handler):
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length < 0:
        raise ValueError("invalid_length")
    if length > MAX_BODY_BYTES:
        raise ValueError("payload_too_large")
    payload = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
    if not isinstance(payload, dict):
        raise ValueError("invalid_payload")
    return payload


def auth_user(handler):
    token = handler.headers.get("Authorization", "").replace("Bearer ", "").strip()
    if not token:
        return None
    with db(read_only=True) as conn:
        row = conn.execute(
            "select user_id, expires_at from sessions where token_hash = ?",
            (token_hash(token),),
        ).fetchone()
        if not row or row["expires_at"] < time.time():
            return None
        users = get_json_key(conn, "users", [])
    user = next((u for u in users if int(u.get("id", 0)) == int(row["user_id"])), None)
    if not user or user.get("estado", "activo") != "activo":
        return None
    return user


def split_full_name(value):
    parts = [p for p in (value or "").strip().split() if p]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return " ".join(parts[:-1]), parts[-1]


def next_id(next_ids, key, fallback):
    current = int(next_ids.get(key, fallback) or fallback)
    next_ids[key] = current + 1
    return current


def find_patient(patients, email="", cedula="", patient_id=0):
    email = (email or "").strip().lower()
    cedula = (cedula or "").strip()
    for patient in patients:
        if patient_id and int(patient.get("id", 0)) == int(patient_id):
            return patient
        if cedula and (patient.get("cedula") or "").strip() == cedula:
            return patient
        if email and (patient.get("email") or "").strip().lower() == email:
            return patient
    return None


def upsert_patient_from_payload(conn, payload):
    patients = get_json_key(conn, "pacientes", []) or []
    next_ids = get_json_key(conn, "nextIds", {}) or {}
    email = (payload.get("email") or "").strip().lower()
    cedula = (payload.get("cedula") or payload.get("documento") or "").strip()
    name = (payload.get("name") or payload.get("nombres") or "").strip()
    last = (payload.get("last") or payload.get("apellidos") or "").strip()
    full_name = (payload.get("nombreCompleto") or payload.get("paciente") or "").strip()
    if not name and full_name:
        name, last = split_full_name(full_name)
    patient = find_patient(patients, email=email, cedula=cedula)
    created = False
    if not patient:
        patient = {
            "id": next_id(next_ids, "pac", len(patients) + 1),
            "nombres": name,
            "apellidos": last,
            "cedula": cedula,
            "fnac": payload.get("fnac") or "",
            "genero": payload.get("genero") or "",
            "tel": payload.get("tel") or payload.get("phone") or "",
            "email": email,
            "dir": payload.get("dir") or "",
            "seguro": payload.get("seguro") or "",
            "afiliado": payload.get("afiliado") or "",
            "sangre": payload.get("sangre") or "",
            "alergias": payload.get("alergias") or "",
            "antec": payload.get("antec") or "",
            "esp": payload.get("esp") or payload.get("especialidad") or "",
            "ultima": "",
            "origen": payload.get("origen") or "Landing pública",
            "createdAt": now_iso(),
        }
        patients.append(patient)
        created = True
    else:
        updates = {
            "nombres": name,
            "apellidos": last,
            "cedula": cedula,
            "fnac": payload.get("fnac") or "",
            "genero": payload.get("genero") or "",
            "tel": payload.get("tel") or payload.get("phone") or "",
            "email": email,
            "dir": payload.get("dir") or "",
            "seguro": payload.get("seguro") or "",
            "afiliado": payload.get("afiliado") or "",
            "sangre": payload.get("sangre") or "",
            "alergias": payload.get("alergias") or "",
            "antec": payload.get("antec") or "",
            "esp": payload.get("esp") or payload.get("especialidad") or "",
        }
        for key, value in updates.items():
            if value and not patient.get(key):
                patient[key] = value
    set_json_key(conn, "pacientes", patients)
    set_json_key(conn, "nextIds", next_ids)
    return patient, created


PUBLIC_APPOINTMENT_HOURS = [
    "07:00", "07:30", "08:00", "08:30", "09:00", "09:30",
    "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
    "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00",
]
CANCELLED_APPOINTMENT_STATES = {
    "cancelada", "cancelado", "anulada", "anulado", "no asistio", "no asistida",
}


class AppointmentError(Exception):
    pass


def appointment_state(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return text.strip().lower()


def appointment_blocks_slot(appointment):
    state = appointment_state(appointment.get("estado"))
    return not state or state not in CANCELLED_APPOINTMENT_STATES


def appointment_conflict(appointments, med, fecha, hora, ignore_id=0, esp=""):
    med = int(med or 0)
    ignore_id = int(ignore_id or 0)
    fecha = str(fecha or "")
    hora = str(hora or "")
    esp = str(esp or "")
    for appointment in appointments:
        if ignore_id and int(appointment.get("id") or 0) == ignore_id:
            continue
        if not appointment_blocks_slot(appointment):
            continue
        if str(appointment.get("fecha") or "") != fecha or str(appointment.get("hora") or "") != hora:
            continue
        appointment_med = int(appointment.get("med") or 0)
        if med and appointment_med == med:
            return appointment
        if not med and appointment_med == 0 and (not esp or str(appointment.get("esp") or "") == esp):
            return appointment
    return None


def appointment_doctor_candidates(medicos, esp="", med=0):
    return [m for m in medicos
            if (not med or int(m.get("id") or 0) == int(med))
            and (not esp or esp in (m.get("esp"), m.get("esp2"), m.get("esp3"), m.get("esp4")))
            and appointment_state(m.get("estado", "activo")) not in ("inactivo", "inactive")]


def doctor_works_at(doctor, fecha, hora):
    import datetime
    import re
    day = datetime.date.fromisoformat(fecha)
    schedule = appointment_state(doctor.get("horario", ""))
    days = {"lun": 0, "mar": 1, "mie": 2, "jue": 3, "vie": 4, "sab": 5, "dom": 6}
    ranges = re.findall(r"(lun|mar|mie|jue|vie|sab|dom)\w*\s*(?:-|a)\s*(lun|mar|mie|jue|vie|sab|dom)", schedule)
    allowed = set()
    for start, end in ranges:
        i = days[start]
        for _ in range(7):
            allowed.add(i)
            if i == days[end]: break
            i = (i + 1) % 7
    if not ranges:
        allowed = {number for name, number in days.items() if name in schedule}
    if allowed and day.weekday() not in allowed:
        return False
    periods = re.findall(r"(\d{1,2}:\d{2})\s*(?:-|a)\s*(\d{1,2}:\d{2})", schedule)
    def minutes(value):
        h, m = map(int, value.split(":"))
        return h * 60 + m
    if periods and not any(minutes(start) <= minutes(hora) and minutes(hora) + 30 <= minutes(end) for start, end in periods):
        return False
    return True


def find_available_doctor(appointments, medicos, esp, med, fecha, hora, ignore_id=0):
    import datetime
    # Ecuador continental uses UTC-05:00.
    clinic_timezone = datetime.timezone(datetime.timedelta(hours=-5))
    try:
        day = datetime.date.fromisoformat(str(fecha))
        instant = datetime.datetime.fromisoformat(str(fecha) + "T" + str(hora)).replace(tzinfo=clinic_timezone)
    except (ValueError, TypeError):
        raise AppointmentError("Selecciona una fecha y hora válidas.")
    if instant <= datetime.datetime.now(clinic_timezone):
        raise AppointmentError("Selecciona una fecha y hora futuras.")
    if hora not in PUBLIC_APPOINTMENT_HOURS:
        raise AppointmentError("Selecciona un horario válido de atención.")
    candidates = appointment_doctor_candidates(medicos, esp, med)
    if not candidates:
        raise AppointmentError("No hay un médico activo para la especialidad seleccionada.")
    for doctor in candidates:
        doctor_id = int(doctor["id"])
        if doctor_works_at(doctor, str(fecha), hora) and not appointment_conflict(appointments, doctor_id, fecha, hora, ignore_id=ignore_id):
            return doctor_id
    raise AppointmentError("El médico no está disponible en ese horario. Selecciona otra fecha u hora.")


def available_appointment_slots(appointments, medicos, esp="", med=0, fecha="", ignore_id=0):
    slots = []
    for hour in PUBLIC_APPOINTMENT_HOURS:
        try:
            assigned_med = find_available_doctor(appointments, medicos, esp, med, fecha, hour, ignore_id=ignore_id)
        except AppointmentError:
            continue
        slots.append({"hora": hour, "med": assigned_med})
    return slots


def create_online_appointment(conn, patient, payload, user=None):
    appointments = get_json_key(conn, "citas", []) or []
    medicos = get_json_key(conn, "medicos", []) or []
    next_ids = get_json_key(conn, "nextIds", {}) or {}
    esp = (payload.get("esp") or payload.get("especialidad") or patient.get("esp") or "").strip()
    fecha = (payload.get("fecha") or "").strip()
    hora = (payload.get("hora") or "08:00").strip()
    med = int(payload.get("med") or payload.get("medicoId") or 0)
    med = find_available_doctor(appointments, medicos, esp, med, fecha, hora)
    appointment = {
        "id": next_id(next_ids, "cita", len(appointments) + 1),
        "pac": int(patient.get("id")),
        "med": med,
        "esp": esp,
        "tipo": payload.get("tipo") or "Reserva online",
        "fecha": fecha,
        "hora": hora,
        "motivo": payload.get("motivo") or "",
        "estado": "Solicitada online",
        "notif": "Sistema",
        "origen": payload.get("origen") or "Landing publica",
        "createdAt": now_iso(),
        "createdBy": user.get("email") if user else "paciente-web",
    }
    appointments.append(appointment)
    set_json_key(conn, "citas", appointments)
    set_json_key(conn, "nextIds", next_ids)
    notifications = get_json_key(conn, "notificaciones", []) or []
    notifications.insert(0, {
        "id": f"web-{appointment['id']}",
        "tipo": "cita_online",
        "fecha": now_iso(),
        "titulo": "Nueva cita solicitada desde la landing",
        "detalle": f"{patient.get('nombres', '')} {patient.get('apellidos', '')} pidio cita de {esp} el {appointment['fecha']} a las {appointment['hora']}",
        "citaId": appointment["id"],
        "leida": False,
    })
    set_json_key(conn, "notificaciones", notifications[:80])
    return appointment


def patient_portal_payload(conn, user):
    patients = get_json_key(conn, "pacientes", []) or []
    patient = find_patient(
        patients,
        email=user.get("email", ""),
        patient_id=int(user.get("patientId") or 0),
    )
    if not patient:
        return None
    patient_id = int(patient.get("id"))
    appointments = [c for c in (get_json_key(conn, "citas", []) or []) if int(c.get("pac", 0)) == patient_id]
    notes = (get_json_key(conn, "notas", {}) or {}).get(str(patient_id), []) or (get_json_key(conn, "notas", {}) or {}).get(patient_id, []) or []
    prescriptions = (get_json_key(conn, "recetas", {}) or {}).get(str(patient_id), []) or (get_json_key(conn, "recetas", {}) or {}).get(patient_id, []) or []
    files = (get_json_key(conn, "archivosClinicos", {}) or {}).get(str(patient_id), []) or (get_json_key(conn, "archivosClinicos", {}) or {}).get(patient_id, []) or []
    invoices = [f for f in (get_json_key(conn, "facturas", []) or []) if int(f.get("pac", 0)) == patient_id]
    from medicg.files import strip_entry, strip_invoices
    files = [strip_entry(f) for f in files]
    invoices = strip_invoices(invoices)
    return {
        "patient": patient,
        "appointments": sorted(appointments, key=lambda c: (c.get("fecha", ""), c.get("hora", "")), reverse=True),
        "notes": sorted(notes, key=lambda n: n.get("fecha", ""), reverse=True),
        "prescriptions": sorted(prescriptions, key=lambda r: r.get("fecha", ""), reverse=True),
        "files": sorted(files, key=lambda f: f.get("fecha", ""), reverse=True),
        "invoices": sorted(invoices, key=lambda f: f.get("fecha", ""), reverse=True),
    }


def public_catalog_payload(conn):
    config = get_json_key(conn, "config", {}) or {}
    public_config = {k: config.get(k, "") for k in ("nombre", "dir", "tel", "wa", "email", "color", "logo")}
    return {
        "config": public_config,
        "especialidades": [e for e in (get_json_key(conn, "especialidades", []) or []) if e.get("estado", "activo") == "activo"],
        "medicos": get_json_key(conn, "medicos", []) or [],
        "servicios": get_json_key(conn, "servicios", []) or [],
    }


def sanitize_app_data_for_user(data, user=None):
    from medicg.files import strip_map, strip_invoices
    data = {k:v for k,v in (data or {}).items() if not k.startswith(("backup_", "migration_"))}
    if "archivosClinicos" in data:
        data["archivosClinicos"] = strip_map(data["archivosClinicos"])
    if "facturas" in data:
        data["facturas"] = strip_invoices(data["facturas"])
    if "pacientes" in data:
        data["pacientes"] = [p for p in (data["pacientes"] or []) if not p.get("deletedAt")]
    if user and user.get("rol") == "medico":
        from medicg.doctor_scope import filter_data
        data = filter_data(data, user)
    data.pop("outgoingEmailPrivate", None)
    data.pop("remindersPrivate", None)
    data.pop("outlookPendingPrivate", None)
    saved_cert = data.pop("sriCertificate", None)
    config = data.get("config") or {}
    if not isinstance(config, dict):
        config = {}
    data["config"] = config
    if isinstance(config, dict):
        config = dict(config)
        for secret_key in ("sriCertP12Base64", "sriCertPassword", "sriCertificate", "sriCertificatePassword"):
            config.pop(secret_key, None)
        data["config"] = config
    data["users"] = [public_user(u) for u in data.get("users", []) if user and (user.get("rol") == "admin" or u.get("id") == user.get("id"))]
    if not user or user.get("rol") != "admin":
        data["config"].pop("wtoken", None)
        perms = set(clean_permissions((user or {}).get("permissions"), (user or {}).get("rol", "pendiente")))
        if "hce" not in perms:
            for key in ("notas", "recetas", "archivosClinicos", "signosVitales", "certificados", "ordenesLab"):
                data[key] = {}
            data["pacientes"] = [{k:v for k,v in p.items() if k not in ("alergias","antec","sangre","antecedentes")} for p in (data.get("pacientes") or [])]
    data["sriCertificateStatus"] = saved_sri_certificate_status(saved_cert)
    return data


def save_normalizer(key):
    from medicg.files import strip_entry, strip_map, strip_invoice, strip_invoices
    if key == "archivosClinicos":
        def normalize(value):
            if isinstance(value, list):
                value = [strip_entry(e) for e in value]
            elif isinstance(value, dict):
                value = strip_entry(value) if "dataUrl" in value else strip_map(value)
            return fix_text(value)
        return normalize
    if key == "facturas":
        return lambda value: fix_text(strip_invoices(value) if isinstance(value, list) else strip_invoice(value))
    return fix_text


def client_ip(handler):
    forwarded = handler.headers.get("X-Forwarded-For", "") or handler.headers.get("X-Real-Ip", "")
    return (forwarded.split(",")[0].strip() if forwarded else handler.client_address[0]) or "unknown"


def login_throttle_keys(handler, email):
    return ["email:" + email, "ip:" + client_ip(handler)]


def login_locked(conn, keys):
    now = time.time()
    for key in keys:
        row = conn.execute("select locked_until from login_attempts where attempt_key = ?", (key,)).fetchone()
        if row and float(row["locked_until"]) > now:
            return int(float(row["locked_until"]) - now) + 1
    return 0


def register_login_failure(conn, keys):
    now = time.time()
    for key in keys:
        limit = LOGIN_MAX_FAILURES * (5 if key.startswith("ip:") else 1)
        row = conn.execute("select failures, first_at from login_attempts where attempt_key = ?", (key,)).fetchone()
        if not row or float(row["first_at"]) < now - LOGIN_WINDOW_SECONDS:
            failures, first_at = 1, now
        else:
            failures, first_at = int(row["failures"]) + 1, float(row["first_at"])
        locked_until = now + LOGIN_WINDOW_SECONDS if failures >= limit else 0
        conn.execute(
            "insert into login_attempts(attempt_key,failures,first_at,locked_until) values(?,?,?,?) "
            "on conflict(attempt_key) do update set failures=excluded.failures, first_at=excluded.first_at, locked_until=excluded.locked_until",
            (key, failures, first_at, locked_until),
        )


def clinical_file_allowed(conn, user, patient_id):
    if user.get("rol") == "paciente":
        return str(user.get("patientId") or "") == str(patient_id)
    if not can_save_key(user, "archivosClinicos"):
        return False
    if user.get("rol") == "medico":
        from medicg.doctor_scope import check_patient
        try:
            check_patient(conn, user, patient_id)
        except ValueError:
            return False
    return True


INVOICE_SRI_FIELDS = (
    "signedXml", "sriRecepcion", "estado", "sriEstado", "sriMensaje", "sriAutorizacion",
    "autorizacion", "fechaAutorizacion", "authorizedXml", "xml", "sri", "secuencial",
)
CLAIM_SECONDS = 180


def claim_invoice(invoice_id, field):
    """Mark an invoice as being processed so slow network work can run outside
    the global write lock without two users sending it twice."""
    with db() as conn:
        invoices = get_json_key(conn, "facturas", []) or []
        invoice = next((f for f in invoices if str(f.get("id")) == str(invoice_id)), None)
        if not invoice:
            raise SRIIntegrationError("Factura no encontrada")
        if float(invoice.get(field) or 0) > time.time() - CLAIM_SECONDS:
            return False
        invoice[field] = time.time()
        set_json_key(conn, "facturas", invoices)
    return True


def release_invoice(invoice_id, field, updates=None, user=None, action=None, detail=None):
    with db() as conn:
        invoices = get_json_key(conn, "facturas", []) or []
        invoice = next((f for f in invoices if str(f.get("id")) == str(invoice_id)), None)
        if not invoice:
            return None
        invoice.update(updates or {})
        invoice.pop(field, None)
        set_json_key(conn, "facturas", invoices)
        if action:
            audit(conn, user, action, "facturas", detail or {})
        return invoice


class MedicGHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".txt": "text/plain; charset=utf-8",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def send_head(self):
        from urllib.parse import unquote
        path = unquote(urlparse(self.path).path)
        requested = (BASE_DIR / path.lstrip("/")).resolve()
        assets = (BASE_DIR / "assets").resolve()
        if path not in ("/", "/index.html", "/config.js", "/favicon.ico") and not requested.is_relative_to(assets):
            self.send_error(404, "Not found")
            return None
        if requested.is_dir() and path != "/":
            self.send_error(404, "Not found")
            return None
        return super().send_head()

    def _guarded(self, route):
        started = time.time()
        try:
            return route()
        except (BrokenPipeError, ConnectionResetError):
            return None
        except Exception:
            log.exception("Unhandled error on %s %s", self.command, urlparse(self.path).path)
            try:
                return make_response(self, 500, {"error": "Ocurrió un error inesperado. Intenta nuevamente."})
            except Exception:
                return None
        finally:
            elapsed = (time.time() - started) * 1000
            if elapsed > 1500 and urlparse(self.path).path.startswith("/api/"):
                log.warning("Slow request %s %s %.0f ms", self.command, urlparse(self.path).path, elapsed)

    def do_GET(self):
        return self._guarded(self.route_GET)

    def do_POST(self):
        return self._guarded(self.route_POST)

    def route_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        if path in ("/health", "/api/health"):
            if "deep=1" in (parsed_url.query or ""):
                started = time.time()
                try:
                    with db(read_only=True) as conn:
                        conn.execute("select 1").fetchone()
                    return make_response(self, 200, {"ok": True, "db": DB_DRIVER, "dbMs": round((time.time() - started) * 1000), "schema": SCHEMA_VERSION})
                except Exception:
                    return make_response(self, 503, {"ok": False, "db": DB_DRIVER})
            return make_response(self, 200, {"ok": True, "db": DB_DRIVER})
        if path == "/api/public/options":
            with db(read_only=True) as conn:
                return make_response(self, 200, public_catalog_payload(conn))
        if path == "/api/public/availability":
            params = parse_qs(parsed_url.query)
            esp = (params.get("esp", [""])[0] or "").strip()
            fecha = (params.get("fecha", [""])[0] or "").strip()
            try:
                med = int(params.get("med", ["0"])[0] or 0)
            except Exception:
                med = 0
            try:
                ignore_id = int(params.get("ignoreId", ["0"])[0] or 0)
            except Exception:
                ignore_id = 0
            if not fecha:
                return make_response(self, 200, {"hours": PUBLIC_APPOINTMENT_HOURS, "slots": []})
            with db(read_only=True) as conn:
                appointments = get_json_key(conn, "citas", []) or []
                medicos = get_json_key(conn, "medicos", []) or []
                slots = available_appointment_slots(appointments, medicos, esp=esp, med=med, fecha=fecha, ignore_id=ignore_id)
            return make_response(self, 200, {"hours": PUBLIC_APPOINTMENT_HOURS, "slots": slots})
        if path == "/api/verify-email":
            token = parse_qs(urlparse(self.path).query).get("token", [""])[0]
            if not token:
                return make_html_response(self, 400, "<h1>Enlace inválido</h1><p>Falta el token de verificación.</p>")
            hashed_token = token_hash(token)
            with db() as conn:
                users = get_json_key(conn, "users", [])
                target = next((u for u in users if u.get("verifyTokenHash") == hashed_token), None)
                if not target:
                    return make_html_response(self, 404, "<h1>Enlace no encontrado</h1><p>Solicita un nuevo registro o contacta al administrador.</p>")
                if float(target.get("verifyExpiresAt") or 0) < time.time():
                    return make_html_response(self, 410, "<h1>Enlace expirado</h1><p>Regístrate nuevamente para recibir otro correo de verificación.</p>")
                target["emailVerified"] = True
                target["estado"] = "activo"
                target.pop("verifyTokenHash", None)
                target.pop("verifyExpiresAt", None)
                set_json_key(conn, "users", users)
                audit(conn, target, "verify_email", "users")
            return make_html_response(
                self,
                200,
                "<!doctype html><html lang='es'><meta charset='utf-8'>"
                "<title>Cuenta verificada</title>"
                "<body style='font-family:Arial,sans-serif;padding:32px;color:#1f2937;'>"
                "<h1>Correo verificado correctamente</h1>"
                "<p>Ya puedes iniciar sesión en Medic G. Si todavía no ves módulos, el administrador debe asignarte permisos.</p>"
                "<p><a href='/' style='color:#0d7a6b;font-weight:700;'>Ir al sistema</a></p>"
                "</body></html>",
            )
        if path == "/api/email/settings":
            user = auth_user(self)
            if not user or user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador configura el correo."})
            from medicg.mailer import public_settings
            with db(read_only=True) as conn:
                return make_response(self, 200, {"settings": public_settings(conn)})
        if path == "/api/clinical/templates":
            user = auth_user(self)
            if not user or not can_save_key(user, "notas"):
                return make_response(self, 403, {"error": "Acceso clínico restringido."})
            from medicg.clinical import PROFILES, VERSION, SOURCES
            return make_response(self, 200, {"profiles": PROFILES, "version": VERSION, "sources": SOURCES})
        if path == "/api/reminders/cron":
            # Daily Vercel cron. Idempotent and rate limited; with CRON_SECRET set, it must match.
            secret = os.environ.get("CRON_SECRET", "")
            if secret and self.headers.get("Authorization", "") != "Bearer " + secret:
                return make_response(self, 401, {"error": "No autorizado"})
            from medicg.reminders import run as run_reminders
            return make_response(self, 200, run_reminders(None, force=bool(secret)))
        if path in ("/api/reminders/settings", "/api/reminders/status"):
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "Sesión no válida"})
            from medicg.reminders import public_settings as reminder_settings, status as reminder_status
            with db(read_only=True) as conn:
                if path.endswith("settings"):
                    if user.get("rol") != "admin":
                        return make_response(self, 403, {"error": "Solo el administrador configura los recordatorios."})
                    return make_response(self, 200, {"settings": reminder_settings(conn)})
                if not can_save_key(user, "citas"):
                    return make_response(self, 403, {"error": "Sin permiso de agenda."})
                ids = [i for i in (parse_qs(parsed_url.query).get("ids", [""])[0] or "").split(",") if i][:300]
                return make_response(self, 200, {"status": reminder_status(conn, ids)})
        if path in ("/api/pharmacy/queue", "/api/pharmacy/kardex"):
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "Sesión no válida"})
            from medicg.pharmacy import queue as pharmacy_queue, kardex as pharmacy_kardex, PharmacyError
            params = parse_qs(parsed_url.query)
            try:
                with db(read_only=True) as conn:
                    if path.endswith("queue"):
                        result = pharmacy_queue(conn, user)
                    else:
                        result = pharmacy_kardex(conn, user, params.get("productId", [""])[0], params.get("limit", ["300"])[0])
                return make_response(self, 200, result)
            except (PharmacyError, ValueError) as exc:
                return make_response(self, 403, {"error": str(exc)})
        if path == "/api/telehealth":
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "Sesión no válida"})
            from medicg.telehealth import appointments
            with db(read_only=True) as conn:
                result = appointments(conn, user)
            return make_response(self, 200, result)
        if path == "/api/patients/trash":
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "Sesión no válida"})
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Papelera disponible solo para el administrador."})
            with db(read_only=True) as conn:
                patients = [p for p in (get_json_key(conn, "pacientes", []) or []) if p.get("deletedAt")]
            return make_response(self, 200, {"patients": patients})
        if path == "/api/data":
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "Sesión no válida"})
            if user.get("rol") not in ("admin", "recepcion", "secretaria", "medico"):
                return make_response(self, 403, {"error": "Acceso restringido. Usa el portal correspondiente a tu cuenta."})
            wanted = [k for k in (parse_qs(parsed_url.query).get("keys", [""])[0] or "").split(",") if k]
            with db(read_only=True) as conn:
                if wanted:
                    # Partial refresh; doctors also need the collections that define their scope.
                    needed = set(wanted) | ({"pacientes", "medicos", "citas"} if user.get("rol") == "medico" else set()) | {"config", "users"}
                    rows = [r for r in conn.execute("select key,value from app_data").fetchall() if r["key"] in needed]
                else:
                    rows = conn.execute("select key,value from app_data").fetchall()
            data = {row["key"]: json.loads(row["value"]) for row in rows}
            data = sanitize_app_data_for_user(data, user)
            if wanted:
                data = {k: v for k, v in data.items() if k in wanted or k == "sriCertificateStatus"}
            return make_response(self, 200, {"user": public_user(user), "data": data})
        if path == "/api/patient/portal":
            user = auth_user(self)
            if not user:
                return make_response(self, 401, {"error": "Sesión no válida"})
            if user.get("rol") != "paciente":
                return make_response(self, 403, {"error": "Portal disponible solo para pacientes"})
            with db(read_only=True) as conn:
                portal = patient_portal_payload(conn, user)
            if not portal:
                return make_response(self, 404, {"error": "No encontramos una ficha de paciente vinculada a tu correo"})
            return make_response(self, 200, {"user": public_user(user), "portal": portal})
        return super().do_GET()

    def route_POST(self):
        path = urlparse(self.path).path
        try:
            payload = read_body(self)
        except ValueError as exc:
            if str(exc) == "payload_too_large":
                return make_response(self, 413, {"error": "Archivo o solicitud demasiado grande"})
            return make_response(self, 400, {"error": "JSON inválido"})
        except Exception:
            return make_response(self, 400, {"error": "JSON inválido"})

        if path == "/api/login":
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            throttle_keys = login_throttle_keys(self, email)
            with db(read_only=True) as conn:
                users = get_json_key(conn, "users", [])
                wait_seconds = login_locked(conn, throttle_keys)
            if wait_seconds:
                return make_response(self, 429, {"error": f"Demasiados intentos fallidos. Espera {max(1, wait_seconds // 60)} minuto(s) e intenta nuevamente."})
            user = next((u for u in users if (u.get("email") or "").lower() == email), None)
            if not user or not verify_password(password, user.get("passHash") or user.get("pass")):
                with db(lock=None) as conn:
                    register_login_failure(conn, throttle_keys)
                return make_response(self, 401, {"error": "Correo o contraseña incorrectos"})
            if not user_email_verified(user) or user.get("estado") == "pendiente_verificacion":
                return make_response(self, 403, {"error": "Verifica tu correo electrónico antes de iniciar sesión"})
            if user.get("estado", "activo") != "activo":
                return make_response(self, 403, {"error": "Usuario no activo"})
            token = secrets.token_urlsafe(32)
            expires_at = time.time() + 24 * 3600
            with db(lock=None) as conn:
                conn.execute("delete from sessions where expires_at < ?", (time.time(),))
                conn.execute("delete from login_attempts where attempt_key = ?", (throttle_keys[0],))
                conn.execute(
                    "insert into sessions(token_hash,user_id,expires_at,created_at) values(?,?,?,?)",
                    (token_hash(token), user["id"], expires_at, now_iso()),
                )
                audit(conn, user, "login", "session")
            return make_response(self, 200, {"token": token, "user": public_user(user)})

        if path == "/api/resend-verification":
            email = (payload.get("email") or "").strip().lower()
            if not email:
                return make_response(self, 400, {"error": "Ingresa el correo registrado"})
            verify_token = secrets.token_urlsafe(32)
            verify_link = f"{app_base_url(self)}/api/verify-email?token={verify_token}"
            target_name = "Paciente"
            with db() as conn:
                users = get_json_key(conn, "users", [])
                target = next((u for u in users if (u.get("email") or "").lower() == email), None)
                if not target:
                    audit(conn, None, "resend_verification_unknown_email", "users", {"email": email})
                    return make_response(self, 200, {
                        "ok": True,
                        "emailSent": False,
                        "message": "Si el correo esta registrado, enviaremos un nuevo enlace de verificacion.",
                    })
                if user_email_verified(target) and target.get("estado") != "pendiente_verificacion":
                    return make_response(self, 200, {
                        "ok": True,
                        "emailSent": False,
                        "alreadyVerified": True,
                        "message": "Este correo ya esta verificado. Intenta iniciar sesion.",
                    })
                target["emailVerified"] = False
                target["estado"] = "pendiente_verificacion"
                target["verifyTokenHash"] = token_hash(verify_token)
                target["verifyExpiresAt"] = time.time() + 48 * 3600
                target_name = target.get("name") or target.get("nombres") or "Paciente"
                set_json_key(conn, "users", users)
                audit(conn, None, "resend_verification_requested", "users", {"email": email})
            email_sent, email_error = send_verification_email(email, target_name, verify_link)
            with db() as conn:
                audit(conn, None, "resend_verification_sent" if email_sent else "resend_verification_failed", "users", {
                    "email": email,
                    "sent": email_sent,
                    "error": email_error if not email_sent else "",
                })
            response = {
                "ok": True,
                "emailSent": email_sent,
                "message": "Te enviamos un nuevo correo de verificacion. Revisa tambien spam o promociones." if email_sent else "No se pudo enviar el correo. Revisa SMTP/Resend en Vercel y vuelve a intentar.",
            }
            if not email_sent:
                response["emailError"] = email_error
            if SHOW_VERIFICATION_LINK:
                response["verificationLink"] = verify_link
            return make_response(self, 200, response)
        if path == "/api/register":
            name = (payload.get("name") or "").strip()
            last = (payload.get("last") or "").strip()
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            if not name or not last or not email or len(password) < 6:
                return make_response(self, 400, {"error": "Completa nombre, apellido, correo y contraseña de mínimo 6 caracteres"})
            verify_token = secrets.token_urlsafe(32)
            verify_link = f"{app_base_url(self)}/api/verify-email?token={verify_token}"
            with db() as conn:
                users = get_json_key(conn, "users", [])
                if any((u.get("email") or "").lower() == email for u in users):
                    return make_response(self, 409, {"error": "Este correo ya está registrado"})
                patient, _ = upsert_patient_from_payload(conn, {
                    **payload,
                    "name": name,
                    "last": last,
                    "email": email,
                    "origen": "Registro web",
                })
                next_ids = get_json_key(conn, "nextIds", {})
                next_ids["user"] = max(int(next_ids.get("user") or 1), max((int(u.get("id") or 0) for u in users), default=0) + 1)
                new_id = next_id(next_ids, "user", len(users) + 1)
                new_user = {
                    "id": new_id,
                    "name": name,
                    "last": last,
                    "email": email,
                    "passHash": hash_password(password),
                    "rol": "paciente",
                    "permissions": [],
                    "estado": "pendiente_verificacion",
                    "emailVerified": False,
                    "patientId": patient.get("id"),
                    "verifyTokenHash": token_hash(verify_token),
                    "verifyExpiresAt": time.time() + 48 * 3600,
                    "createdAt": now_iso(),
                }
                users.append(new_user)
                set_json_key(conn, "users", users)
                set_json_key(conn, "nextIds", next_ids)
                audit(conn, None, "patient_register", "users", {"createdUserId": new_id, "createdEmail": email, "patientId": patient.get("id")})
            try:
                email_sent, email_error = send_verification_email(email, name, verify_link)
            except Exception as exc:
                email_sent, email_error = False, str(exc)
            response = {
                "ok": True,
                "emailSent": email_sent,
                "message": "Cuenta creada. Revisa tu correo para verificar tu cuenta antes de iniciar sesión.",
            }
            if not email_sent:
                response["message"] = "Cuenta creada, pero el servidor de correo no está configurado. Configura SMTP o Resend para enviar verificaciones."
                response["emailError"] = email_error
            if SHOW_VERIFICATION_LINK:
                response["verificationLink"] = verify_link
            return make_response(self, 201, response)

        if path == "/api/public/appointment":
            required = [
                payload.get("name") or payload.get("nombres") or payload.get("paciente"),
                payload.get("last") or payload.get("apellidos") or payload.get("paciente"),
                payload.get("email"),
                payload.get("tel") or payload.get("phone"),
                payload.get("esp") or payload.get("especialidad"),
                payload.get("fecha"),
                payload.get("hora"),
            ]
            if any(not str(v or "").strip() for v in required):
                return make_response(self, 400, {"error": "Completa paciente, correo, teléfono, especialidad, fecha y hora"})
            try:
                with db() as conn:
                    patient, patient_created = upsert_patient_from_payload(conn, {**payload, "origen": "Landing publica"})
                    appointment = create_online_appointment(conn, patient, payload)
                    audit(conn, None, "public_appointment", "citas", {"appointmentId": appointment["id"], "patientId": patient.get("id")})
            except AppointmentError as exc:
                return make_response(self, 409, {"error": str(exc)})
            return make_response(self, 201, {
                "ok": True,
                "patientCreated": patient_created,
                "appointment": appointment,
                "message": "Cita solicitada correctamente. El centro médico la verá en agenda y te confirmará la atención.",
            })

        if path == "/api/logout":
            token = self.headers.get("Authorization", "").replace("Bearer ", "").strip()
            user = auth_user(self)
            with db(lock=None) as conn:
                if user:
                    audit(conn, user, "logout", "session")
                if token:
                    conn.execute("delete from sessions where token_hash = ?", (token_hash(token),))
            return make_response(self, 200, {"ok": True})

        user = auth_user(self)
        if not user:
            return make_response(self, 401, {"error": "Sesión no válida"})

        if user.get("rol") == "medico" and path.startswith(("/api/invoices", "/api/cash/", "/api/sri/")):
            return make_response(self, 403, {"error": "Operación reservada a administración y recepción."})
        if path == "/api/email/settings":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador configura el correo."})
            from medicg.mailer import save_settings, MailError
            try:
                with db() as conn:
                    status = save_settings(conn, user, payload)
                return make_response(self, 200, {"ok": True, "settings": status})
            except MailError as exc:
                return make_response(self, 400, {"error": str(exc)})
        if path == "/api/email/outlook":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador conecta Outlook."})
            from medicg.outlook import connect
            from medicg.mailer import MailError
            try:
                with db() as conn:
                    result = connect(conn, user, payload.get("action", "poll"))
                return make_response(self, 200, result)
            except MailError as exc:
                return make_response(self, 400, {"error": str(exc)})
            except Exception:
                return make_response(self, 400, {"error": "No se pudo completar la conexión con Microsoft. Reintenta desde Configuración."})
        if path == "/api/email/patient":
            if user.get("rol") not in ("admin", "recepcion", "secretaria") or not can_invoice_sri(user):
                return make_response(self, 403, {"error": "No tienes permiso para enviar correos a pacientes."})
            from medicg.mailer import settings, send
            import html as html_module
            subject, message = payload.get("subject"), payload.get("message")
            if not isinstance(subject, str) or not 1 <= len(subject.strip()) <= 180 or not isinstance(message, str) or not 1 <= len(message.strip()) <= 10000:
                return make_response(self, 400, {"error": "Completa asunto y mensaje (máximo 180 y 10000 caracteres)."})
            with db(read_only=True) as conn:
                patient = next((p for p in get_json_key(conn, "pacientes", []) if str(p.get("id")) == str(payload.get("patientId")) and not p.get("deletedAt")), None)
                mail_config = settings(conn)
            if not patient:
                return make_response(self, 404, {"error": "Paciente no disponible."})
            # Network delivery runs outside any database transaction.
            sent, error = send(patient.get("email", ""), subject.strip(), message, "<div style='font-family:Arial;white-space:pre-wrap'>" + html_module.escape(message) + "</div>", config=mail_config, conn=None)
            with db(lock=None) as conn:
                audit(conn, user, "patient_email_sent" if sent else "patient_email_failed", "pacientes", {"patientId": patient["id"], "recipient": patient.get("email", ""), "error": error})
            return make_response(self, 200 if sent else 400, {"ok": sent, "error": error})
        if path == "/api/clinical/file":
            from medicg.files import load_content
            patient_id = str(payload.get("patientId") or "")
            file_id = str(payload.get("fileId") or "")
            if not patient_id or not file_id:
                return make_response(self, 400, {"error": "Falta el archivo solicitado."})
            with db(read_only=True) as conn:
                if not clinical_file_allowed(conn, user, patient_id):
                    return make_response(self, 403, {"error": "No tienes permiso para abrir archivos clínicos."})
                data_url, mime = load_content(conn, patient_id, file_id)
                if data_url is None:
                    entries = (get_json_key(conn, "archivosClinicos", {}) or {}).get(patient_id) or []
                    legacy = next((e for e in entries if str(e.get("id")) == file_id), None)
                    data_url = (legacy or {}).get("dataUrl")
            if not data_url:
                return make_response(self, 404, {"error": "Archivo no encontrado."})
            return make_response(self, 200, {"ok": True, "dataUrl": data_url, "mime": mime or ""})
        if path in ("/api/cash/open", "/api/cash/close"):
            from medicg.cash import open_box, close_box, CashError
            try:
                with db() as conn:
                    result = (open_box if path.endswith("open") else close_box)(conn, user, payload)
                return make_response(self, 200, result)
            except CashError as exc:
                return make_response(self, 409, {"error": str(exc)})
        if path.startswith("/api/reminders/"):
            from medicg import reminders
            try:
                if path == "/api/reminders/settings":
                    with db() as conn:
                        return make_response(self, 200, {"ok": True, "settings": reminders.save_settings(conn, user, payload)})
                if path == "/api/reminders/run":
                    if not can_save_key(user, "citas"):
                        return make_response(self, 403, {"error": "Sin permiso de agenda."})
                    return make_response(self, 200, reminders.run(None, force=bool(payload.get("force")) and user.get("rol") == "admin"))
                if path == "/api/reminders/send":
                    return make_response(self, 200, reminders.send_now(None, user, payload))
                if path == "/api/reminders/mark":
                    with db(lock="reminders") as conn:
                        return make_response(self, 200, reminders.mark_manual(conn, user, payload))
            except reminders.ReminderError as exc:
                return make_response(self, 409, {"error": str(exc)})
            return make_response(self, 404, {"error": "Ruta no encontrada"})
        if path == "/api/pharmacy":
            from medicg.pharmacy import operation as pharmacy_operation, PharmacyError
            try:
                with db() as conn:
                    result = pharmacy_operation(conn, user, payload)
                return make_response(self, 200, result)
            except PharmacyError as exc:
                return make_response(self, 409, {"error": str(exc)})
        if path == "/api/clinical/docs":
            from medicg.clinical_docs import operation as clinical_docs_operation, DocsError
            try:
                with db() as conn:
                    result = clinical_docs_operation(conn, user, payload)
                return make_response(self, 200, result)
            except DocsError as exc:
                return make_response(self, 409, {"error": str(exc)})
        if path == "/api/clinical/entries":
            from medicg.clinical import append_entry, ClinicalError
            try:
                with db() as conn:
                    result = append_entry(conn, user, payload)
                return make_response(self, 200, result)
            except ClinicalError as exc:
                return make_response(self, 409, {"error": str(exc)})
        if path == "/api/telehealth/session":
            from medicg.telehealth import operation, VideoError
            try:
                # Signaling only writes telehealth_native: lock per appointment, not the whole clinic.
                with db(lock="telehealth:" + str(payload.get("appointmentId") or "")) as conn:
                    result = operation(conn, user, payload)
                return make_response(self, 200, result)
            except VideoError as exc:
                return make_response(self, 409, {"error": str(exc)})
        if path == "/api/sri/certificate":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el dueno/administrador puede configurar el certificado SRI"})
            action = (payload.get("action") or "save").strip().lower()
            with db() as conn:
                if action == "status":
                    return make_response(self, 200, {"ok": True, "status": sri_certificate_status(conn)})
                if action == "delete":
                    if SRI_CERT_P12_BASE64:
                        return make_response(self, 400, {"error": "El certificado viene de variables privadas de Vercel. Eliminalo desde Vercel si deseas cambiarlo."})
                    set_json_key(conn, "sriCertificate", {})
                    audit(conn, user, "delete_sri_certificate", "sriCertificate")
                    return make_response(self, 200, {"ok": True, "status": sri_certificate_status(conn)})
                cert_b64 = normalize_cert_base64(payload.get("p12Base64") or payload.get("certificate") or "")
                password = str(payload.get("password") or "")
                filename = str(payload.get("filename") or "certificado-sri.p12")[:160]
                if not cert_b64:
                    return make_response(self, 400, {"error": "Selecciona el archivo .p12 o .pfx del certificado digital"})
                if not password:
                    return make_response(self, 400, {"error": "Ingresa la clave del certificado digital"})
                try:
                    base64.b64decode(cert_b64, validate=True)
                except Exception:
                    return make_response(self, 400, {"error": "No se pudo leer el certificado. Sube un archivo .p12/.pfx valido."})
                set_json_key(conn, "sriCertificate", {
                    "p12Base64": cert_b64,
                    "password": password,
                    "filename": filename,
                    "updatedAt": now_iso(),
                    "uploadedBy": user.get("email", ""),
                })
                audit(conn, user, "save_sri_certificate", "sriCertificate", {"filename": filename})
                return make_response(self, 200, {"ok": True, "status": sri_certificate_status(conn)})
        if path == "/api/invoices":
            if not can_invoice_sri(user):
                return make_response(self, 403, {"error": "No tienes permiso para emitir facturas"})
            try:
                with db() as conn:
                    invoice, patient, config = prepare_invoice_from_payload(conn, user, payload)
                    invoice["estado"] = "Pendiente SRI"
                    invoice["sriEstado"] = "GENERADO"
                    invoice["sriMensaje"] = "Guardada; envío manual al SRI pendiente"
                    email_sent, email_error = False, ""
                    save_invoice_record(conn, invoice)
                    audit(conn, user, "sri_invoice_emit", "facturas", {"invoiceId": invoice.get("id"), "estado": invoice.get("estado"), "emailSent": email_sent})
                return make_response(self, 201, {"ok": True, "invoice": invoice, "emailSent": email_sent, "emailError": email_error})
            except SRIIntegrationError as exc:
                return make_response(self, 400, {"error": str(exc)})
            except Exception:
                log.exception("invoice emit failed")
                return make_response(self, 500, {"error": "No se pudo emitir la factura. Intenta nuevamente o revisa la configuración SRI."})

        if path == "/api/invoices/sri-retry":
            if user.get("rol") not in ("admin", "recepcion", "secretaria") or not can_invoice_sri(user):
                return make_response(self, 403, {"error": "No tienes permiso para reenviar facturas al SRI"})
            invoice_id = payload.get("id") or payload.get("invoiceId")
            if not invoice_id:
                return make_response(self, 400, {"error": "Falta el numero de factura"})
            try:
                with db(read_only=True) as conn:
                    invoice, patient, config = invoice_context(conn, invoice_id)
                    cert_info = get_sri_certificate(conn)
                if invoice.get("sriEstado") == "AUTORIZADO" or invoice.get("estado") == "Autorizado SRI":
                    return make_response(self, 200, {"ok": True, "invoice": invoice, "alreadyAuthorized": True})
                if invoice.get("estado") == "Anulado":
                    return make_response(self, 409, {"error": "No se puede enviar una factura anulada."})
                if not claim_invoice(invoice_id, "sriSendingAt"):
                    return make_response(self, 409, {"error": "Esta factura se está enviando al SRI en este momento. Espera unos segundos y actualiza."})
                # The SRI web services can take several seconds: never hold the write lock meanwhile.
                try:
                    invoice = send_invoice_to_sri(invoice, cert_info)
                except SRIIntegrationError as exc:
                    invoice["estado"] = "Error SRI"
                    invoice["sriEstado"] = "ERROR"
                    invoice["sriMensaje"] = str(exc)
                except Exception:
                    log.exception("SRI send failed")
                    invoice["estado"] = "Error SRI"
                    invoice["sriEstado"] = "ERROR"
                    invoice["sriMensaje"] = "No se pudo conectar con el SRI. Reintenta en unos minutos."
                updates = {k: invoice[k] for k in INVOICE_SRI_FIELDS if k in invoice}
                saved = release_invoice(invoice_id, "sriSendingAt", updates, user, "sri_invoice_retry",
                                        {"invoiceId": invoice.get("id"), "estado": invoice.get("estado"), "emailSent": False})
                from medicg.files import strip_invoice
                return make_response(self, 200, {"ok": True, "invoice": strip_invoice(saved or invoice), "emailSent": False, "emailError": ""})
            except SRIIntegrationError as exc:
                return make_response(self, 404, {"error": str(exc)})
            except Exception:
                log.exception("SRI retry failed")
                return make_response(self, 500, {"error": "No se pudo consultar el SRI. Intenta nuevamente."})

        if path == "/api/invoices/email":
            if user.get("rol") not in ("admin", "recepcion", "secretaria") or not can_invoice_sri(user):
                return make_response(self, 403, {"error": "No tienes permiso para enviar facturas por correo"})
            invoice_id = payload.get("id") or payload.get("invoiceId")
            if not invoice_id:
                return make_response(self, 400, {"error": "Falta el numero de factura"})
            try:
                from medicg.mailer import settings
                with db(read_only=True) as conn:
                    invoice, patient, config = invoice_context(conn, invoice_id)
                    mail_config = settings(conn)
                if invoice.get("estado") == "Anulado":
                    return make_response(self, 409, {"error": "No se puede enviar una factura anulada."})
                if invoice.get("emailEnviado") and payload.get("resend") is not True:
                    return make_response(self, 409, {"error": "Esta factura ya fue enviada. Confirma el reenvío."})
                if not claim_invoice(invoice_id, "emailSendingAt"):
                    return make_response(self, 409, {"error": "Esta factura se está enviando por correo en este momento."})
                try:
                    email_sent, email_error = send_invoice_email(invoice, patient, config, mail_config, None)
                except Exception:
                    log.exception("invoice email failed")
                    email_sent, email_error = False, "No se pudo confirmar el envío del correo."
                updates = {"emailError": email_error}
                if email_sent:
                    updates.update(emailSentAt=now_iso(), emailSentBy=user.get("email", ""), emailTo=patient.get("email", ""), emailEnviado=True)
                saved = release_invoice(invoice_id, "emailSendingAt", updates, user, "sri_invoice_email",
                                        {"invoiceId": invoice.get("id"), "emailSent": email_sent, "error": email_error})
                from medicg.files import strip_invoice
                invoice = strip_invoice(saved or {**invoice, **updates})
                if not email_sent:
                    return make_response(self, 400, {"error": email_error or "No se pudo enviar el correo", "invoice": invoice})
                return make_response(self, 200, {"ok": True, "invoice": invoice, "emailSent": True})
            except SRIIntegrationError as exc:
                return make_response(self, 404, {"error": str(exc)})

        if path == "/api/invoices/ride":
            if not can_invoice_sri(user) and user.get("rol") != "paciente":
                return make_response(self, 403, {"error": "No tienes permiso para imprimir RIDE"})
            invoice_id = payload.get("id") or payload.get("invoiceId")
            if not invoice_id:
                return make_response(self, 400, {"error": "Falta el numero de factura"})
            try:
                with db() as conn:
                    invoice, patient, config = invoice_context(conn, invoice_id)
                    if user.get("rol") == "paciente" and int(invoice.get("pac") or 0) != int(user.get("patientId") or 0):
                        return make_response(self, 403, {"error": "No puedes ver esta factura"})
                html = ride_html(invoice, patient, config, ticket=(payload.get("format") == "ticket"))
                return make_response(self, 200, {"ok": True, "html": html, "filename": f"RIDE-{invoice.get('id')}.html"})
            except SRIIntegrationError as exc:
                return make_response(self, 404, {"error": str(exc)})

        if path == "/api/invoices/xml":
            if not can_invoice_sri(user) and user.get("rol") != "paciente":
                return make_response(self, 403, {"error": "No tienes permiso para descargar XML"})
            invoice_id = payload.get("id") or payload.get("invoiceId")
            if not invoice_id:
                return make_response(self, 400, {"error": "Falta el numero de factura"})
            try:
                with db() as conn:
                    invoice, _patient, _config = invoice_context(conn, invoice_id)
                    if user.get("rol") == "paciente" and int(invoice.get("pac") or 0) != int(user.get("patientId") or 0):
                        return make_response(self, 403, {"error": "No puedes ver esta factura"})
                xml = invoice.get("authorizedXml") or invoice.get("signedXml") or invoice.get("xml") or ""
                return make_response(self, 200, {"ok": True, "xml": xml, "filename": f"{invoice.get('id')}.xml", "authorized": invoice.get("estado") == "Autorizado SRI"})
            except SRIIntegrationError as exc:
                return make_response(self, 404, {"error": str(exc)})
        if path == "/api/patient/appointment":
            if user.get("rol") != "paciente":
                return make_response(self, 403, {"error": "Ruta disponible solo para pacientes"})
            if not (payload.get("esp") or payload.get("especialidad")) or not payload.get("fecha") or not payload.get("hora"):
                return make_response(self, 400, {"error": "Selecciona especialidad, fecha y hora"})
            try:
                with db() as conn:
                    portal = patient_portal_payload(conn, user)
                    if not portal:
                        return make_response(self, 404, {"error": "No encontramos una ficha de paciente vinculada a tu usuario"})
                    appointment = create_online_appointment(conn, portal["patient"], {**payload, "origen": "Portal paciente"}, user)
                    audit(conn, user, "patient_appointment", "citas", {"appointmentId": appointment["id"], "patientId": portal["patient"].get("id")})
                    portal = patient_portal_payload(conn, user)
            except AppointmentError as exc:
                return make_response(self, 409, {"error": str(exc)})
            return make_response(self, 201, {"ok": True, "appointment": appointment, "portal": portal})

        if path == "/api/patient/appointment-update":
            if user.get("rol") != "paciente":
                return make_response(self, 403, {"error": "Ruta disponible solo para pacientes"})
            appointment_id = int(payload.get("id") or payload.get("appointmentId") or 0)
            action = (payload.get("action") or "").strip().lower()
            if not appointment_id or action not in ("cancel", "reschedule"):
                return make_response(self, 400, {"error": "Accion de cita no valida"})
            try:
                with db() as conn:
                    portal = patient_portal_payload(conn, user)
                    if not portal:
                        return make_response(self, 404, {"error": "No encontramos una ficha de paciente vinculada a tu usuario"})
                    patient_id = int(portal["patient"].get("id") or 0)
                    appointments = get_json_key(conn, "citas", []) or []
                    appointment = next((c for c in appointments if int(c.get("id") or 0) == appointment_id and int(c.get("pac") or 0) == patient_id), None)
                    if not appointment:
                        return make_response(self, 404, {"error": "Cita no encontrada"})
                    if action == "cancel":
                        appointment["estado"] = "Cancelada"
                        appointment["cancelReason"] = payload.get("reason") or "Cancelada por el paciente"
                        appointment["cancelledAt"] = now_iso()
                        audit_action = "patient_appointment_cancel"
                    else:
                        fecha = (payload.get("fecha") or "").strip()
                        hora = (payload.get("hora") or "").strip()
                        if not fecha or not hora:
                            return make_response(self, 400, {"error": "Selecciona nueva fecha y hora"})
                        medicos = get_json_key(conn, "medicos", []) or []
                        med = int(appointment.get("med") or payload.get("med") or 0)
                        assigned_med = find_available_doctor(
                            appointments,
                            medicos,
                            appointment.get("esp") or payload.get("esp") or "",
                            med,
                            fecha,
                            hora,
                            ignore_id=appointment_id,
                        )
                        appointment["previousFecha"] = appointment.get("fecha")
                        appointment["previousHora"] = appointment.get("hora")
                        appointment["fecha"] = fecha
                        appointment["hora"] = hora
                        appointment["med"] = assigned_med
                        appointment["estado"] = "Pospuesta"
                        appointment["rescheduledAt"] = now_iso()
                        audit_action = "patient_appointment_reschedule"
                    set_json_key(conn, "citas", appointments)
                    notifications = get_json_key(conn, "notificaciones", []) or []
                    notifications.insert(0, {
                        "id": f"patient-action-{appointment_id}-{int(time.time())}",
                        "tipo": "cita_paciente",
                        "fecha": now_iso(),
                        "titulo": "Cita actualizada por paciente",
                        "detalle": f"{portal['patient'].get('nombres', '')} {portal['patient'].get('apellidos', '')}: {appointment.get('estado')} {appointment.get('fecha')} {appointment.get('hora')}",
                        "citaId": appointment_id,
                        "leida": False,
                    })
                    set_json_key(conn, "notificaciones", notifications[:80])
                    audit(conn, user, audit_action, "citas", {"appointmentId": appointment_id, "estado": appointment.get("estado")})
                    portal = patient_portal_payload(conn, user)
            except AppointmentError as exc:
                return make_response(self, 409, {"error": str(exc)})
            return make_response(self, 200, {"ok": True, "appointment": appointment, "portal": portal})

        if path == "/api/consultations/walkin":
            if not can_save_key(user, "citas"):
                return make_response(self, 403, {"error": "No tienes permiso para registrar consultas."})
            from medicg.walkin import register
            from medicg.cash import CashError
            try:
                with db() as conn:
                    result = register(conn, user, payload)
                return make_response(self, 200, result)
            except CashError as exc:
                return make_response(self, 409, {"error": str(exc)})
        if path == "/api/appointments":
            if not can_save_key(user, "citas"):
                return make_response(self, 403, {"error": "No tienes permiso para guardar citas"})
            try:
                with db() as conn:
                    appointments = get_json_key(conn, "citas", []) or []
                    medicos = get_json_key(conn, "medicos", []) or []
                    patients = get_json_key(conn, "pacientes", []) or []
                    appointment_id = int(payload.get("id") or 0)
                    previous = next((c for c in appointments if int(c.get("id") or 0) == appointment_id), None)
                    if appointment_id and not previous:
                        raise AppointmentError("La cita ya no existe. Actualiza la agenda.")
                    if previous and payload.get("base") != previous:
                        raise AppointmentError("Otro usuario cambió esta cita. Actualiza la agenda antes de guardar.")
                    item = {k: payload.get(k) for k in ("pac", "med", "esp", "tipo", "fecha", "hora", "motivo", "estado", "notif")}
                    item["modalidad"] = payload.get("modalidad", (previous or {}).get("modalidad", "presencial"))
                    if item["modalidad"] not in ("presencial", "online"):
                        raise AppointmentError("Modalidad inválida.")
                    item["pac"] = int(item.get("pac") or 0)
                    item["med"] = int(item.get("med") or 0)
                    if user.get("rol") == "medico":
                        from medicg.doctor_scope import check_patient, specialties
                        check_patient(conn, user, item["pac"])
                        own = next((m for m in medicos if str(m.get("id")) == str(user.get("medicoId"))), {})
                        if str(item["med"]) != str(user.get("medicoId")) or item.get("esp") not in specialties(own):
                            raise AppointmentError("Solo puedes registrar citas en tus especialidades y a tu nombre.")
                        if previous and str(previous.get("med")) != str(user.get("medicoId")):
                            raise AppointmentError("No puedes modificar citas asignadas a otro médico.")
                    if not any(int(p.get("id") or 0) == item["pac"] for p in patients):
                        raise AppointmentError("Selecciona un paciente registrado.")
                    if item["estado"] not in ("Solicitada online", "Pendiente", "Confirmada", "Pospuesta", "Cancelada", "Atendida"):
                        raise AppointmentError("Estado de cita inválido.")
                    if item["estado"] in ("Cancelada", "Atendida"):
                        if not previous:
                            raise AppointmentError("Primero registra la cita antes de cambiar este estado.")
                        for field in ("pac", "med", "esp", "fecha", "hora"):
                            item[field] = previous.get(field)
                    if item["estado"] != "Cancelada" and item["estado"] != "Atendida":
                        item["med"] = find_available_doctor(appointments, medicos, item["esp"], item["med"], item["fecha"], item["hora"], appointment_id)
                        clash = next((c for c in appointments if int(c.get("id") or 0) != appointment_id and int(c.get("pac") or 0) == item["pac"]
                                      and str(c.get("fecha")) == str(item["fecha"]) and str(c.get("hora")) == str(item["hora"]) and appointment_blocks_slot(c)), None)
                        if clash:
                            raise AppointmentError(f"El paciente ya tiene una cita a esa hora (cita #{clash.get('id')}, {clash.get('esp') or ''}).")
                    if item["estado"] == "Pospuesta" and previous and (item["fecha"], item["hora"]) == (previous.get("fecha"), previous.get("hora")):
                        raise AppointmentError("Selecciona una nueva fecha u hora para posponer la cita.")
                    ids = get_json_key(conn, "nextIds", {}) or {}
                    if not previous:
                        ids["cita"] = max(int(ids.get("cita") or 1), max((int(c.get("id") or 0) for c in appointments), default=0) + 1)
                        item["id"] = next_id(ids, "cita", 1)
                        item["createdAt"] = now_iso()
                        appointments.append(item)
                        set_json_key(conn, "nextIds", ids)
                    else:
                        previous.update(item)
                        item = previous
                    item["updatedAt"] = now_iso()
                    set_json_key(conn, "citas", appointments)
                    audit(conn, user, "save_appointment", "citas", {"id": item["id"]})
                    if user.get("rol") == "medico":
                        from medicg.doctor_scope import context, filter_data
                        appointments = filter_data({**context(conn), "citas": appointments}, user)["citas"]
                return make_response(self, 200, {"ok": True, "appointment": item, "appointments": appointments, "nextIds": ids})
            except (AppointmentError, ValueError, TypeError) as exc:
                return make_response(self, 409, {"error": str(exc)})
        if path == "/api/cash/delete-movement":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador puede eliminar movimientos."})
            from medicg.cash import delete_movement, CashError
            try:
                with db() as conn:
                    result = delete_movement(conn, user, payload)
                return make_response(self, 200, result)
            except CashError as exc:
                return make_response(self, 409, {"error": str(exc)})
        if path in ("/api/cash/charge", "/api/cash/payment"):
            if not can_save_key(user, "cajas"):
                return make_response(self, 403, {"error": "No tienes permiso para registrar cobros."})
            from medicg.cash import cash_operation, CashError
            try:
                with db() as conn:
                    result = cash_operation(conn, user, payload, "charge" if path.endswith("/charge") else "payment")
                return make_response(self, 200, result)
            except CashError as exc:
                return make_response(self, 409, {"error": str(exc)})
        if path in ("/api/patients/archive", "/api/patients/restore"):
            role = user.get("rol")
            if role not in ("admin", "recepcion", "secretaria") or (path.endswith("restore") and role != "admin"):
                return make_response(self, 403, {"error": "No tienes permiso para eliminar o restaurar pacientes."})
            if not can_save_key(user, "pacientes"):
                return make_response(self, 403, {"error": "No tienes permiso para gestionar pacientes."})
            reason = payload.get("reason", "")
            if path.endswith("archive") and (not isinstance(reason, str) or not 5 <= len(reason.strip()) <= 1000):
                return make_response(self, 400, {"error": "Escribe el motivo de eliminación (entre 5 y 1000 caracteres)."})
            with db() as conn:
                patients = get_json_key(conn, "pacientes", []) or []
                patient = next((p for p in patients if str(p.get("id")) == str(payload.get("patientId"))), None)
                if not patient:
                    return make_response(self, 404, {"error": "Paciente no encontrado."})
                if path.endswith("archive"):
                    if not patient.get("deletedAt"):
                        patient.update(deletedAt=now_iso(), deletedBy=user.get("email"), deletedByName=(user.get("name", "")+" "+user.get("last", "")).strip(), deletionReason=reason.strip())
                        audit(conn, user, "archive_patient", "pacientes", {"patientId": patient["id"], "reason": reason.strip()})
                else:
                    if patient.get("deletedAt"):
                        audit(conn, user, "restore_patient", "pacientes", {"patientId": patient["id"], "previousReason": patient.get("deletionReason")})
                        for field in ("deletedAt", "deletedBy", "deletedByName", "deletionReason"):
                            patient.pop(field, None)
                set_json_key(conn, "pacientes", patients)
            return make_response(self, 200, {"ok": True})
        if path == "/api/data":
            key = payload.get("key")
            value = payload.get("value")
            if key == "users":
                return make_response(self, 403, {"error": "Gestiona usuarios desde su ruta específica."})
            if key == "citas":
                return make_response(self, 409, {"error": "Actualiza la página para guardar citas con la nueva versión."})
            if not isinstance(key, str) or not key:
                return make_response(self, 400, {"error": "Falta key válido"})
            if key == "users" and user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador puede modificar usuarios"})
            if key != "users" and not can_save_key(user, key):
                return make_response(self, 403, {"error": "No tienes permiso para guardar este módulo"})
            from medicg.merge import merge_save, MergeConflict
            from medicg.files import extract_contents, restore_invoice_fields
            object_keys = {"config", "nextIds", "notas", "recetas", "archivosClinicos"}
            if "delta" not in payload and not isinstance(value, dict if key in object_keys else list):
                if "baseValue" not in payload:
                    return make_response(self, 409, {"error": "Actualiza la página antes de guardar; falta la versión original."})
                return make_response(self, 400, {"error": "Formato de datos inválido."})
            with db() as conn:
                current = get_json_key(conn, key)
                from medicg.doctor_scope import context, merge_write
                scope_data = context(conn) if user.get("rol") == "medico" else {}
                visible = sanitize_app_data_for_user({**scope_data, key: current}, user).get(key) if current is not None else None
                if visible is None:
                    visible = {} if key in object_keys else []
                try:
                    # Only records this user actually changed are checked and written;
                    # concurrent edits to other records are preserved.
                    value = merge_save(key, visible, payload, save_normalizer(key))
                except MergeConflict as exc:
                    return make_response(self, 409, {"error": str(exc), "conflicts": exc.items[:50]})
                except ValueError as exc:
                    return make_response(self, 400, {"error": str(exc)})
                if not isinstance(value, dict if key in object_keys else list):
                    return make_response(self, 400, {"error": "Formato de datos inválido."})
                if key == "facturas":
                    value = restore_invoice_fields(current, value)
                if key == "archivosClinicos":
                    value = extract_contents(conn, value)
                if user.get("rol") == "medico":
                    try:
                        value = merge_write(conn, user, key, value)
                    except ValueError as exc:
                        return make_response(self, 403, {"error": str(exc)})
                if key == "recetas":
                    def electronic(data):
                        return {(str(pid), str(r.get("id"))): r for pid, rows in (data or {}).items() if isinstance(rows, list)
                                for r in rows if isinstance(r, dict) and r.get("rxVersion")}
                    if electronic(current) != electronic(value):
                        return make_response(self, 409, {"error": "Las recetas electrónicas no se editan ni eliminan desde aquí."})
                if key == "notas":
                    from medicg.clinical import preserve_entries, ClinicalError
                    try:
                        preserve_entries(current, value)
                    except ClinicalError as exc:
                        return make_response(self, 409, {"error": str(exc)})
                if key == "facturas":
                    protected = {f["id"]: f for f in (current or []) if f.get("cobroVersion") == 1}
                    incoming = {f.get("id"): f for f in value if isinstance(f, dict)}
                    if any(incoming.get(k) != v for k, v in protected.items()) or any(f.get("cobroVersion") == 1 and f.get("id") not in protected for f in value if isinstance(f, dict)):
                        return make_response(self, 409, {"error": "Registra pagos de estas cuentas desde Caja o desde el paciente."})
                if key == "cajas":
                    def ledger(boxes):
                        return [m for c in boxes if isinstance(c, dict) for m in c.get("movimientos", []) if m.get("cobroVersion") == 1]
                    if ledger(current or []) != ledger(value):
                        return make_response(self, 409, {"error": "Los pagos registrados no se pueden modificar desde un guardado general."})
                    closed = {str(c.get("id")): c for c in (current or []) if isinstance(c, dict) and c.get("cierre")}
                    incoming_boxes = {str(c.get("id")): c for c in value if isinstance(c, dict)}
                    if any(incoming_boxes.get(k) != v for k, v in closed.items()):
                        return make_response(self, 409, {"error": "Los cierres de caja no se modifican ni eliminan."})
                if key == "pacientes":
                    if any(not isinstance(p, dict) or not p.get("id") for p in value):
                        return make_response(self, 400, {"error": "Paciente inválido."})
                    if len({str(p["id"]) for p in value}) != len(value):
                        return make_response(self, 400, {"error": "Identificadores de pacientes duplicados."})
                    active_ids = {str(p["id"]) for p in (current or []) if not p.get("deletedAt")}
                    incoming_ids = {str(p["id"]) for p in value}
                    archived = [p for p in (current or []) if p.get("deletedAt")]
                    if not active_ids.issubset(incoming_ids) or incoming_ids.intersection(str(p["id"]) for p in archived):
                        return make_response(self, 409, {"error": "Para eliminar pacientes usa la papelera e indica el motivo."})
                    for patient in value:
                        age = patient.get("edadDeclarada")
                        if age is not None and (isinstance(age, bool) or not isinstance(age, int) or not 0 <= age <= 130):
                            return make_response(self, 400, {"error": "La edad debe ser un número entero entre 0 y 130 años."})
                        if patient.get("fnac"):
                            patient["edadDeclarada"] = None
                            patient["edadDeclaradaFecha"] = None
                        for field in ("deletedAt", "deletedBy", "deletedByName", "deletionReason"):
                            patient.pop(field, None)
                    value.extend(archived)
                    perms = set(clean_permissions(user.get("permissions"), user.get("rol")))
                    if user.get("rol") != "admin" and "hce" not in perms:
                        previous = {str(p["id"]): p for p in (current or [])}
                        protected = {"alergias", "antec", "sangre", "antecedentes"}
                        for patient in value:
                            original = previous.get(str(patient["id"]), {})
                            for field in protected:
                                patient.pop(field, None)
                                if field in original:
                                    patient[field] = original[field]
                if key == "config":
                    # Certificate secrets are managed exclusively through their dedicated endpoint.
                    for field in ("sriCertP12Base64", "sriCertPassword", "sriCertificate", "sriCertificatePassword"):
                        value.pop(field, None)
                        if isinstance(current, dict) and field in current:
                            value[field] = current[field]
                set_json_key(conn, key, value)
                audit(conn, user, "save", key, {"mode": "delta" if "delta" in payload else "full"})
            return make_response(self, 200, {"ok": True})

        if path == "/api/users":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador puede crear usuarios"})
            action = payload.get("action") or "create"
            if action in ("update", "delete", "verify"):
                user_id = int(payload.get("userId") or 0)
                with db() as conn:
                    users = get_json_key(conn, "users", [])
                    target = next((u for u in users if int(u.get("id", 0)) == user_id), None)
                    if not target:
                        return make_response(self, 404, {"error": "Usuario no encontrado"})
                    is_self = int(user.get("id", 0)) == user_id
                    admin_count = sum(1 for u in users if u.get("rol") == "admin")

                    if action == "verify":
                        target["emailVerified"] = True
                        target["estado"] = "activo"
                        target.pop("verifyTokenHash", None)
                        target.pop("verifyExpiresAt", None)
                        set_json_key(conn, "users", users)
                        audit(conn, user, "verify_user", "users", {"targetUserId": user_id, "email": target.get("email")})
                        return make_response(self, 200, {"user": public_user(target)})

                    if action == "delete":
                        if is_self:
                            return make_response(self, 400, {"error": "No puedes eliminar tu propio usuario administrador"})
                        if target.get("rol") == "admin" and admin_count <= 1:
                            return make_response(self, 400, {"error": "No puedes eliminar el ultimo administrador"})
                        users = [u for u in users if int(u.get("id", 0)) != user_id]
                        set_json_key(conn, "users", users)
                        conn.execute("delete from sessions where user_id = ?", (user_id,))
                        audit(conn, user, "delete_user", "users", {"targetUserId": user_id, "email": target.get("email"), "rol": target.get("rol")})
                        return make_response(self, 200, {"ok": True, "deletedUserId": user_id})

                    allowed_roles = set(ROLE_DEFAULT_PERMISSIONS.keys())
                    name = (payload.get("name") or "").strip()
                    last = (payload.get("last") or "").strip()
                    email = (payload.get("email") or "").strip().lower()
                    rol = (payload.get("rol") or target.get("rol") or "recepcion").strip()
                    superadmin_medico = rol == "medico_superadmin"
                    if superadmin_medico:
                        rol = "admin"
                    estado = (payload.get("estado") or target.get("estado") or "activo").strip()
                    password = payload.get("password") or ""
                    if not name or not last or not email:
                        return make_response(self, 400, {"error": "Completa nombre, apellido y correo"})
                    if rol not in allowed_roles:
                        return make_response(self, 400, {"error": "Rol no valido"})
                    if any((u.get("email") or "").lower() == email and int(u.get("id", 0)) != user_id for u in users):
                        return make_response(self, 409, {"error": "Este correo ya esta registrado"})
                    if is_self and rol != "admin":
                        return make_response(self, 400, {"error": "No puedes quitarte el rol de administrador"})
                    if target.get("rol") == "admin" and rol != "admin" and admin_count <= 1:
                        return make_response(self, 400, {"error": "Debe quedar al menos un administrador"})
                    if is_self:
                        estado = "activo"
                    if password:
                        if len(password) < 6:
                            return make_response(self, 400, {"error": "La nueva contrasena debe tener minimo 6 caracteres"})
                        target["passHash"] = hash_password(password)
                        target.pop("pass", None)
                    if rol == "paciente" and not target.get("patientId"):
                        patient, _ = upsert_patient_from_payload(conn, {
                            "name": name,
                            "last": last,
                            "email": email,
                            "origen": "Vinculado por administrador",
                        })
                        target["patientId"] = patient.get("id")
                    if rol == "medico" or superadmin_medico:
                        medico_id = resolve_medico_id(conn, payload, name, last, email)
                        if not medico_id:
                            return make_response(self, 400, {"error": "Selecciona el perfil medico vinculado para este usuario"})
                        target["medicoId"] = medico_id
                    else:
                        target.pop("medicoId", None)
                    if superadmin_medico:
                        target["superadminMedico"] = True
                    else:
                        target.pop("superadminMedico", None)
                    if rol != "paciente":
                        target.pop("patientId", None)
                    target.update({
                        "name": name,
                        "last": last,
                        "email": email,
                        "rol": rol,
                        "estado": estado,
                        "permissions": clean_permissions(payload.get("permissions"), rol),
                        "updatedAt": now_iso(),
                    })
                    set_json_key(conn, "users", users)
                    audit(conn, user, "update_user", "users", {"targetUserId": user_id, "email": email, "rol": rol, "estado": estado})
                    return make_response(self, 200, {"user": public_user(target)})
            if payload.get("action") == "permissions":
                user_id = int(payload.get("userId") or 0)
                permissions = payload.get("permissions") or []
                with db() as conn:
                    users = get_json_key(conn, "users", [])
                    target = next((u for u in users if int(u.get("id", 0)) == user_id), None)
                    if not target:
                        return make_response(self, 404, {"error": "Usuario no encontrado"})
                    target["permissions"] = clean_permissions(permissions, target.get("rol", "recepcion"))
                    set_json_key(conn, "users", users)
                    audit(conn, user, "update_permissions", "users", {"targetUserId": user_id, "permissions": target["permissions"]})
                return make_response(self, 200, {"user": public_user(target)})
            name = (payload.get("name") or "").strip()
            last = (payload.get("last") or "").strip()
            email = (payload.get("email") or "").strip().lower()
            password = payload.get("password") or ""
            rol = payload.get("rol") or "recepcion"
            superadmin_medico = rol == "medico_superadmin"
            if superadmin_medico:
                rol = "admin"
            if not name or not last or not email or len(password) < 6:
                return make_response(self, 400, {"error": "Completa nombre, apellido, correo y contraseña de mínimo 6 caracteres"})
            permissions = clean_permissions(payload.get("permissions"), rol)
            with db() as conn:
                users = get_json_key(conn, "users", [])
                if any((u.get("email") or "").lower() == email for u in users):
                    return make_response(self, 409, {"error": "Este correo ya está registrado"})
                if rol not in ROLE_DEFAULT_PERMISSIONS:
                    return make_response(self, 400, {"error": "Rol no valido"})
                patient_id = None
                medico_id = None
                if rol == "paciente":
                    patient, _ = upsert_patient_from_payload(conn, {
                        "name": name,
                        "last": last,
                        "email": email,
                        "origen": "Creado por administrador",
                    })
                    patient_id = patient.get("id")
                if rol == "medico" or superadmin_medico:
                    medico_id = resolve_medico_id(conn, payload, name, last, email)
                    if not medico_id:
                        return make_response(self, 400, {"error": "Selecciona el perfil medico vinculado para este usuario"})
                next_ids = get_json_key(conn, "nextIds", {})
                new_id = max(int(next_ids.get("user", len(users) + 1)), max((int(u.get("id") or 0) for u in users), default=0) + 1)
                next_ids["user"] = new_id + 1
                new_user = {
                    "id": new_id,
                    "name": name,
                    "last": last,
                    "email": email,
                    "passHash": hash_password(password),
                    "rol": rol,
                    "permissions": permissions,
                    "estado": "activo",
                    "emailVerified": True,
                    "patientId": patient_id,
                    "medicoId": medico_id,
                    "createdAt": now_iso(),
                }
                if superadmin_medico:
                    new_user["superadminMedico"] = True
                users.append(new_user)
                set_json_key(conn, "users", users)
                set_json_key(conn, "nextIds", next_ids)
                audit(conn, user, "create_user", "users", {"createdUserId": new_id, "createdEmail": email, "rol": rol})
            return make_response(self, 200, {"user": public_user(new_user)})

        if path == "/api/users/permissions":
            if user.get("rol") != "admin":
                return make_response(self, 403, {"error": "Solo el administrador puede configurar permisos"})
            user_id = int(payload.get("userId") or 0)
            permissions = payload.get("permissions") or []
            with db() as conn:
                users = get_json_key(conn, "users", [])
                target = next((u for u in users if int(u.get("id", 0)) == user_id), None)
                if not target:
                    return make_response(self, 404, {"error": "Usuario no encontrado"})
                target["permissions"] = clean_permissions(permissions, target.get("rol", "recepcion"))
                set_json_key(conn, "users", users)
                audit(conn, user, "update_permissions", "users", {"targetUserId": user_id, "permissions": target["permissions"]})
            return make_response(self, 200, {"user": public_user(target)})

        return make_response(self, 404, {"error": "Ruta no encontrada"})

    def do_OPTIONS(self):
        return make_response(self, 200, {"ok": True})


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), MedicGHandler)
    print(f"Medic G con base de datos {DB_DRIVER}")
    print(f"Abre: http://{HOST}:{PORT}")
    print(f"Base de datos: {DB_PATH if DB_DRIVER == 'sqlite' else 'PostgreSQL'}")
    server.serve_forever()












