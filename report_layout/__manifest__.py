{
    'name': 'Report Layout',
    'version': '19.0.1.0.0',
    'summary': 'Custom report layouts: centred header image, right-aligned company address',
    'category': 'Technical',
    'depends': ['web'],
    'data': [
        'views/res_company_views.xml',
        'views/report_layout.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
