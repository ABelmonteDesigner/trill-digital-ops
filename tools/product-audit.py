import requests
import csv
import os
import sys
from datetime import datetime

# Fix Windows terminal encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Configuration ──────────────────────────────────────────────────────────────

# Fetch all products from /collections/all, then group by product_type.
# Each "group" defines which product_types belong to that category.
# Use None to include ALL product types in a single group.

CLIENTS = {
    "Designer Eyes": {
        "all_products_url": "https://www.designereyes.com/collections/all/products.json",
        "base_url":         "https://www.designereyes.com/products/",
        "groups": {
            "Sunglasses": ["SUNGLASS", "SUNGLASSES"],
            "Eyeglasses": ["OPTICAL"],
        },
    },
    "Shades Eyeconic": {
        "all_products_url": "https://shadeseyeconic.com/collections/all/products.json",
        "base_url":         "https://shadeseyeconic.com/products/",
        # collection_groups: classify products by which Shopify collection they belong to.
        # Fetches handles from each collection URL, then matches against full catalog.
        # "None" group catches everything not matched.
        "collection_groups": {
            "Sunglasses": "https://shadeseyeconic.com/collections/sunglasses/products.json",
            "Eyeglasses": "https://shadeseyeconic.com/collections/eyeglasses/products.json",
            "Apparel":    None,
        },
    },
}

MAX_PRICE = 5000.0
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Fetch ───────────────────────────────────────────────────────────────────────

def fetch_all_products(url: str) -> list:
    products = []
    page = 1
    while True:
        try:
            r = requests.get(url, params={"limit": 250, "page": page}, timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  ERROR fetching page {page}: {e}")
            break

        batch = r.json().get("products", [])
        if not batch:
            break

        products.extend(batch)
        print(f"    Page {page}: {len(batch)} products fetched...")

        if len(batch) < 250:
            break
        page += 1

    return products

# ── Group ───────────────────────────────────────────────────────────────────────

def fetch_collection_handles(url: str) -> set:
    handles = set()
    for page in range(1, 20):
        try:
            r = requests.get(url, params={"limit": 250, "page": page}, timeout=15)
            r.raise_for_status()
        except requests.RequestException:
            break
        batch = r.json().get("products", [])
        if not batch:
            break
        for p in batch:
            handles.add(p["handle"])
    return handles

def group_by_collections(products: list, collection_groups: dict) -> dict:
    # Build handle → group mapping
    handle_to_group = {}
    for name, url in collection_groups.items():
        if url is None:
            continue
        print(f"    Loading collection handles: {name}...")
        for handle in fetch_collection_handles(url):
            handle_to_group[handle] = name

    grouped = {name: [] for name in collection_groups}
    for product in products:
        group = handle_to_group.get(product["handle"])
        if group:
            grouped[group].append(product)
        else:
            # Find the None-keyed group (catch-all)
            for name, url in collection_groups.items():
                if url is None:
                    grouped[name].append(product)
                    break

    return grouped

def group_products(products: list, groups: dict) -> dict:
    grouped = {name: [] for name in groups}
    assigned_types = set()

    for name, types in groups.items():
        if types is None:
            continue
        for p in products:
            if p.get("product_type", "").upper() in [t.upper() for t in types]:
                grouped[name].append(p)
                assigned_types.add(p.get("product_type", "").upper())

    # "None" group catches everything not assigned above
    for name, types in groups.items():
        if types is None:
            grouped[name] = [
                p for p in products
                if p.get("product_type", "").upper() not in assigned_types
            ]

    return grouped

# ── Checks ──────────────────────────────────────────────────────────────────────

def check_product(product: dict) -> list:
    issues = []

    if not product.get("images"):
        issues.append("NO MAIN PHOTO")

    for variant in product.get("variants", []):
        try:
            price = float(variant.get("price", 0))
        except ValueError:
            continue
        if price >= MAX_PRICE:
            issues.append(f"PRICE ${price:,.2f} (exceeds ${MAX_PRICE:,.0f})")
            break

    return issues

# ── Output ──────────────────────────────────────────────────────────────────────

def print_header():
    now = datetime.now().strftime("%Y-%m-%d  %H:%M")
    print()
    print("=" * 62)
    print("   Daily Product Audit — Designer Eyes & Shades Eyeconic")
    print(f"   {now}")
    print("=" * 62)
    print()

def print_summary(total: int, flagged: int):
    print()
    print("=" * 62)
    print("   FINAL SUMMARY")
    print("=" * 62)
    print(f"   Total products checked  : {total}")
    print(f"   Passed                  : {total - flagged}")
    print(f"   Flagged                 : {flagged}")
    print("=" * 62)
    print()

def save_csv(rows: list, timestamp: str):
    if not rows:
        print("   No issues found — CSV not generated.\n")
        return

    filename = os.path.join(OUTPUT_DIR, f"audit_{timestamp}.csv")
    fieldnames = ["client", "group", "product_type", "title", "issues", "url"]

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"   CSV saved: {filename}\n")

# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    flagged_rows = []
    total_checked = 0

    print_header()

    for client_name, client in CLIENTS.items():
        print("=" * 62)
        print(f"  CLIENT: {client_name.upper()}")
        print("=" * 62)
        print()
        print(f"  Fetching full catalog...")

        all_products = fetch_all_products(client["all_products_url"])
        print(f"  Total fetched: {len(all_products)} products\n")

        if "collection_groups" in client:
            grouped = group_by_collections(all_products, client["collection_groups"])
        else:
            grouped = group_products(all_products, client["groups"])

        for group_name, products in grouped.items():
            print(f"  Group: {group_name.upper()} ({len(products)} products)")
            print("-" * 62)

            total_checked += len(products)
            group_flags = 0

            for product in products:
                issues = check_product(product)
                if not issues:
                    continue

                group_flags += 1
                product_url = client["base_url"] + product["handle"]
                issues_str = "  |  ".join(issues)

                print(f"  WARNING  {product['title']}")
                print(f"    Issues : {issues_str}")
                print(f"    URL    : {product_url}")
                print()

                flagged_rows.append({
                    "client":       client_name,
                    "group":        group_name,
                    "product_type": product.get("product_type", "N/A"),
                    "title":        product["title"],
                    "issues":       issues_str,
                    "url":          product_url,
                })

            if group_flags == 0:
                print(f"  All {len(products)} products passed.\n")
            else:
                print(f"  {group_flags} product(s) flagged.\n")

        print()

    print_summary(total_checked, len(flagged_rows))
    save_csv(flagged_rows, timestamp)


if __name__ == "__main__":
    main()
