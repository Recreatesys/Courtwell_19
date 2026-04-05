{
    'name': 'Project Expense Re-invoice',
    'version': '19.0.1.0.0',
    'summary': 'Require receipt on Re-invoice Expenses; auto-create draft invoice on submission',
    'category': 'Project',
    'depends': ['hr_expense', 'account', 'project'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/expense_receipt_wizard_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
