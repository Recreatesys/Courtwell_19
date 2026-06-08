import logging
from datetime import timedelta

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class ProjectTask(models.Model):
    _inherit = 'project.task'

    cw_is_qc_inspection = fields.Boolean(
        string='QC Inspection Task',
        tracking=True,
        help="Mark this task as the QC finished-goods inspection. "
             "Combined with QC Inspection Date, drives the shipping "
             "booking deadline.",
    )
    cw_qc_inspection_date = fields.Date(
        string='QC Inspection Date',
        tracking=True,
    )
    cw_shipping_booking_deadline = fields.Date(
        string='Shipping Booking Deadline',
        compute='_compute_cw_shipping_booking_deadline',
        store=True,
        help="Computed deadline for Shipping to book the forwarder: "
             "QC Inspection Date minus 7 days.",
    )

    @api.depends('cw_qc_inspection_date', 'cw_is_qc_inspection')
    def _compute_cw_shipping_booking_deadline(self):
        for task in self:
            if task.cw_is_qc_inspection and task.cw_qc_inspection_date:
                task.cw_shipping_booking_deadline = task.cw_qc_inspection_date - timedelta(days=7)
            else:
                task.cw_shipping_booking_deadline = False

    def write(self, vals):
        result = super().write(vals)
        triggers = {'cw_qc_inspection_date', 'cw_is_qc_inspection'}
        if triggers & set(vals.keys()):
            for task in self:
                if task.cw_is_qc_inspection and task.cw_qc_inspection_date:
                    task._cw_notify_shipping_qc_scheduled()
        return result

    def _cw_notify_shipping_qc_scheduled(self):
        self.ensure_one()
        if not self.project_id:
            return
        Lead = self.env['crm.lead'].sudo()
        opp = Lead.search([('project_id', '=', self.project_id.id)], limit=1)
        if not opp:
            return
        Shipment = self.env['cw.shipment'].sudo()
        shipment = Shipment.search(
            [
                ('opportunity_id', '=', opp.id),
                ('status', 'not in', ('shipped', 'arrived', 'delivered', 'cancelled')),
            ],
            order='id desc', limit=1,
        )
        if not shipment:
            return

        responsible = shipment.responsible_user_id or self.env.user
        shipment.activity_schedule(
            act_type_xmlid='cw_shipping_workflow.mail_activity_type_book_shipping',
            date_deadline=self.cw_shipping_booking_deadline,
            summary=_("Book shipping plan with forwarder before QC"),
            note=_(
                "QC inspection scheduled for %(qc)s on task %(task)s. "
                "Shipping plan must be booked by %(deadline)s "
                "(QC date − 7 days)."
            ) % {
                'qc': self.cw_qc_inspection_date,
                'task': self.display_name,
                'deadline': self.cw_shipping_booking_deadline,
            },
            user_id=responsible.id,
        )
        _logger.info(
            "cw_shipping_workflow: scheduled booking activity on shipment %s "
            "tied to QC task %s",
            shipment.id, self.id,
        )
