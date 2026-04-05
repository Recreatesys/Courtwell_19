{
    'name': 'CRM Project Assignment',
    'version': '19.0.1.0.0',
    'summary': 'Assign or create a project directly from a CRM opportunity',
    'category': 'CRM',
    'depends': ['crm', 'project', 'sale_crm'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/crm_project_wizard_views.xml',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
