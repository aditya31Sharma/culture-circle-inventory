"""
Website Revamp routes — track per-store theme revamp status, draft preview
links, and the per-page element checklist. Read-only views over the revamp_*
tables seeded by tools/revamp_seed.py.
"""
from flask import Blueprint, render_template
from db.database import query

revamp_bp = Blueprint('revamp', __name__, url_prefix='/revamp')

# Canonical element + page ordering for display.
PAGES = ['home', 'collection', 'product', 'cart']
ELEMENTS = ['banner', 'category_cards', 'featured_carousel', 'vertical_grid']
ELEMENT_LABELS = {
    'banner': 'Banner',
    'category_cards': 'Category Cards',
    'featured_carousel': 'Featured Carousel',
    'vertical_grid': 'Vertical Grid',
}


@revamp_bp.route('/')
def index():
    stores = query("SELECT * FROM revamp_stores ORDER BY store_name")

    # Build a checklist lookup: {prefix: {page: {element: row}}}
    rows = query("SELECT * FROM revamp_checklist")
    checklist = {}
    for r in rows:
        checklist.setdefault(r['store_prefix'], {}).setdefault(r['page'], {})[r['element']] = r

    # Recent activity per store.
    activity = {}
    for a in query("SELECT * FROM revamp_activity ORDER BY created_at DESC LIMIT 200"):
        activity.setdefault(a['store_prefix'], []).append(a)

    # Per-store progress summary (found vs total expected).
    summary = {}
    for s in stores:
        pfx = s['prefix']
        cells = [c for page in checklist.get(pfx, {}).values() for c in page.values()]
        total = len(cells)
        done = len([c for c in cells if c['status'] in ('found', 'done')])
        summary[pfx] = {'done': done, 'total': total,
                        'pct': round(done / total * 100) if total else 0}

    return render_template(
        'revamp.html',
        stores=stores,
        checklist=checklist,
        activity=activity,
        summary=summary,
        pages=PAGES,
        elements=ELEMENTS,
        element_labels=ELEMENT_LABELS,
    )
