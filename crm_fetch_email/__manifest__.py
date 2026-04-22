{
    'name': 'CRM Fetch Email Button',
    'version': '19.0.1.0.0',
    'summary': 'Adds a Fetch Emails button to the CRM lead/opportunity form',
    'category': 'CRM',
    'depends': ['crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
