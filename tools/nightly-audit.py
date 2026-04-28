"""
Nightly Product Audit — Designer Eyes & Shades Eyeconic
Checks: missing image, missing price (=$0), price > $5000
Sends results by email via Resend
"""

import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Config ──────────────────────────────────────────────────────────────────────

RESEND_API_KEY = "re_4sfaj7sx_D5DWujLdmQM7NQxRptfZXms1"
EMAIL_TO       = "andres.belmonte87@gmail.com"
EMAIL_FROM     = "onboarding@resend.dev"
MAX_PRICE      = 5000.0

CLIENTS = {
    "Designer Eyes": {
        "url":      "https://www.designereyes.com/collections/all/products.json",
        "base_url": "https://www.designereyes.com/products/",
    },
    "Shades Eyeconic": {
        "url":      "https://shadeseyeconic.com/collections/all/products.json",
        "base_url": "https://shadeseyeconic.com/products/",
    },
}

# ── Fetch ────────────────────────────────────────────────────────────────────────

def fetch_products(base_url):
    products = []
    page = 1
    while True:
        url = f"{base_url}?limit=250&page={page}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                batch = json.loads(r.read()).get("products", [])
        except Exception as e:
            print(f"  Fetch error page {page}: {e}")
            break
        if not batch:
            break
        products.extend(batch)
        print(f"  Page {page}: {len(batch)} products")
        if len(batch) < 250:
            break
        page += 1
    return products

# ── Check ────────────────────────────────────────────────────────────────────────

def check_product(product):
    issues = []

    if not product.get("images"):
        issues.append("SIN IMAGEN PRINCIPAL")

    prices = []
    for variant in product.get("variants", []):
        try:
            prices.append(float(variant.get("price", 0)))
        except (ValueError, TypeError):
            pass

    if not prices or all(p == 0 for p in prices):
        issues.append("SIN PRECIO")
    elif any(p >= MAX_PRICE for p in prices):
        max_p = max(prices)
        issues.append(f"PRECIO ${max_p:,.2f} (supera ${MAX_PRICE:,.0f})")

    return issues

# ── Email ────────────────────────────────────────────────────────────────────────

