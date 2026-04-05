{
    'name': 'Sale Quotation Fields',
    'version': '19.0.1.0.0',
    'summary': 'Attention To field, custom address/incoterm display in print layouts',
    'category': 'Sales',
    'depends': ['sale', 'sale_stock', 'project', 'sale_project'],
    'data': [
        'views/sale_order_views.xml',
        'views/project_project_views.xml',
        'views/project_task_views.xml',
        'report/sale_order_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
