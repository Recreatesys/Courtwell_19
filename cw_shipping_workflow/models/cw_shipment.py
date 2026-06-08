import logging
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class CwShipment(models.Model):
    _inherit = 'cw.shipment'

    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        tracking=True,
        index=True,
        domain="[('type', '=', 'opportunity')]",
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        tracking=True,
        index=True,
    )
    responsible_user_id = fields.Many2one(
        'res.users',
        string='Shipping Responsible',
        tracking=True,
        default=lambda self: self._default_responsible_user(),
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        related='opportunity_id.project_id',
        store=True,
        readonly=True,
    )
    freight_quote_ids = fields.One2many(
        'cw.shipment.freight.quote',
        'shipment_id',
        string='Freight Quotes',
        copy=True,
    )
    freight_quote_count = fields.Integer(
        string='# Quotes',
        compute='_compute_freight_quote_count',
        store=True,
    )

    @api.depends('freight_quote_ids')
    def _compute_freight_quote_count(self):
        for ship in self:
            ship.freight_quote_count = len(ship.freight_quote_ids)

    @api.model
    def _default_responsible_user(self):
        group = self.env.ref(
            'cw_shipping_workflow.group_shipping_user',
            raise_if_not_found=False,
        )
        if group and group.user_ids:
            return group.user_ids[:1].id
        return self.env.user.id

    @api.onchange('opportunity_id')
    def _onchange_opportunity_id_set_customer(self):
        for ship in self:
            if ship.opportunity_id and not ship.customer_id and ship.opportunity_id.partner_id:
                ship.customer_id = ship.opportunity_id.partner_id

    @api.model
    def _cron_check_qc_booking_deadlines(self):
        today = fields.Date.context_today(self)
        soon = today + timedelta(days=2)
        Task = self.env['project.task']
        pending_tasks = Task.search([
            ('cw_is_qc_inspection', '=', True),
            ('cw_shipping_booking_deadline', '!=', False),
            ('cw_shipping_booking_deadline', '<=', soon),
            ('cw_shipping_booking_deadline', '>=', today),
        ])
        if not pending_tasks:
            return
        Lead = self.env['crm.lead']
        for task in pending_tasks:
            if not task.project_id:
                continue
            opp = Lead.search([('project_id', '=', task.project_id.id)], limit=1)
            if not opp:
                continue
            shipment = self.search([
                ('opportunity_id', '=', opp.id),
                ('status', 'not in', ('booked', 'shipped', 'arrived', 'delivered', 'cancelled')),
            ], limit=1, order='id desc')
            if not shipment:
                continue
            shipment.message_post(
                body=_(
                    "Shipping booking deadline %(deadline)s is within 2 days "
                    "(QC inspection on %(qc)s, task %(task)s). "
                    "Confirm forwarder booking now."
                ) % {
                    'deadline': task.cw_shipping_booking_deadline,
                    'qc': task.cw_qc_inspection_date,
                    'task': task.display_name,
                }
            )
            _logger.info(
                "cw_shipping_workflow: deadline warning posted on shipment %s for task %s",
                shipment.id, task.id,
            )
