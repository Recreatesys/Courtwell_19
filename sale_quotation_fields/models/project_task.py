from odoo import api, fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    payment_status = fields.Selection(
        [
            ('not_invoiced', 'Not Invoiced'),
            ('not_paid', 'Not Paid'),
            ('partial', 'Partially Paid'),
            ('paid', 'Paid'),
        ],
        string='Payment Status',
        compute='_compute_payment_status',
        store=True,
    )

    @api.depends(
        'sale_line_id',
        'sale_line_id.order_id.invoice_ids.state',
        'sale_line_id.order_id.invoice_ids.payment_state',
        'sale_line_id.order_id.invoice_ids.move_type',
    )
    def _compute_payment_status(self):
        for task in self:
            order = task.sale_line_id.order_id
            if not order:
                task.payment_status = False
                continue
            invoices = order.invoice_ids.filtered(
                lambda inv: inv.state == 'posted' and inv.move_type == 'out_invoice'
            )
            if not invoices:
                task.payment_status = 'not_invoiced'
            elif all(inv.payment_state in ('paid', 'in_payment') for inv in invoices):
                task.payment_status = 'paid'
            elif any(inv.payment_state in ('paid', 'in_payment', 'partial') for inv in invoices):
                task.payment_status = 'partial'
            else:
                task.payment_status = 'not_paid'
