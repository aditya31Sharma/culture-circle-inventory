#!/usr/bin/env python3
"""
Seed / refresh the revamp tables for a pilot store: records the store row
(live + draft theme, preview link) and runs the audit to fill the checklist.

Usage:
    python tools/revamp_seed.py <PREFIX> <DOMAIN> <TOKEN> \
        <LIVE_THEME_ID> <LIVE_THEME_NAME> <DRAFT_THEME_ID> <DRAFT_THEME_NAME>
"""
import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from flask import Flask
from db.database import init_app, execute, query

HERE = os.path.dirname(__file__)


def run_audit(domain, token, draft_id):
    out = subprocess.check_output(
        [sys.executable, os.path.join(HERE, "revamp_audit.py"), domain, token, str(draft_id)],
        text=True,
    )
    return json.loads(out)


def seed(prefix, domain, token, live_id, live_name, draft_id, draft_name):
    preview = f"https://{domain}?preview_theme_id={draft_id}"
    editor = f"https://{domain}/admin/themes/{draft_id}/editor"
    report = run_audit(domain, token, draft_id)

    execute(
        """
        INSERT INTO revamp_stores
            (prefix, store_name, domain, live_theme_id, live_theme_name,
             draft_theme_id, draft_theme_name, preview_url, editor_url,
             status, current_activity, last_audited_at, updated_at)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'audited',
                'Audit complete — review missing sections', NOW(), NOW())
        ON CONFLICT (prefix) DO UPDATE SET
            store_name=EXCLUDED.store_name, domain=EXCLUDED.domain,
            live_theme_id=EXCLUDED.live_theme_id, live_theme_name=EXCLUDED.live_theme_name,
            draft_theme_id=EXCLUDED.draft_theme_id, draft_theme_name=EXCLUDED.draft_theme_name,
            preview_url=EXCLUDED.preview_url, editor_url=EXCLUDED.editor_url,
            status='audited', current_activity='Audit complete — review missing sections',
            last_audited_at=NOW(), updated_at=NOW()
        """,
        (prefix, prefix.replace("_", " ").title(), domain, live_id, live_name,
         draft_id, draft_name, preview, editor),
    )

    for page, pdata in report["pages"].items():
        tpl = pdata.get("template")
        for element, info in pdata.get("checklist", {}).items():
            execute(
                """
                INSERT INTO revamp_checklist
                    (store_prefix, page, element, status, evidence, template_key, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,NOW())
                ON CONFLICT (store_prefix, page, element) DO UPDATE SET
                    status=EXCLUDED.status, evidence=EXCLUDED.evidence,
                    template_key=EXCLUDED.template_key, updated_at=NOW()
                """,
                (prefix, page, element, info["status"], info.get("evidence"), tpl),
            )

    execute(
        "INSERT INTO revamp_activity (store_prefix, message) VALUES (%s,%s)",
        (prefix, f"Duplicated live theme #{live_id} -> draft #{draft_id}; audit complete."),
    )

    missing = query(
        "SELECT page, element FROM revamp_checklist WHERE store_prefix=%s AND status='missing' ORDER BY page",
        (prefix,),
    )
    print(f"Seeded {prefix}: {len(missing)} missing element(s)")
    for m in missing:
        print(f"  - {m['page']}: {m['element']}")


def main():
    args = sys.argv[1:]
    app = Flask(__name__)
    init_app(app)
    with app.app_context():
        seed(*args)


if __name__ == "__main__":
    main()
