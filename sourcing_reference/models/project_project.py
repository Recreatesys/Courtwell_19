from odoo import _, api, fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    sourcing_reference = fields.Char(
        string='Sourcing Ref',
        readonly=True,
        copy=False,
        index=True,
        tracking=True,
        help='Inherited from the originating Sale Order. '
             'Format: PR-{ClientCode}-{SegmentCode}-{YY}-{NNN}. '
             'Phase 3 propagation: triggered when project is created from SO.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        for project, vals in zip(projects, vals_list):
            if project.sourcing_reference:
                continue

            # Walk to the opportunity if possible (via SO link).
            so = project.sale_order_id if 'sale_order_id' in project._fields else False
            if not so and 'sale_order_id' in vals:
                so = self.env['sale.order'].search(
                    [('order_line.project_id', '=', project.id)], limit=1
                )
            opp = False
            if so and 'opportunity_id' in so._fields:
                opp = so.opportunity_id

            # Preferred path: opportunity carries the canonical PR- reference,
            # generated at opp creation (sourcing_reference v19.0.1.3.0+).
            # Copy it directly — it's already in PR- form.
            if opp and opp.project_reference:
                project.sourcing_reference = opp.project_reference
                continue

            # Legacy fallback: derive PR- from the SO's QP- (pre-1.3.0 opps
            # that never got a project_reference backfilled).
            if so and so.sourcing_reference:
                base = so.sourcing_reference.strip()
                if base.startswith('QP-'):
                    project.sourcing_reference = 'PR-' + base[3:]
        return projects
