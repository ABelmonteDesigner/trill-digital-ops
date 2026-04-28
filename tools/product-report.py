import requests
import sys
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


def print_designer_eyes(client_name, products):
    known_brands = set(
        p["vendor"].upper() for p in products
        if p.get("vendor", "") not in STORE_VENDORS
    )

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
