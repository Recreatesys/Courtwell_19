{
    'name': 'Sale Order Line Image',
    'version': '19.0.1.0.0',
    'summary': 'Add an Image column to sale order lines, visible in form and printed report',
    'category': 'Sales',
    'depends': ['sale'],
    'data': [
        'views/sale_order_views.xml',
        'report/sale_order_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
