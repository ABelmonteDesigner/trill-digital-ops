import requests, sys
sys.stdout.reconfigure(encoding="utf-8")

all_products = []
for page in range(1, 20):
    r = requests.get("https://shadeseyeconic.com/collections/all/products.json", params={"limit": 250, "page": page}, timeout=15)
    batch = r.json().get("products", [])
    if not batch:
        break
    all_products.extend(batch)

known_brands = set(p["vendor"].upper() for p in all_products if p["vendor"] != "ShadesEyeconic")
print("Known brands from vendor field:", known_brands)
print()

unmatched = []
for p in all_products:
    if p["vendor"] != "ShadesEyeconic":
        continue
    tag_brands = [t.upper() for t in p["tags"] if t.upper() in known_brands]
    if not tag_brands:
        unmatched.append(p)

print(f"ShadesEyeconic products with NO brand tag match: {len(unmatched)}")
for p in unmatched[:10]:
    title = p["title"]
    tags = p["tags"]
    handle = p["handle"]
    print(f"  {title} | tags: {tags} | handle: {handle}")
