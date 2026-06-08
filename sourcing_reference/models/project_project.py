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
            so = project.sale_order_id if 'sale_order_id' in project._fields else False
            if not so and 'sale_order_id' in vals:
                so = self.env['sale.order'].search(
                    [('order_line.project_id', '=', project.id)], limit=1
                )
            if so and so.sourcing_reference:
                base = so.sourcing_reference.strip()
                if base.startswith('QP-'):
                    project.sourcing_reference = 'PR-' + base[3:]
        return projects