def build_html(results, date_str, total, total_flagged, site_counts):
    status_color = "#22c55e" if total_flagged == 0 else "#ef4444"
    passed       = total - total_flagged

    # Per-site breakdown table
    site_rows = ""
    for site_name, count in site_counts.items():
        site_flagged = sum(1 for r in results if r["client"] == site_name)
        dot_color = "#22c55e" if site_flagged == 0 else "#ef4444"
        flag_text = f"<span style='color:#ef4444;font-weight:700;'>{site_flagged} problema(s)</span>" if site_flagged > 0 else "<span style='color:#22c55e;'>Sin problemas</span>"
        site_rows += (
            f"<tr style='border-bottom:1px solid #f3f4f6;'>"
            f"<td style='padding:10px 12px;font-size:13px;font-weight:700;'>"
            f"<span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:{dot_color};margin-right:8px;'></span>"
            f"{site_name}</td>"
            f"<td style='padding:10px 12px;font-size:13px;text-align:center;'>{count}</td>"
            f"<td style='padding:10px 12px;font-size:13px;'>{flag_text}</td>"
            f"</tr>"
        )
    site_table = (
        "<h3 style='font-size:13px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin:24px 0 8px;'>Detalle por sitio</h3>"
        "<table style='width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;margin-bottom:24px;'>"
        "<thead><tr style='background:#f3f4f6;'>"
        "<th style='padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;'>Sitio</th>"
        "<th style='padding:10px 12px;text-align:center;font-size:12px;color:#6b7280;'>Artículos verificados</th>"
        "<th style='padding:10px 12px;text-align:left;font-size:12px;color:#6b7280;'>Estado</th>"
        "</tr></thead>"
        f"<tbody>{site_rows}</tbody></table>"
    )

    # Build issues table
    if total_flagged == 0:
        body_html = (
            site_table
            + '<p style="color:#22c55e;font-weight:700;font-size:16px;">✅ Todos los productos pasaron la auditoria.</p>'
        )
    else:
        rows = ""
        for r in results:
            rows += (
                "<tr style='border-bottom:1px solid #e5e7eb;'>"
                f"<td style='padding:10px;font-size:13px;color:#6b7280;font-weight:700;'>{r['client']}</td>"
                f"<td style='padding:10px;font-size:13px;'>{r['title']}</td>"
                f"<td style='padding:10px;font-size:12px;color:#ef4444;'>{r['issues']}</td>"
                f"<td style='padding:10px;font-size:13px;'><a href='{r['url']}' style='color:#6366f1;text-decoration:none;font-weight:600;'>Ver producto →</a></td>"
                "</tr>"
            )
        body_html = (
            site_table
            + "<h3 style='font-size:13px;color:#6b7280;text-transform:uppercase;letter-spacing:0.05em;margin:0 0 8px;'>Productos con problemas</h3>"
            + "<table style='width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;'>"
            "<thead><tr style='background:#f3f4f6;'>"
            "<th style='padding:12px;text-align:left;font-size:12px;color:#6b7280;'>Sitio</th>"
            "<th style='padding:12px;text-align:left;font-size:12px;color:#6b7280;'>Producto</th>"
            "<th style='padding:12px;text-align:left;font-size:12px;color:#6b7280;'>Problema</th>"
            "<th style='padding:12px;text-align:left;font-size:12px;color:#6b7280;'>Link</th>"
            "</tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    return (
        "<div style='font-family:Arial,sans-serif;max-width:700px;margin:0 auto;background:#f9f9f9;padding:24px;border-radius:12px;'>"
        f"<h2 style='color:#1a1d27;border-bottom:2px solid #6366f1;padding-bottom:10px;'>Auditoria Nocturna - {date_str}</h2>"
        "<table style='width:100%;margin-bottom:24px;'><tr>"
        f"<td style='text-align:center;padding:16px;background:#fff;border:1px solid #e5e7eb;border-radius:8px;'>"
        f"<div style='font-size:32px;font-weight:800;'>{total}</div>"
        f"<div style='font-size:12px;color:#6b7280;'>REVISADOS</div></td>"
        f"<td style='width:16px;'></td>"
        f"<td style='text-align:center;padding:16px;background:#fff;border:1px solid {status_color};border-radius:8px;'>"
        f"<div style='font-size:32px;font-weight:800;color:{status_color};'>{total_flagged}</div>"
        f"<div style='font-size:12px;color:#6b7280;'>PROBLEMAS</div></td>"
        f"<td style='width:16px;'></td>"
        f"<td style='text-align:center;padding:16px;background:#fff;border:1px solid #22c55e;border-radius:8px;'>"
        f"<div style='font-size:32px;font-weight:800;color:#22c55e;'>{passed}</div>"
        f"<div style='font-size:12px;color:#6b7280;'>SIN PROBLEMAS</div></td>"
        "</tr></table>"
        f"{body_html}"
        "<hr style='border:none;border-top:1px solid #e5e7eb;margin:24px 0;'>"
        "<p style='color:#6b7280;font-size:12px;'>Trill Digital Media - Auditoria automatica nocturna - Designer Eyes &amp; Shades Eyeconic</p>"
        "</div>"
    )

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
            "Authorization":  f"Bearer {RESEND_API_KEY}",
            "Content-Type":   "application/json",
            "User-Agent":     "Mozilla/5.0 (compatible; TrillDigitalAudit/1.0)",
            "Accept":         "application/json",
        }
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        result = json.loads(r.read())
        print(f"  Email enviado. ID: {result.get('id')}")

# ── Main ─────────────────────────────────────────────────────────────────────────

def main():
    date_str     = datetime.now(timezone.utc).strftime("%d %b %Y")
    flagged_rows = []
    total        = 0
    site_counts  = {}

    print(f"\n{'='*60}")
    print(f"  Nightly Product Audit — {date_str}")
    print(f"{'='*60}\n")

    for client_name, client in CLIENTS.items():
        print(f"  [{client_name}] Fetching products...")
        products = fetch_products(client["url"])
        print(f"  [{client_name}] {len(products)} products loaded\n")
        total += len(products)
        site_counts[client_name] = len(products)

        flagged = 0
        for product in products:
            issues = check_product(product)
            if not issues:
                continue
            flagged += 1
            url = client["base_url"] + product["handle"]
            print(f"  ⚠️  {product['title']}")
            print(f"      Issues: {' | '.join(issues)}")
            print(f"      URL:    {url}\n")
            flagged_rows.append({
                "client": client_name,
                "title":  product["title"],
                "issues": " | ".join(issues),
                "url":    url,
            })

        if flagged == 0:
            print(f"  ✅ All {len(products)} products passed.\n")
        else:
            print(f"  ❌ {flagged} product(s) flagged.\n")

    total_flagged = len(flagged_rows)
    print(f"\n{'='*60}")
    print(f"  TOTAL: {total} checked | {total_flagged} flagged | {total - total_flagged} passed")
    print(f"{'='*60}\n")

    subject = (
        f"✅ Auditoría OK — {date_str} ({total} productos)"
        if total_flagged == 0
        else f"⚠️ Auditoría: {total_flagged} problema(s) — {date_str}"
    )
    html = build_html(flagged_rows, date_str, total, total_flagged, site_counts)
    print("  Sending email...")
    send_email(subject, html)
    print("  Done.\n")


if __name__ == "__main__":
    main()
