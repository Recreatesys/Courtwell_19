from odoo import _, fields, models

REINVOICE_CATEGORY = 'Re-invoice Expenses'


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    reinvoice_id = fields.Many2one(
        'account.move',
        string='Re-invoice Draft',
        copy=False,
        readonly=True,
        ondelete='set null',
    )

    def action_submit(self):
        # For each Re-invoice Expenses expense that has no receipt, open the
        # upload wizard instead of proceeding.  Only check the first offender
        # so the wizard can resolve it; remaining expenses are handled after
        # the user re-submits.
        for expense in self:
            if expense.product_id.name != REINVOICE_CATEGORY:
                continue
            attachment_count = self.env['ir.attachment'].search_count([
                ('res_model', '=', 'hr.expense'),
                ('res_id', '=', expense.id),
            ])
            if attachment_count == 0:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Receipt Required'),
                    'res_model': 'expense.receipt.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_expense_id': expense.id},
                }

        result = super().action_submit()

        # After successful submission, create a draft invoice for every
        # Re-invoice Expenses record that doesn't have one yet.
        for expense in self.filtered(
            lambda e: e.product_id.name == REINVOICE_CATEGORY and not e.reinvoice_id
        ):
            expense._create_reinvoice()

        return result

    def _create_reinvoice(self):
        self.ensure_one()

        # Resolve customer: prefer the project customer linked via the
        # expense's analytic distribution, fall back to the employee's address.
        partner = self.env['res.partner']
        if self.analytic_distribution:
            analytic_id = int(next(iter(self.analytic_distribution)))
            project = self.env['project.project'].search(
                [('account_id', '=', analytic_id)], limit=1
            )
            if project and project.partner_id:
                partner = project.partner_id
        if not partner:
            partner = (
                self.employee_id.address_home_id
                or self.employee_id.user_id.partner_id
            )

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'invoice_origin': self.name,
            'partner_id': partner.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'name': self.name,
                'quantity': self.quantity,
                'price_unit': self.price_unit,
                'tax_ids': [(6, 0, self.tax_ids.ids)],
            })],
        })

        # Copy all receipt attachments to the new invoice
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.expense'),
            ('res_id', '=', self.id),
        ])
        for att in attachments:
            att.copy({
                'res_model': 'account.move',
                'res_id': invoice.id,
                'res_name': invoice.name,
            })

        self.reinvoice_id = invoice
