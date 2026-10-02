#!/usr/bin/env python3
"""
Compute an internal PRIORITY SCORE (0-100) for every Myugen product and write it
to a hidden Shopify metafield (custom.priority_score). Used to rank products on
collection + search pages. NEVER shown to customers.

score = 45*orders_norm + 30*views_norm + 25*stock_norm

  orders_norm : units sold (Shopify orders in local DB), normalized to catalog max
  views_norm  : GA4 product-page views (last 90d), normalized to catalog max
  stock_norm  : availability gate (in stock -> ~1, near-empty -> low, sold out -> 0)

Signals:
  - orders : Postgres  shopify_order_items (store MYUGEN)  joined by product_id
  - views  : GA4 Data API  property 535265210  pagePath /products/<handle>
  - stock  : Shopify Admin API  variant inventory_quantity

Usage:
  GOOGLE_APPLICATION_CREDENTIALS=.secrets/myugen-ga-sa.json \
  python tools/compute_priority.py [--dry-run]
"""
import os
import sys
import json
import math
import time
import urllib.request
import urllib.parse

API = "2025-01"
GA_PROPERTY = "535265210"
GA_LOOKBACK = "90daysAgo"
WEIGHTS = {"orders": 45.0, "views": 30.0, "stock": 25.0}
METAFIELD_NS = "custom"
METAFIELD_KEY = "priority_score"

DOMAIN = os.environ["MYUGEN_SHOPIFY_DOMAIN"]
TOKEN = os.environ["MYUGEN_SHOPIFY_ACCESS_TOKEN"]
DRY = "--dry-run" in sys.argv


# ---------- Shopify helpers ----------
def shopify(path, method="GET", body=None):
    url = f"https://{DOMAIN}/admin/api/{API}/{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"X-Shopify-Access-Token": TOKEN,
                                          "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read()), r.headers
        except urllib.error.HTTPError as e:
            if e.code == 429:  # rate limited
                time.sleep(2 * (attempt + 1)); continue
            raise
    raise RuntimeError("shopify retry exhausted: " + path)


def all_products():
    """Return [{id, handle, title, inventory}] across the whole catalog (paginated)."""
    out, page_info = [], None
    while True:
        q = "products.json?limit=250&fields=id,handle,title,variants,status"
        if page_info:
            q = f"products.json?limit=250&page_info={page_info}"
        data, headers = shopify(q)
        for p in data.get("products", []):
            inv = sum((v.get("inventory_quantity") or 0) for v in p.get("variants", []))
            out.append({"id": p["id"], "handle": p["handle"], "title": p["title"],
                        "inventory": inv, "status": p.get("status")})
        link = headers.get("Link", "")
        nxt = None
        for part in link.split(","):
            if 'rel="next"' in part:
                nxt = part[part.find("page_info=") + 10: part.find(">")].split("&")[0]
        if not nxt:
            break
        page_info = nxt
    return out


# ---------- Orders (Postgres) ----------
def orders_by_product():
    """units sold per shopify product_id for MYUGEN."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from flask import Flask
    from db.database import init_app, query
    app = Flask(__name__); init_app(app)
    with app.app_context():
        rows = query("""
            SELECT oi.product_id, SUM(oi.quantity) AS units
            FROM shopify_order_items oi
            JOIN shopify_orders o ON o.id = oi.order_id
            WHERE o.store_prefix = 'MYUGEN' AND oi.product_id IS NOT NULL
            GROUP BY oi.product_id
        """)
    return {str(r["product_id"]): int(r["units"] or 0) for r in rows}


# ---------- Views (GA4) ----------
def views_by_handle():
    """GA4 product-page views (last 90d) keyed by product handle."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, DateRange, Dimension, Metric, Filter, FilterExpression)
    c = BetaAnalyticsDataClient()
    req = RunReportRequest(
        property=f"properties/{GA_PROPERTY}",
        date_ranges=[DateRange(start_date=GA_LOOKBACK, end_date="today")],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews")],
        dimension_filter=FilterExpression(filter=Filter(
            field_name="pagePath",
            string_filter=Filter.StringFilter(
                match_type=Filter.StringFilter.MatchType.BEGINS_WITH,
                value="/products/"))),
        limit=10000,
    )
    resp = c.run_report(req)
    views = {}
    for row in resp.rows:
        path = row.dimension_values[0].value
        v = int(row.metric_values[0].value or 0)
        # /products/<handle>[?variant=..]  -> handle
        handle = path.split("/products/", 1)[1].split("?")[0].split("/")[0].strip("/")
        if handle:
            views[handle] = views.get(handle, 0) + v
    return views


# ---------- scoring ----------
def stock_norm(inv):
    if inv <= 0:
        return 0.0
    # smooth ramp: 0 at sold out, ~1.0 once >= 20 units in stock
    return min(1.0, math.log1p(inv) / math.log1p(20))


def main():
    print("Loading products...")
    products = all_products()
    print(f"  {len(products)} products")
    print("Loading orders (DB)...")
    orders = orders_by_product()
    print(f"  {len(orders)} products with orders")
    print("Loading views (GA4)...")
    views = views_by_handle()
    print(f"  {len(views)} product paths with views")

    max_orders = max([orders.get(str(p["id"]), 0) for p in products] + [1])
    max_views = max([views.get(p["handle"], 0) for p in products] + [1])

    scored = []
    for p in products:
        o = orders.get(str(p["id"]), 0)
        v = views.get(p["handle"], 0)
        on = o / max_orders
        vn = v / max_views
        sn = stock_norm(p["inventory"])
        score = WEIGHTS["orders"] * on + WEIGHTS["views"] * vn + WEIGHTS["stock"] * sn
        scored.append({**p, "orders": o, "views": v, "score": round(score, 2)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    print("\nTop 12 by priority score:")
    for s in scored[:12]:
        print(f"  {s['score']:6.2f}  orders={s['orders']:<4} views={s['views']:<5} stock={s['inventory']:<4} {s['title'][:42]}")

    if DRY:
        print("\n--dry-run: not writing metafields.")
        return

    print("\nWriting metafields...")
    written = 0
    for s in scored:
        # Zero-padded string so Liquid's lexical `sort` == numeric order
        # (e.g. 0100.00 > 0074.66 > 0009.50). Internal value, never shown.
        padded = f"{s['score']:07.2f}"   # 3 int digits + dot + 2 dec -> "0100.00"
        # Upsert: existing metafield (any type) deleted, recreated as text so the
        # padded sort key sticks. (Shopify locks type once set.)
        try:
            data, _ = shopify(f"products/{s['id']}/metafields.json?namespace={METAFIELD_NS}")
            for m in data.get("metafields", []):
                if m["key"] == METAFIELD_KEY:
                    shopify(f"products/{s['id']}/metafields/{m['id']}.json", method="DELETE")
        except Exception:
            pass
        body = {"metafield": {"namespace": METAFIELD_NS, "key": METAFIELD_KEY,
                              "type": "single_line_text_field", "value": padded}}
        try:
            shopify(f"products/{s['id']}/metafields.json", method="POST", body=body)
            written += 1
        except Exception as e:
            print(f"  WARN {s['handle']}: {str(e)[:80]}")
        if written % 25 == 0 and written:
            print(f"  {written}/{len(scored)} written")
            time.sleep(0.5)
    print(f"Done. {written}/{len(scored)} metafields written.")


if __name__ == "__main__":
    main()
