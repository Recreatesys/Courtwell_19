{
    'name': "Courtwell Contacts: Restricted View",
    'version': '19.0.1.0.0',
    'category': 'Contacts',
    'summary': "Limit the Contacts app to a form-only UI for everyone except Howard",
    'description': """
Courtwell Contacts — Restricted View
====================================

Goal
----
Prevent merchandisers, shipping, and other non-directory staff from
browsing the full Contacts list / kanban / pivot. They retain the
ability to:

* Create new contacts via a form
* Look up an existing contact one at a time via a Many2one autocomplete
  wizard (no list dialog)
* Edit contacts they themselves created

The "Contacts / Full Directory Access" group is the single source of
truth for who sees the full Contacts app. Only Howard is in this group
by default; assignment is manual via Settings -> Users.

Mechanism
---------
1. ``group_contacts_full_view`` — custom group, Howard-only.
2. ``contacts.menu_contacts`` is gated to that group (only Howard sees
   the standard Contacts icon and its kanban/list/form/pivot views).
3. A new top-level menu ``menu_contacts_limited`` ("Contacts") is
   visible to every internal user. It points at
   ``action_contacts_limited`` which exposes ``view_mode="form"`` only.
4. A sub-menu opens the ``cw.contact.lookup`` wizard — a transient
   model with a single ``res.partner`` Many2one. The autocomplete
   shows up to ~8 matches as the user types; an "Open Contact" button
   returns an act_window opening the chosen partner in form view.
5. ``ir.rule`` rows restrict write/unlink on ``res.partner`` to records
   the user created themselves, with a permissive bypass rule scoped
   to ``group_contacts_full_view`` so Howard retains full edit.
6. On install, the module patches ``groups_id`` of the standard list /
   kanban res.partner views so they are only visible to Howard. This
   is defense-in-depth: it also hides the list/kanban from the
   "Search More" dialog of any res.partner Many2one across the ERP.
   The ``uninstall_hook`` reverses this patch on module removal.

Trade-offs and known side effects
---------------------------------
* **Two Contacts icons for Howard.** Howard sees both the standard
  Contacts icon (full app) and the limited Contacts icon (form-only).
  He uses the standard one and ignores the other. Chosen over a
  server-action branch for simpler XML and easier uninstall.

* **Partner write is restricted to "own only" for ALL non-Howard
  internal users, system-wide.** This includes accounting, sales, and
  any other roles. If a merchandiser tries to edit a supplier's phone
  number from inside a purchase order, the change will be blocked
  unless that supplier was created by the same user. If this is too
  tight in practice, the fastest fix is to add
  ``base.group_system`` (or ``account.group_account_user``) to
  ``group_contacts_full_view.implied_ids`` so admins / bookkeepers
  bypass the rule.

* **Ctrl+K command palette** still surfaces contact names that the
  user has read access to. ACL grants broad read on res.partner
  (required for partner fields to render across the ERP). The palette
  shows the partner's form on selection, not a list — acceptable.

* **Module uninstall** restores ``groups_id`` on the standard partner
  views via the ``uninstall_hook``. The custom group and any user
  assignments are also removed by the usual Odoo uninstall flow.

Assignment
----------
Add Howard to "Contacts / Full Directory Access" via
Settings -> Users & Companies -> Users -> Howard -> Other -> Contacts.
This module does not pin a specific user.
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'base',
        'contacts',
    ],
    'data': [
        'security/cw_contacts_restrict_groups.xml',
        'security/cw_contacts_restrict_rules.xml',
        'security/ir.model.access.csv',
        'wizard/contact_lookup_views.xml',
        'data/menu_action_data.xml',
        'data/view_lockdown_data.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'uninstall_hook': 'uninstall_hook',
}
