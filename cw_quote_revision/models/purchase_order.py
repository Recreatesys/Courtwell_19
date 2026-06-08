from odoo import _, api, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model_create_multi
    def create(self, vals_list):
        """Block PO creation when origin resolves to a superseded
        sale.order.

        Rationale: a superseded SO represents a revision that's no
        longer the canonical commercial commitment. Issuing a PO to a
        supplier based on that revision risks the supplier acting on
        outdated specs/pricing and creates ambiguity if a separate
        PO is also issued from the latest revision (both inherit the
        same PO- reference via the base ref chain).

        The check covers comma-separated origins (Odoo concatenates
        when a PO links to multiple SOs) and surfaces the latest
        revision in the error so the merchandiser knows where to go.
        """
        Sale = self.env['sale.order']
        for vals in vals_list:
            origin = (vals.get('origin') or '').strip()
            if not origin:
                continue
            # Origin can be a comma-separated list when Odoo merges PO
            # sources. Split, trim, and check each candidate.
            names = [n.strip() for n in origin.split(',') if n.strip()]
            for name in names:
                so = Sale.search([('name', '=', name)], limit=1)
                if not so or not so.is_superseded:
                    continue
                latest = (
                    so.revision_root_id.revision_ids
                    .sorted('revision_number', reverse=True)[:1]
                )
                raise UserError(_(
                    "Cannot create a Purchase Order from %(orig)s — that "
                    "quotation has been superseded by a newer revision "
                    "(%(latest)s). Create the PO from the latest revision "
                    "instead so the supplier receives the canonical "
                    "specifications and pricing.",
                    orig=so.display_name,
                    latest=latest.display_name if latest else _('(unknown)'),
                ))
        return super().create(vals_list)
