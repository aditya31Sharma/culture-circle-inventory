#!/usr/bin/env python3
"""
Revamp audit: for a given store theme, fetch the key page templates + the
sections they reference, then detect which standardized elements exist on each
page. Read-only — never writes to the theme.

Usage:
    python tools/revamp_audit.py <DOMAIN> <ACCESS_TOKEN> <THEME_ID>

Prints a JSON report: per page -> {element: found|missing} plus evidence.
"""
import sys
import json
import urllib.parse
import urllib.request

API = "2025-01"

# Pages we audit and the template key that drives each.
PAGES = {
    "home": ["templates/index.json", "templates/index.liquid"],
    "collection": ["templates/collection.json", "templates/collection.liquid"],
    "product": ["templates/product.json", "templates/product.liquid"],
    "cart": ["templates/cart.json", "templates/cart.liquid"],
}

# Checklist elements -> keyword signals found in section TYPES or liquid source.
# We match against section `type` names and raw liquid for robustness.
ELEMENT_SIGNALS = {
    "banner": ["banner", "hero", "slideshow", "image-banner", "image_banner"],
    "category_cards": ["collection-list", "collection_list", "category", "collage", "collection-cards"],
    "featured_carousel": ["featured-collection", "featured_collection", "carousel", "slider", "product-recommendations", "featured-product"],
    "vertical_grid": ["main-collection-product-grid", "product-grid", "collection-grid", "product_grid", "main-product-grid"],
}

# Which elements are expected on which page (so "missing" means missing where it matters).
PAGE_EXPECTATIONS = {
    "home": ["banner", "category_cards", "featured_carousel", "vertical_grid"],
    "collection": ["banner", "vertical_grid"],
    "product": ["featured_carousel"],  # related/recommended products carousel
    "cart": [],  # cart has no merchandising checklist; audited for completeness only
}


def api_get(domain, token, path):
    url = f"https://{domain}/admin/api/{API}/{path}"
    req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": token})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def get_asset(domain, token, theme_id, key):
    q = urllib.parse.urlencode({"asset[key]": key})
    try:
        d = api_get(domain, token, f"themes/{theme_id}/assets.json?{q}")
        return (d.get("asset") or {}).get("value", "")
    except Exception:
        return ""


def detect(text, section_types):
    """Return which elements are present given combined liquid text + section type list."""
    hay = (text or "").lower() + " " + " ".join(section_types).lower()
    found = {}
    for element, signals in ELEMENT_SIGNALS.items():
        hit = next((s for s in signals if s in hay), None)
        found[element] = hit  # signal string or None
    return found


def audit_page(domain, token, theme_id, template_keys):
    """Fetch whichever template variant exists, plus its sections, and detect elements."""
    tpl_value, tpl_key = "", None
    for key in template_keys:
        v = get_asset(domain, token, theme_id, key)
        if v:
            tpl_value, tpl_key = v, key
            break
    if not tpl_key:
        return {"template": None, "elements": {}, "section_types": [], "note": "template missing"}

    section_types = []
    combined_text = tpl_value

    if tpl_key.endswith(".json"):
        try:
            data = json.loads(tpl_value)
            for sid, sec in (data.get("sections") or {}).items():
                stype = sec.get("type", "")
                section_types.append(stype)
                # pull the section liquid too for keyword evidence
                sec_src = get_asset(domain, token, theme_id, f"sections/{stype}.liquid")
                combined_text += "\n" + sec_src
        except Exception as e:
            combined_text += f"\n(JSON parse error: {e})"
    # for .liquid templates, combined_text already holds the source

    elements = detect(combined_text, section_types)
    return {"template": tpl_key, "elements": elements, "section_types": section_types}


def main():
    domain, token, theme_id = sys.argv[1], sys.argv[2], sys.argv[3]
    report = {"theme_id": theme_id, "pages": {}}
    for page, keys in PAGES.items():
        res = audit_page(domain, token, theme_id, keys)
        expected = PAGE_EXPECTATIONS.get(page, [])
        checklist = {}
        for el in expected:
            sig = res["elements"].get(el)
            checklist[el] = {"status": "found" if sig else "missing", "evidence": sig}
        report["pages"][page] = {
            "template": res["template"],
            "checklist": checklist,
            "all_section_types": res["section_types"],
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
