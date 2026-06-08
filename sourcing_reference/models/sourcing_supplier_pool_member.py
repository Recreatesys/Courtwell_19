from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SourcingSupplierPoolMember(models.Model):
    """One row per supplier × (province, segment) pool.

    Stores the supplier's permanent letter within the pool (A, B, …, Z,
    AA, AB, …) and the per-supplier RFQ count used as the NNN component
    of `RQ-{prov}-{seg}-{letter}-{NNN}`.

    Allocation rule: when a supplier issues their first RFQ in a pool,
    they take the pool's `next_letter_index` (decoded to a letter) and
    the pool advances. The letter is then permanent for that supplier
    in that pool — re-engaging the same supplier reuses their letter
    and only increments `count`.
    """

    _name = 'sourcing.supplier.pool.member'
    _description = 'Sourcing — Supplier Pool Membership'
    _order = 'province_code, gpc_segment, letter'
    _rec_name = 'display_name'

    province_code = fields.Char(
        string='Province / Country Code',
        size=2,
        required=True,
        index=True,
    )
    gpc_segment = fields.Char(
        string='GS1 Segment Code',
        size=2,
        required=True,
        index=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Supplier',
        required=True,
        index=True,
        ondelete='restrict',
    )
    letter = fields.Char(
        string='Pool Letter',
        size=2,
        required=True,
        index=True,
        help='Permanent supplier-letter within this (Province × Segment) pool. '
             'Allocated A, B, …, Z, AA, AB, … in order of first RFQ in the pool.',
    )
    count = fields.Integer(
        string='RFQ Count',
        default=0,
        help='Number of RFQs issued to this supplier in this pool. '
             'Drives the NNN component of the RFQ/PO reference ID.',
    )
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('pool_partner_uniq',
         'UNIQUE(province_code, gpc_segment, partner_id)',
         'A supplier may only have one membership row per (Province, Segment) pool.'),
        ('pool_letter_uniq',
         'UNIQUE(province_code, gpc_segment, letter)',
         'Two suppliers cannot share the same letter within one pool.'),
    ]

    @api.depends('province_code', 'gpc_segment', 'partner_id', 'letter', 'count')
    def _compute_display_name(self):
        for rec in self:
            supplier = rec.partner_id.display_name if rec.partner_id else '—'
            rec.display_name = (
                f'{rec.province_code or "??"}-{rec.gpc_segment or "??"}-'
                f'{rec.letter or "?"} · {supplier} → {rec.count}'
            )

    @api.constrains('letter')
    def _check_letter(self):
        for rec in self:
            if not rec.letter:
                continue
            if len(rec.letter) not in (1, 2) or not rec.letter.isalpha() or not rec.letter.isupper():
                raise ValidationError(
                    'Pool letter must be 1 or 2 uppercase letters (A–Z, AA–ZZ).'
                )

    @api.constrains('count')
    def _check_count_non_negative(self):
        for rec in self:
            if rec.count < 0:
                raise ValidationError('RFQ count cannot be negative.')

    @api.model
    def _index_to_letter(self, idx):
        """0→A, 25→Z, 26→AA, 27→AB, …, 701→ZZ."""
        if idx < 0:
            raise ValueError('Letter index must be non-negative')
        if idx < 26:
            return chr(ord('A') + idx)
        offset = idx - 26
        if offset >= 26 * 26:
            raise ValueError(
                f'Pool letter index {idx} exceeds two-letter capacity (max 701).'
            )
        first = chr(ord('A') + offset // 26)
        second = chr(ord('A') + offset % 26)
        return first + second