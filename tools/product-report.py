import requests
import sys
import json
import os
from datetime import datetime
from collections import defaultdict, Counter

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

CLIENTS = {
    "Designer Eyes":   "https://www.designereyes.com/collections/all/products.json",
    "Shades Eyeconic": "https://shadeseyeconic.com/collections/all/products.json",
}

STORE_VENDORS = {"ShadesEyeconic"}

BRAND_ALIASES = {
    "COSTA": "COSTA DEL MAR",
}

# Designer Eyes: product_types that map to Sunglasses or Eyeglasses
DE_SUNGLASS_TYPES = {"SUNGLASS", "SUNGLASSES"}
DE_EYEGLASS_TYPES = {"OPTICAL"}

# Shades: product_types that count as Apparel
SE_APPAREL_TYPES = {
    "T-SHIRTS", "POLO SHIRTS", "FLIP FLOPS", "SWEATSHIRTS", "HATS",
    "BOARD SHORTS", "SHORTS", "HYBRID SHORTS", "PANTS", "WOVEN SHIRTS",
    "JACKETS", "VESTS",
}

SNAPSHOTS_DIR = os.path.join(os.path.dirname(__file__), "snapshots")


def extract_brand(product: dict, known_brands: set) -> str:
    vendor = product.get("vendor", "").strip()
    if vendor not in STORE_VENDORS:
        brand = vendor.upper()
        return BRAND_ALIASES.get(brand, brand)

    for tag in product.get("tags", []):
        tag_upper = tag.upper()
        tag_upper = BRAND_ALIASES.get(tag_upper, tag_upper)
        if tag_upper in known_brands or tag_upper in BRAND_ALIASES.values():
            return tag_upper

    handle = product.get("handle", "")
    if handle:
        brand = handle.split("-")[0].upper()
        return BRAND_ALIASES.get(brand, brand)

    return "UNKNOWN"


def fetch_all(url):
    products = []
    for page in range(1, 20):
        r = requests.get(url, params={"limit": 250, "page": page}, timeout=15)
        batch = r.json().get("products", [])
        if not batch:
            break
        products.extend(batch)
    return products


def classify_shades_eyewear(product: dict) -> str:
    """Return 'sunglasses', 'eyeglasses', or 'unknown' for a Shades EYEWEAR product."""
    tags = {t.upper() for t in product.get("tags", [])}
    if "SUNGLASS" in tags:
        return "sunglasses"
    if "OPTICAL" in tags:
        return "eyeglasses"
    return "unknown"


# ─── Snapshot helpers ────────────────────────────────────────────────────────

def snapshot_path(client_name: str) -> str:
    slug = client_name.lower().replace(" ", "-")
    return os.path.join(SNAPSHOTS_DIR, f"{slug}-latest.json")


