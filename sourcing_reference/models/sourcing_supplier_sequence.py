from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SourcingSupplierSequence(models.Model):
    """Cumulative RFQ counter per (province code, GS1 segment).

    The Sequence component of every supplier-side Reference ID is read from
    here. Cumulative for the lifetime of the system. Never resets.

    Phase-1 scope: data structure only. Auto-increment hooks (on RFQ
    creation) are not configured in this module.
    """

    _name = 'sourcing.supplier.sequence'
    _description = 'Sourcing — Province × GS1 Segment Sequence Counter'
    _order = 'province_code, gpc_segment'
    _rec_name = 'display_name'

    province_code = fields.Char(
        string='Province / Country Code',
        size=2,
        required=True,
        index=True,
        help='Chinese provincial 2-letter abbreviation, OR ISO 3166-1 alpha-2 '
             'country code for non-China suppliers.',
    )
    gpc_segment = fields.Char(
        string='GS1 Segment Code',
        size=2,
        required=True,
        index=True,
    )
    count = fields.Integer(
        string='Cumulative Count',
        default=0,
        help='Number of RFQs issued to date for this province × segment pair. '
             'Cumulative for the lifetime of the system. Never resets.',
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('province_segment_uniq',
         'UNIQUE(province_code, gpc_segment)',
         'There can only be one sequence row per (Province, GS1 Segment) pair.'),
    ]

    @api.depends('province_code', 'gpc_segment', 'count')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f'{rec.province_code or "??"} × '
                f'{rec.gpc_segment or "??"} → {rec.count}'
            )

    @api.constrains('province_code')
    def _check_province_code(self):
        for rec in self:
            if rec.province_code and (
                len(rec.province_code) != 2 or not rec.province_code.isalpha()
            ):
                raise ValidationError(
                    'Province / country code must be exactly 2 letters.'
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
