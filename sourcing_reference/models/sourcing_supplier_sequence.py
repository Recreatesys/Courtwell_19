from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SourcingSupplierSequence(models.Model):
    """Pool counter per (province code, GS1 segment).

    Parent row for `sourcing.supplier.pool.member` records.
    `next_letter_index` tracks how many distinct suppliers have entered
    this pool, used to allocate the next supplier-letter (A, B, …, Z, AA…)
    when a brand-new supplier issues their first RFQ in this pool.

    `count` is retained as a pool-wide RFQ tally for reporting; the
    per-supplier operational counter lives on the pool-member row.
    """

    _name = 'sourcing.supplier.sequence'
    _description = 'Sourcing — Province × GS1 Segment Pool Counter'
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
        string='Pool RFQ Count',
        default=0,
        help='Cumulative RFQs issued in this (Province × Segment) pool, '
             'across all suppliers. Reporting metric only — the operational '
             'NNN sequence lives on the pool-member row.',
    )
    next_letter_index = fields.Integer(
        string='Next Letter Index',
        default=0,
        help='Zero-based index of the next supplier-letter to assign in this '
             'pool. 0 → A, 1 → B, …, 25 → Z, 26 → AA, 27 → AB, … '
             'Incremented when a brand-new supplier joins the pool.',
    )
    member_ids = fields.One2many(
        'sourcing.supplier.pool.member',
        compute='_compute_members',
        string='Pool Members',
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('province_segment_uniq',
         'UNIQUE(province_code, gpc_segment)',
         'There can only be one sequence row per (Province, GS1 Segment) pair.'),
    ]

    @api.depends('province_code', 'gpc_segment', 'count', 'next_letter_index')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = (
                f'{rec.province_code or "??"} × '
                f'{rec.gpc_segment or "??"} → {rec.count} RFQs, '
                f'{rec.next_letter_index} suppliers'
            )

    def _compute_members(self):
        Member = self.env['sourcing.supplier.pool.member']
        for rec in self:
            rec.member_ids = Member.search([
                ('province_code', '=', rec.province_code),
                ('gpc_segment', '=', rec.gpc_segment),
            ])

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
