import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    cw_shipment_ids = fields.One2many(
        'cw.shipment',
        'opportunity_id',
        string='Shipments',
    )
    cw_shipment_count = fields.Integer(
        compute='_compute_cw_shipment_count',
    )

    @api.depends('cw_shipment_ids')
    def _compute_cw_shipment_count(self):
        for lead in self:
            lead.cw_shipment_count = len(lead.cw_shipment_ids)

    def action_view_cw_shipments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Shipments"),
            'res_model': 'cw.shipment',
            'view_mode': 'list,form',
            'domain': [('opportunity_id', '=', self.id)],
            'context': {
                'default_opportunity_id': self.id,
                'default_customer_id': self.partner_id.id if self.partner_id else False,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        proforma_stage = self.env.ref(
            'sourcing_reference.crm_stage_proforma_invoice',
            raise_if_not_found=False,
        )
        if proforma_stage:
            for lead in leads:
                if lead.stage_id.id == proforma_stage.id:
                    lead._cw_ensure_draft_shipment()
        return leads

    def write(self, vals):
        result = super().write(vals)
        if 'stage_id' in vals:
            proforma_stage = self.env.ref(
                'sourcing_reference.crm_stage_proforma_invoice',
                raise_if_not_found=False,
            )
            if proforma_stage:
                for lead in self:
                    if lead.stage_id.id == proforma_stage.id:
                        lead._cw_ensure_draft_shipment()
        return result

    def _cw_ensure_draft_shipment(self):
        self.ensure_one()
        Shipment = self.env['cw.shipment']
        existing = Shipment.search([('opportunity_id', '=', self.id)], limit=1)
        if existing:
            return existing

        group = self.env.ref(
            'cw_shipping_workflow.group_shipping_user',
            raise_if_not_found=False,
        )
        responsible = group.user_ids[:1] if (group and group.user_ids) else self.env.user

        pi_no = self.sourcing_reference or f"DRAFT-OPP-{self.id}"
        candidate = pi_no
        n = 1
        while Shipment.sudo().search_count([('pi_no', '=', candidate)]):
            n += 1
            candidate = f"{pi_no}-{n}"
            if n > 50:
                _logger.warning(
                    "cw_shipping_workflow: could not generate unique pi_no for opp %s after 50 tries",
                    self.id,
                )
                return False

        shipment = Shipment.sudo().create({
            'pi_no': candidate,
            'opportunity_id': self.id,
            'sale_order_id': self._cw_find_primary_sale_order(),
            'customer_id': self.partner_id.id if self.partner_id else False,
            'responsible_user_id': responsible.id,
        })
        if responsible.partner_id:
            shipment.sudo().message_subscribe(partner_ids=responsible.partner_id.ids)

        shipment.sudo().activity_schedule(
            act_type_xmlid='cw_shipping_workflow.mail_activity_type_request_spot_rates',
            summary=_("Request freight forwarder spot rates"),
            note=_(
                "Opportunity %(opp)s has reached Proforma Invoice. Reach out to "
                "freight forwarders for current spot rates and container schedules."
            ) % {'opp': self.display_name},
            user_id=responsible.id,
        )
        _logger.info(
            "cw_shipping_workflow: auto-created draft cw.shipment %s for opp %s (pi_no=%s)",
            shipment.id, self.id, candidate,
        )
        return shipment

    def _cw_find_primary_sale_order(self):
        self.ensure_one()
        so = self.env['sale.order'].sudo().search(
            [('opportunity_id', '=', self.id)],
            order='id desc', limit=1,
        )
        return so.id if so else False