def load_snapshot(client_name: str) -> dict | None:
    path = snapshot_path(client_name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_snapshot(client_name: str, products: list, known_brands: set):
    snapshot = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total": len(products),
        "products": [
            {
                "handle":       p.get("handle", ""),
                "title":        p.get("title", ""),
                "brand":        extract_brand(p, known_brands),
                "product_type": p.get("product_type", "").strip().upper(),
            }
            for p in products
        ],
    }
    os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
    with open(snapshot_path(client_name), "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)


def print_diff(client_name: str, prev: dict, curr_products: list, known_brands: set):
    prev_map = {p["handle"]: p for p in prev["products"]}
    curr_map = {
        p.get("handle", ""): {
            "handle":       p.get("handle", ""),
            "title":        p.get("title", ""),
            "brand":        extract_brand(p, known_brands),
            "product_type": p.get("product_type", "").strip().upper(),
        }
        for p in curr_products
    }

    removed = [prev_map[h] for h in prev_map if h not in curr_map]
    added   = [curr_map[h] for h in curr_map if h not in prev_map]

    if not removed and not added:
        print(f"  Sin cambios desde {prev['date']}  ✓")
        return

    prev_date = prev["date"]

    if removed:
        print(f"\n  ❌  ELIMINADOS desde {prev_date}  ({len(removed)} productos)")
        print(f"  {'#':<4} {'MARCA':<20} {'TIPO':<14} TÍTULO")
        print(f"  {'-'*80}")
        for i, p in enumerate(sorted(removed, key=lambda x: x["brand"]), 1):
            title = p["title"][:50]
            print(f"  {i:<4} {p['brand']:<20} {p['product_type']:<14} {title}")

    if added:
        print(f"\n  ✅  AGREGADOS desde {prev_date}  ({len(added)} productos)")
        print(f"  {'#':<4} {'MARCA':<20} {'TIPO':<14} TÍTULO")
        print(f"  {'-'*80}")
        for i, p in enumerate(sorted(added, key=lambda x: x["brand"]), 1):
            title = p["title"][:50]
            print(f"  {i:<4} {p['brand']:<20} {p['product_type']:<14} {title}")


# ─── Report printers ─────────────────────────────────────────────────────────

def print_designer_eyes(client_name, products):
    known_brands = set(
        p["vendor"].upper() for p in products
        if p.get("vendor", "") not in STORE_VENDORS
    )

    # Diff vs previous snapshot
    prev = load_snapshot(client_name)
    if prev:
        print_diff(client_name, prev, products, known_brands)
    else:
        print(f"  (Primer snapshot guardado — el próximo reporte mostrará cambios)")

    # Save new snapshot
    save_snapshot(client_name, products, known_brands)

    brand_total   = Counter()
    brand_sun     = Counter()
    brand_eye     = Counter()

    for p in products:
        brand = extract_brand(p, known_brands)
        ptype = p.get("product_type", "").strip().upper()
        brand_total[brand] += 1
        if ptype in DE_SUNGLASS_TYPES:
            brand_sun[brand] += 1
        elif ptype in DE_EYEGLASS_TYPES:
            brand_eye[brand] += 1

    W = 75
    col = 13
    print()
    print("=" * W)
    print(f"  {client_name.upper()}")
    print(f"  Total active products : {len(products)}")
    print(f"  Total brands          : {len(brand_total)}")
    print("=" * W)
    print(f"  {'MARCA':<32} {'PRODUCTOS':>{col}}   {'SUNGLASSES':>{col}}   {'EYEGLASSES':>{col}}")
    print("-" * W)

    for brand, total in brand_total.most_common():
        sun = brand_sun[brand]
        eye = brand_eye[brand]
        print(f"  {brand:<32} {total:>{col}}   {sun:>{col}}   {eye:>{col}}")

    total_sun = sum(brand_sun.values())
    total_eye = sum(brand_eye.values())
    print("-" * W)
    print(f"  {'TOTAL':<32} {len(products):>{col}}   {total_sun:>{col}}   {total_eye:>{col}}")
    print("=" * W)
    print()


def print_shades_eyeconic(client_name, products):
    known_brands = set(
        p["vendor"].upper() for p in products
        if p.get("vendor", "") not in STORE_VENDORS
    )

    # Diff vs previous snapshot
    prev = load_snapshot(client_name)
    if prev:
        print_diff(client_name, prev, products, known_brands)
    else:
        print(f"  (Primer snapshot guardado — el próximo reporte mostrará cambios)")

    # Save new snapshot
    save_snapshot(client_name, products, known_brands)

    brand_total   = Counter()
    brand_sun     = Counter()
    brand_eye     = Counter()
    brand_apparel = Counter()

    for p in products:
        brand = extract_brand(p, known_brands)
        ptype = p.get("product_type", "").strip().upper()
        brand_total[brand] += 1
        if ptype == "EYEWEAR":
            kind = classify_shades_eyewear(p)
            if kind == "sunglasses":
                brand_sun[brand] += 1
            elif kind == "eyeglasses":
                brand_eye[brand] += 1
        elif ptype in SE_APPAREL_TYPES:
            brand_apparel[brand] += 1

    W = 90
    col = 13
    print()
    print("=" * W)
    print(f"  {client_name.upper()}")
    print(f"  Total active products : {len(products)}")
    print(f"  Total brands          : {len(brand_total)}")
    print("=" * W)
    print(f"  {'MARCA':<32} {'PRODUCTOS':>{col}}   {'SUNGLASSES':>{col}}   {'EYEGLASSES':>{col}}   {'APPAREL':>{col}}")
    print("-" * W)

    for brand, total in brand_total.most_common():
        sun     = brand_sun[brand]
        eye     = brand_eye[brand]
        apparel = brand_apparel[brand]
        print(f"  {brand:<32} {total:>{col}}   {sun:>{col}}   {eye:>{col}}   {apparel:>{col}}")

    total_sun     = sum(brand_sun.values())
    total_eye     = sum(brand_eye.values())
    total_apparel = sum(brand_apparel.values())
    print("-" * W)
    print(f"  {'TOTAL':<32} {len(products):>{col}}   {total_sun:>{col}}   {total_eye:>{col}}   {total_apparel:>{col}}")
    print("=" * W)
    print()


def main():
    handlers = {
        "Designer Eyes":   print_designer_eyes,
        "Shades Eyeconic": print_shades_eyeconic,
    }
    for client_name, url in CLIENTS.items():
        print(f"\n  Fetching {client_name}...", end="", flush=True)
        products = fetch_all(url)
        print(f" {len(products)} products loaded.")
        handlers[client_name](client_name, products)


if __name__ == "__main__":
    main()
