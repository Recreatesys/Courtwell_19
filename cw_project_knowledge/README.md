# cw_project_knowledge

Connects the **Project** app to the **Knowledge** app so merchandiser learnings become company
memory. Built for the CW001 merchandising template.

## What it does

| Feature | Detail |
|---|---|
| **Knowledge Capture field** | An Html field (notebook tab) on every `project.task`, separate from the SOP Description. This is where merchandisers log findings. |
| **Auto article per project** | On `project.project` create (non-template), creates one `knowledge.article` named after the project, parented under a shared workspace article **"Project Knowledge Base"**. Stored in `project.knowledge_article_id`. |
| **Sync to Knowledge Base** | Button on the project form. Rebuilds the article `body` from every task's Knowledge Capture note, grouped by stage (ordered by stage then task sequence). |
| **Knowledge Article** button | Opens the linked article. |

Failures during article creation are logged (`_logger.warning`) and never block project creation.
Article writes use `sudo()` so Project users without Knowledge-write rights can still sync; the
root article is created with `internal_permission = 'write'` (workspace, all internal users).

## Models touched
- `project.task` — adds `cw_knowledge_note` (Html).
- `project.project` — adds `knowledge_article_id` (M2o), `action_sync_knowledge`,
  `action_open_knowledge_article`, `_ensure_knowledge_article`, `_render_knowledge_body`,
  `_get_knowledge_root`; overrides `create`.

No new models, so no ACL/security file is required.

## Dependencies
`project`, `knowledge` (both installed on CW19_Test).

## Deploy (CW19_Test)

Standard recipe (see memory `contabo-odoo-layout`). Run from a shell with the SSH key:

```bash
KEY=/c/Users/CW-LT1/OD19/cw_contabo_RSA_Dev
scp -i "$KEY" -r custom-addons/cw_project_knowledge \
    root@courtwell.com.hk:/opt/odoo19/odoo19/custom-addons/
ssh -i "$KEY" root@courtwell.com.hk \
    "chown -R odoo19:odoo19 /opt/odoo19/odoo19/custom-addons/cw_project_knowledge && \
     systemctl stop odoo19 && \
     sudo -u odoo19 /opt/odoo19/odoo19-venv/bin/python3 /opt/odoo19/odoo19/odoo-bin \
        -c /etc/odoo19.conf -d CW19_Test -i cw_project_knowledge \
        --stop-after-init --no-http --logfile=/tmp/install_cwpk.log && \
     systemctl start odoo19"
```

Verify:
```bash
ssh -i "$KEY" root@courtwell.com.hk \
  "sudo -u postgres psql -d CW19_Test -tAc \
   \"SELECT name, state FROM ir_module_module WHERE name='cw_project_knowledge';\""
```

## Notes on existing projects
Auto-creation fires only for projects created **after** install. Existing projects get their
article on the first **Sync to Knowledge Base** click (the method calls `_ensure_knowledge_article`
first). To backfill all at once, run a server action calling `action_sync_knowledge()` on the
relevant `project.project` recordset.

## Behaviour knobs
- Pass context `cw_skip_knowledge=True` on `project.project.create(...)` to suppress
  auto-article creation (e.g. bulk imports).
- Templates (`is_template = True`) never get an article.
