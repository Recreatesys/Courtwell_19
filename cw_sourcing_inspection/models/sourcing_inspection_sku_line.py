from odoo import fields, models


class SourcingInspectionSkuLine(models.Model):
    """Per-SKU detail row of an inspection — corresponds to the bottom
    grid of the paper QC form (貨號 / 訂單數量 / 抽驗數量 / 質量通過 /
    立即修復 / 不可修復).

    Optional: many inspections (single-SKU shipments) won't need lines
    at all. Useful when one inspection covers multiple LED bulb models,
    for example.
    """
    _name = 'sourcing.inspection.sku.line'
    _description = 'Inspection SKU Detail Line'
    _order = 'inspection_id, sequence, id'

    inspection_id = fields.Many2one(
        'sourcing.inspection',
        string='Inspection',
        required=True,
        ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)

    item_code = fields.Char(
        string='Item No.',
        help='Supplier SKU / item code printed on the inspection form.',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help='Optional link to a system product. Free-text item_code '
             'is the primary identifier.',
    )
    description = fields.Char(
        string='Description',
        help='Product description or specification note.',
    )

    ordered_qty = fields.Float(string='Ordered Qty')
    sampled_qty = fields.Float(string='Sampled Qty')

    quality_pass    = fields.Boolean(string='Quality Pass')
    immediate_repair = fields.Boolean(string='Immediate Repair')
    not_repairable  = fields.Boolean(string='Not Repairable')

    notes = fields.Char(string='Line Notes')
