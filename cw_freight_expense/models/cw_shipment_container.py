from odoo import _, api, fields, models


class CwShipmentContainer(models.Model):
    _inherit = 'cw.shipment.container'

    # ------------------------------------------------------------------
    # Per-container commercial linkage
    #
    # The base cw.shipment.container already has customer_id and
    # supplier_id (from cw_shipment), but no link to the specific
    # sale.order. For consolidated shipments where the cw.shipment
    # itself spans multiple suppliers/customers, the SO linkage has to
    # live on the container — that's the only place where the (customer,
    # supplier, deal) tuple is unambiguous.
    # ------------------------------------------------------------------
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        index=True,
        help='The client sale order whose goods are in this container. '
             'Drives the project analytic linkage used to receive the '
             'allocated freight cost.',
    )

    project_id = fields.Many2one(
        'project.project',
        string='Project',
        index=True,
        help='Project that receives this container\'s share of the '
             'freight cost. Auto-defaults from the linked sale order '
             'when derivable; override manually when the standard '
             'sale.order.line -> project linkage isn\'t set up.',
    )

    currency_id = fields.Many2one(
        related='shipment_id.currency_id',
        store=True,
        readonly=True,
    )

    # ------------------------------------------------------------------
    # Dimensions used for allocation
    # ------------------------------------------------------------------
    weight_kg = fields.Float(
        string='Weight (kg)',
        help='Gross weight of this container\'s share of the cargo. '
             'Used only when the shipment\'s Allocation Method = By Weight.',
    )
    volume_cbm = fields.Float(
        string='Volume (CBM)',
        help='Volume in cubic metres. Used only when Allocation Method '
             '= By Volume.',
    )
    order_value = fields.Monetary(
        string='Order Value',
        compute='_compute_order_value',
        store=True,
        currency_field='currency_id',
        help='Container\'s share of the linked sale order value. Defaults '
             'to the full SO total; used when Allocation Method = By Value.',
    )

    # ------------------------------------------------------------------
    # Freight allocation
    # ------------------------------------------------------------------
    allocated_freight_pct = fields.Float(
        string='Allocated %',
        default=0.0,
        help='Percentage of the shipment\'s total freight cost allocated '
             'to this container. Computed by the shipment\'s allocation '
             'method, but can be manually overridden.',
    )
    allocated_freight_amount = fields.Monetary(
        string='Allocated Freight',
        compute='_compute_allocated_freight_amount',
        currency_field='currency_id',
        help='Currency amount of freight cost that will be posted to this '
             'container\'s project analytic account when the shipment is '
             'finalized.',
    )

    # ------------------------------------------------------------------
    # Computes + onchanges
    # ------------------------------------------------------------------
    @api.onchange('sale_order_id')
    def _onchange_sale_order_id_default_project(self):
        """Suggest a project based on the linked sale order. Tries:
          1. sale.order.project_id (computed, may be empty)
          2. sale.order.order_line.project_id (per-line; first non-empty)
        Leaves project_id alone if nothing derivable — user picks manually.
        """
        for container in self:
            if not container.sale_order_id:
                continue
            so = container.sale_order_id
            project = so.project_id
            if not project:
                projects = so.order_line.mapped('project_id')
                project = projects[:1] if projects else False
            if project:
                container.project_id = project

    @api.depends('sale_order_id', 'sale_order_id.amount_total')
    def _compute_order_value(self):
        for container in self:
            container.order_value = (
                container.sale_order_id.amount_total
                if container.sale_order_id else 0.0
            )

    @api.depends('allocated_freight_pct', 'shipment_id.total_freight_cost')
    def _compute_allocated_freight_amount(self):
        for container in self:
            total = container.shipment_id.total_freight_cost or 0.0
            pct = container.allocated_freight_pct or 0.0
            container.allocated_freight_amount = total * pct / 100.0
