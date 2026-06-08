from odoo import fields, models


class CWContactLookup(models.TransientModel):
    _name = 'cw.contact.lookup'
    _description = "Look up a single contact by name (form-only access path)"

    partner_id = fields.Many2one(
        'res.partner',
        string="Contact",
        required=True,
        ondelete='cascade',
        help="Start typing a name. The autocomplete shows up to a handful of matches; "
             "select one and click Open Contact to view its form.",
    )

    def action_open(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.partner_id.display_name,
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }
