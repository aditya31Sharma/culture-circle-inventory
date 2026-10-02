#!/usr/bin/env python3
"""
Build the storefront SEARCH INDEX for a Shopify theme and upload it as a theme
asset (assets/rv-search-index.json). The rv-search overlay reads this file so
EVERY product title (e.g. "aura") is suggestable, ranked by popularity.

This is a MANUAL sync (no cron). Run it on purpose after catalog/popularity
changes. Designed to be SCALABLE across many brands: point it at any store via
env vars / flags, or sync all brands at once from a brands config.

Index shape (short keys keep the asset small):
  { "generated", "store", "count",
    "collections": [{ "title", "handle" }],
    "products":    [{ "t":title, "h":handle, "ty":type, "tg":[tags],
                      "img":featured_image, "price":min_price, "p":popularity }] }

popularity (p) = custom.priority_score metafield (0-100), written by
tools/compute_priority.py. Missing -> 0 (still searchable, just unranked).

Usage:
  # single brand (env)
  MYUGEN_SHOPIFY_DOMAIN=xfjetw-dv.myshopify.com \
  MYUGEN_SHOPIFY_ACCESS_TOKEN=shpat_xxx \
  MYUGEN_THEME_ID=162712748280 \
  python tools/sync_search_index.py

  # single brand (flags override env)
  python tools/sync_search_index.py --store foo.myshopify.com --token shpat_xxx --theme 123

  # ALL brands from a config (scales to 20+)
  python tools/sync_search_index.py --brands tools/brands.json

  # preview without uploading
  python tools/sync_search_index.py --dry-run

brands.json format:
  [ { "name":"Myugen", "store":"xfjetw-dv.myshopify.com",
      "token":"shpat_xxx", "theme":"162712748280" }, ... ]
"""
import os
import sys
import json
import time
import argparse
import datetime
import urllib.request
import urllib.error

API = "2024-10"
ASSET_KEY = "assets/rv-search-index.json"


def gql(store, token, query, variables=None):
    url = f"https://{store}/admin/api/{API}/graphql.json"
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            if data.get("errors"):
                raise RuntimeError(json.dumps(data["errors"])[:300])
            # GraphQL throttling -> back off
            cost = data.get("extensions", {}).get("cost", {})
            avail = cost.get("throttleStatus", {}).get("currentlyAvailable")
            if avail is not None and avail < 200:
                time.sleep(1.0)
            return data["data"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503):
                time.sleep(2 * (attempt + 1)); continue
            raise
    raise RuntimeError("gql retry exhausted")


def rest_put(store, token, theme, key, value):
    url = f"https://{store}/admin/api/{API}/themes/{theme}/assets.json"
    body = json.dumps({"asset": {"key": key, "value": value}}).encode()
    req = urllib.request.Request(
        url, data=body, method="PUT",
        headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (429, 502, 503):
                time.sleep(2 * (attempt + 1)); continue
            raise RuntimeError(f"asset PUT {e.code}: {e.read().decode()[:300]}")
    raise RuntimeError("asset PUT retry exhausted")


def fetch_collections(store, token):
    out, cursor = [], None
    while True:
        q = """
        query($c:String){ collections(first:100, after:$c){
          pageInfo{ hasNextPage endCursor }
          nodes{ handle title } } }"""
        d = gql(store, token, q, {"c": cursor})["collections"]
        for c in d["nodes"]:
            if c["handle"] in ("frontpage", "all"):
                continue
            out.append({"title": c["title"], "handle": c["handle"]})
        if not d["pageInfo"]["hasNextPage"]:
            break
        cursor = d["pageInfo"]["endCursor"]
    return out


def fetch_products(store, token):
    out, cursor = [], None
    while True:
        q = """
        query($c:String){ products(first:200, after:$c, query:"status:active"){
          pageInfo{ hasNextPage endCursor }
          nodes{
            handle title productType tags vendor
            featuredImage{ url }
            priceRangeV2{ minVariantPrice{ amount } }
            metafield(namespace:"custom", key:"priority_score"){ value }
          } } }"""
        d = gql(store, token, q, {"c": cursor})["products"]
        for p in d["nodes"]:
            try:
                pop = round(float((p.get("metafield") or {}).get("value") or 0), 2)
            except (TypeError, ValueError):
                pop = 0.0
            try:
                price = float(p["priceRangeV2"]["minVariantPrice"]["amount"])
            except (TypeError, KeyError, ValueError):
                price = 0.0
            rec = {
                "t": p["title"],
                "h": p["handle"],
                "ty": p.get("productType") or "",
                "tg": [t for t in (p.get("tags") or [])][:12],
                "img": (p.get("featuredImage") or {}).get("url") or "",
                "price": price,
                "p": pop,
            }
            out.append(rec)
        if not d["pageInfo"]["hasNextPage"]:
            break
        cursor = d["pageInfo"]["endCursor"]
    return out


def sync_brand(name, store, token, theme, dry=False):
    print(f"\n=== {name or store} ===")
    print("  collections...", end="", flush=True)
    collections = fetch_collections(store, token)
    print(f" {len(collections)}")
    print("  products...", end="", flush=True)
    products = fetch_products(store, token)
    print(f" {len(products)}")
    # popularity desc so the array is pre-ranked (client still re-ranks by match)
    products.sort(key=lambda x: x["p"], reverse=True)

    index = {
        "generated": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "store": store.split(".")[0],
        "count": len(products),
        "collections": collections,
        "products": products,
    }
    payload = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    kb = len(payload.encode()) / 1024
    print(f"  index: {len(products)} products, {len(collections)} collections, {kb:.1f} KB")
    with_pop = sum(1 for p in products if p["p"] > 0)
    print(f"  popularity-scored: {with_pop}/{len(products)}  (run compute_priority.py to raise this)")

    sample = next((p["t"] for p in products if "aura" in p["t"].lower()), None)
    if sample:
        print(f"  sanity: 'aura' -> {sample}")

    if dry:
        print("  --dry-run: not uploading.")
        return
    if not theme:
        print("  ERROR: no theme id (set --theme or MYUGEN_THEME_ID). Skipping upload.")
        return
    print(f"  uploading {ASSET_KEY} -> theme {theme} ...", end="", flush=True)
    rest_put(store, token, theme, ASSET_KEY, payload)
    print(" done.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--store"); ap.add_argument("--token"); ap.add_argument("--theme")
    ap.add_argument("--brands", help="path to brands.json for multi-brand sync")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.brands:
        with open(a.brands) as f:
            brands = json.load(f)
        for b in brands:
            try:
                sync_brand(b.get("name"), b["store"], b["token"], b.get("theme"), a.dry_run)
            except Exception as e:
                print(f"  FAILED {b.get('name') or b.get('store')}: {str(e)[:200]}")
        return

    store = a.store or os.environ.get("MYUGEN_SHOPIFY_DOMAIN")
    token = a.token or os.environ.get("MYUGEN_SHOPIFY_ACCESS_TOKEN")
    theme = a.theme or os.environ.get("MYUGEN_THEME_ID")
    if not store or not token:
        sys.exit("Missing store/token. Use --store/--token or MYUGEN_SHOPIFY_* env vars.")
    sync_brand("Myugen", store, token, theme, a.dry_run)


if __name__ == "__main__":
    main()
