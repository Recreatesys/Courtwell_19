{
    'name': 'GS1 GPC Classification',
    'version': '19.0.1.0.0',
    'summary': 'GS1 Global Product Classification — Segment and Class reference data',
    'category': 'Technical',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/gpc.segment.csv',
        'data/gpc.class.csv',
        'views/gpc_segment_views.xml',
        'views/gpc_class_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
