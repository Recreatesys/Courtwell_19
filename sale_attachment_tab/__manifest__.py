{
    'name': 'Sale Order Attachment Tab',
    'version': '19.0.1.0.0',
    'summary': 'Add an Attachment tab with rich-text editor (text, tables, images) printed as appendix',
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
