"""
Daily Briefing — Trill Digital Media
Reads task files, generates prioritized briefing, sends via Resend.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Config ───────────────────────────────────────────────────────────────────

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "re_4sfaj7sx_D5DWujLdmQM7NQxRptfZXms1")
EMAIL_TO       = "andres.belmonte87@gmail.com"
EMAIL_FROM     = "onboarding@resend.dev"

TASK_FILES = [
    ("Designer Eyes",    "tasks/designer-eyes/pendientes.md"),
    ("Shades Eyeconic",  "tasks/shades-eyeconic/pendientes.md"),
]
RESPONSABLES_FILE = "tasks/responsables.md"

# ── Parse tasks ──────────────────────────────────────────────────────────────

def parse_tasks(filepath, project):
    tasks = []
    if not os.path.exists(filepath):
        print(f"  [WARN] File not found: {filepath}")
        return tasks

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Split by task blocks (## XX-NNN)
    blocks = re.split(r"\n(?=## [A-Z]{2}-\d+)", content)

    for block in blocks:
        id_match = re.search(r"## ([A-Z]{2}-\d+) \| (.+)", block)
        if not id_match:
            continue

        task_id    = id_match.group(1)
        task_title = id_match.group(2).strip()

        # Skip completed section
        if "Completadas" in task_title:
            continue

        prioridad    = _extract(block, "Prioridad")
        estado       = _extract(block, "Estado")
        responsable  = _extract(block, "Responsable")
        fecha        = _extract(block, "Fecha límite")
        contexto     = _extract(block, "Contexto")

        # Determine priority level
        if "🔴" in prioridad:
            level = 1  # Alta
        elif "🟡" in prioridad:
            level = 2  # Media
        else:
            level = 3  # Baja

        tasks.append({
            "id":          task_id,
            "title":       task_title,
            "project":     project,
            "level":       level,
            "prioridad":   prioridad,
            "estado":      estado,
            "responsable": responsable,
            "fecha":       fecha,
            "contexto":    contexto,
        })

    return tasks


def _extract(block, field):
    match = re.search(rf"\*\*{field}:\*\*\s*(.+)", block)
    return match.group(1).strip() if match else "—"


def parse_completed(filepath, project):
    completed = []
    if not os.path.exists(filepath):
        return completed
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    section = re.search(r"## ✅ Completadas Recientes(.+?)(?=\n## |\Z)", content, re.DOTALL)
    if not section:
        return completed
    for row in re.finditer(r"\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|\s*([^\|]+?)\s*\|", section.group(1)):
        id_, title, date = row.group(1).strip(), row.group(2).strip(), row.group(3).strip()
        if id_ == "ID" or not title or title == "---":
            continue
        completed.append({"id": id_, "title": title, "date": date, "project": project})
    return completed

# ── Build HTML ───────────────────────────────────────────────────────────────

def task_row(t, color):
    fecha_label = f"Vence: {t['fecha']}" if t['fecha'] != "—" else "Sin fecha"
    return (
        f"<li style='margin-bottom:8px;'>"
        f"<strong style='color:{color};'>[{t['id']}]</strong> {t['title']} "
        f"<span style='color:#6b7280;font-size:12px;'>| {t['project']} | {t['responsable']} | {fecha_label}</span>"
        f"</li>"
    )


def build_html(tasks, completed, date_str):
    alta   = [t for t in tasks if t["level"] == 1]
    media  = [t for t in tasks if t["level"] == 2]
    baja   = [t for t in tasks if t["level"] == 3]

    def section(title, items, color, emoji):
        if not items:
            return ""
        rows = "".join(task_row(t, color) for t in items)
        return (
            f"<h3 style='color:{color};margin-top:24px;'>{emoji} {title}</h3>"
            f"<ul style='line-height:1.8;padding-left:20px;'>{rows}</ul>"
        )

    # Vista por responsable
    resp_map = {}
    for t in tasks:
        key = t["responsable"]
        resp_map.setdefault(key, []).append(t)

    resp_html = "<h3 style='margin-top:24px;'>👤 Vista por responsable</h3>"
    for resp, items in resp_map.items():
        rows = "".join(
            f"<li style='margin-bottom:4px;'>[{t['id']}] {t['title']} — {t['prioridad']} — Vence: {t['fecha']}</li>"
            for t in items
        )
        resp_html += f"<p style='margin-bottom:4px;'><strong>{resp}:</strong></p><ul style='line-height:1.8;padding-left:20px;'>{rows}</ul>"

    # Completadas
    comp_html = ""
    if completed:
        comp_rows = "".join(
            f"<li style='margin-bottom:4px;'>[{c['id']}] {c['title']} — {c['project']} — {c['date']}</li>"
            for c in completed
        )
        comp_html = (
            "<h3 style='margin-top:24px;'>✅ Completadas recientemente</h3>"
            f"<ul style='line-height:1.8;padding-left:20px;'>{comp_rows}</ul>"
        )

    total = len(tasks)
    urgentes = len(alta)
    status_color = "#ef4444" if urgentes > 0 else "#22c55e"

    return (
        "<div style='font-family:Arial,sans-serif;max-width:700px;margin:0 auto;background:#f9f9f9;padding:24px;border-radius:12px;'>"
        f"<h2 style='color:#1a1d27;border-bottom:2px solid #6366f1;padding-bottom:10px;'>📋 Briefing Trill Digital — {date_str}</h2>"
        # Summary cards
        "<table style='width:100%;margin-bottom:8px;'><tr>"
        f"<td style='text-align:center;padding:16px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;'>"
        f"<div style='font-size:28px;font-weight:800;'>{total}</div>"
        f"<div style='font-size:11px;color:#6b7280;'>TAREAS ACTIVAS</div></td>"
        f"<td style='width:12px;'></td>"
        f"<td style='text-align:center;padding:16px;background:#fff;border:1px solid {status_color};border-radius:8px;'>"
        f"<div style='font-size:28px;font-weight:800;color:{status_color};'>{urgentes}</div>"
        f"<div style='font-size:11px;color:#6b7280;'>URGENTES HOY</div></td>"
        f"<td style='width:12px;'></td>"
        f"<td style='text-align:center;padding:16px;background:#fff;border:1px solid #22c55e;border-radius:8px;'>"
        f"<div style='font-size:28px;font-weight:800;color:#22c55e;'>{len(completed)}</div>"
        f"<div style='font-size:11px;color:#6b7280;'>COMPLETADAS</div></td>"
        "</tr></table>"
        + section("Prioridad Alta", alta, "#ef4444", "🔴")
        + section("Prioridad Media", media, "#f59e0b", "🟡")
        + section("Prioridad Baja", baja, "#22c55e", "🟢")
        + "<hr style='border:none;border-top:1px solid #e5e7eb;margin:24px 0;'>"
        + resp_html
        + "<hr style='border:none;border-top:1px solid #e5e7eb;margin:24px 0;'>"
        + comp_html
        + "<hr style='border:none;border-top:1px solid #e5e7eb;margin:24px 0;'>"
        + (
            "<h3 style='margin-top:0;'>📅 Reuniones de hoy</h3>"
            "<div style='background:#eff6ff;border:1px solid #bfdbfe;border-radius:8px;padding:14px 16px;font-size:13px;color:#1e40af;'>"
            "Revisá tu calendario de Teams para ver las reuniones agendadas para hoy."
            "<br><a href='https://teams.microsoft.com/_#/calendarv2' style='color:#6366f1;font-weight:600;'>Abrir Teams Calendar →</a>"
            "</div>"
            "<hr style='border:none;border-top:1px solid #e5e7eb;margin:24px 0;'>"
        )
        + "<p style='color:#6b7280;font-size:12px;'>Trill Digital Media — Briefing diario automatico</p>"
        "</div>"
    )

# ── Send email ───────────────────────────────────────────────────────────────

def send_email(subject, html):
    data = json.dumps({
        "from":    EMAIL_FROM,
        "to":      EMAIL_TO,
        "subject": subject,
        "html":    html,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type":  "application/json",
            "User-Agent":    "Mozilla/5.0 (compatible; TrillDigitalBriefing/1.0)",
            "Accept":        "application/json",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        result = json.loads(r.read())
        print(f"  Email enviado. ID: {result.get('id')}")

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    now      = datetime.now(timezone.utc)
    date_str = now.strftime("%d %b %Y")

    print(f"\n{'='*60}")
    print(f"  Daily Briefing — {date_str}")
    print(f"{'='*60}\n")

    all_tasks     = []
    all_completed = []

    for project, filepath in TASK_FILES:
        tasks = parse_tasks(filepath, project)
        comp  = parse_completed(filepath, project)
        print(f"  [{project}] {len(tasks)} tareas activas, {len(comp)} completadas")
        all_tasks.extend(tasks)
        all_completed.extend(comp)

    # Sort by priority level
    all_tasks.sort(key=lambda t: t["level"])

    print(f"\n  TOTAL: {len(all_tasks)} tareas | {len([t for t in all_tasks if t['level']==1])} urgentes\n")

    html    = build_html(all_tasks, all_completed, date_str)
    subject = f"📋 Briefing Trill Digital — {date_str}"

    print("  Enviando email...")
    send_email(subject, html)
    print("  Listo.\n")


if __name__ == "__main__":
    main()
