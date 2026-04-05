from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    attachment_notes = fields.Html(
        string='Attachment',
        sanitize=True,
        sanitize_overridable=True,
    )
