def uninstall_hook(env):
    """Restore the standard res.partner list/kanban views to "all employees"
    visibility. The install-time <function> in data/view_lockdown_data.xml
    narrowed group_ids to group_contacts_full_view; here we clear that gate.

    Field name note: Odoo 19 uses group_ids (M2M to res.groups) on
    ir.ui.view; older Odoo versions called this groups_id.
    """
    view_xml_ids = (
        'base.view_partner_tree',
        'base.res_partner_kanban_view',
    )
    views = env['ir.ui.view']
    for xml_id in view_xml_ids:
        view = env.ref(xml_id, raise_if_not_found=False)
        if view:
            views |= view
    if views:
        views.write({'group_ids': [(5, 0, 0)]})
