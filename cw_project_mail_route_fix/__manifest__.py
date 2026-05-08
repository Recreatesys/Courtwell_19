{
    'name': 'CW Project — Mail Route Fix',
    'version': '19.0.1.0.0',
    'summary': 'Defensive fix for upstream ValueError when routing incoming mail to project tasks',
    'description': """
Workaround for an upstream Odoo 19 bug at
addons/project/models/project_task.py:1685 where
``unmatched_partner_emails.remove(project_alias_address)`` is called
unconditionally. The alias is not always present in the list (notably for
mail routed via direct alias match), so the call raises
``ValueError: list.remove(x): x not in list`` and the incoming email fails
to be converted to a project task.

This module overrides ``_find_internal_users_from_address_mail`` on
``project.task`` and guards the remove() with an ``in`` check.

Auto-installs wherever ``project`` is installed; safe to uninstall once
upstream ships a fix.
""",
    'author': 'CW Internal',
    'category': 'Project',
    'depends': ['project'],
    'auto_install': True,
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
