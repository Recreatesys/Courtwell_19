from odoo import fields, models


class CwPaymentTermTag(models.Model):
    _name = 'cw.payment.term.tag'
    _description = 'Supplier Payment Terms Tag'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Payment term tag name must be unique.'),
    ]


class CwSupplierCertification(models.Model):
    _name = 'cw.supplier.certification'
    _description = 'Supplier Certification Tag'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Certification tag name must be unique.'),
    ]


class CwCoverageMarket(models.Model):
    _name = 'cw.coverage.market'
    _description = 'Service Provider Coverage Market'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Coverage market tag must be unique.'),
    ]


class CwServiceOffered(models.Model):
    _name = 'cw.service.offered'
    _description = 'Service Provider Service Offered'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    color = fields.Integer()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE(name)', 'Service tag must be unique.'),
    ]
