from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SourcingClientSequence(models.Model):
    """Cumulative inquiry counter per (client partner, GS1 segment).

    The Sequence component of every client-side Reference ID is read from
    here. The counter never resets — the YY component of the Reference ID
    provides temporal context independently.

    Phase-1 scope: data structure only. Auto-increment hooks (on Opportunity
    Qualification exit) are not configured in this module.
    """

    _name = 'sourcing.client.sequence'
    _description = 'Sourcing — Client × GS1 Segment Sequence Counter'
    _order = 'partner_id, gpc_segment'
    _rec_name = 'display_name'

    partner_id = fields.Many2one(
        'res.partner',
        string='Client',
        required=True,
        ondelete='restrict',
        domain="[('contact_type', '=', 'client')]",
        index=True,
    )
    gpc_segment = fields.Char(
        string='GS1 Segment Code',
        size=2,
        required=True,
        index=True,
        help='2-digit GS1 GPC Segment code.',
    )
    count = fields.Integer(
        string='Cumulative Count',
        default=0,
        help='Number of inquiries to date for this client × segment pair. '
             'Cumulative for the lifetime of the system. Never resets.',
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('partner_segment_uniq',
         'UNIQUE(partner_id, gpc_segment)',
         'There can only be one sequence row per (Client, GS1 Segment) pair.'),
    ]

    @api.depends('partner_id', 'partner_id.client_code', 'gpc_segment', 'count')
    def _compute_display_name(self):
        for rec in self:
            code = rec.partner_id.client_code or '??'
            rec.display_name = (
                f'{code} × {rec.gpc_segment or "??"} → {rec.count}'
            )

    @api.constrains('gpc_segment')
    def _check_segment(self):
        for rec in self:
            if rec.gpc_segment and (
                len(rec.gpc_segment) != 2 or not rec.gpc_segment.isdigit()
            ):
                raise ValidationError(
                    'GS1 Segment code must be exactly 2 digits.'
                )

    @api.constrains('count')
    def _check_count_non_negative(self):
        for rec in self:
            if rec.count < 0:
                raise ValidationError('Cumulative count cannot be negative.')
