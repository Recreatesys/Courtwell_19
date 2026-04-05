from odoo import _, fields, models
from odoo.exceptions import UserError


class ExpenseReceiptWizard(models.TransientModel):
    _name = 'expense.receipt.wizard'
    _description = 'Expense Receipt Upload'

    expense_id = fields.Many2one('hr.expense', required=True, readonly=True)
    attachment = fields.Binary(string='Receipt / 收據', required=True)
    attachment_filename = fields.Char()

    def action_upload_and_submit(self):
        self.ensure_one()
        if not self.attachment:
            raise UserError(_(
                'Please attach a receipt image before submitting.\n'
                '請在提交前上載收據圖片。'
            ))
        self.env['ir.attachment'].create({
            'name': self.attachment_filename or 'receipt',
            'datas': self.attachment,
            'res_model': 'hr.expense',
            'res_id': self.expense_id.id,
        })
        # Invalidate cache so nb_attachment reflects the new file
        self.expense_id.invalidate_recordset(['nb_attachment', 'attachment_ids'])
        self.expense_id.action_submit()
        return {'type': 'ir.actions.act_window_close'}
