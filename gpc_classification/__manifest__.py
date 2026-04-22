{
    'name': 'GS1 GPC Classification',
    'version': '19.0.1.0.0',
    'summary': 'GS1 Global Product Classification — Segment and Class reference data',
    'category': 'Technical',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/gpc_class_views.xml',
        'data/gpc_class_data.csv',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
