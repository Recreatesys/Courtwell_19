{
    'name': "CW Client Code: Manager Approval Workflow",
    'version': '19.0.1.0.0',
    'category': 'Contacts',
    'summary': "Manager-only assignment of 2-letter client codes, with auto-request "
               "activities, chatter @mentions, and a pending-codes worklist.",
    'description': """
Courtwell — Client Code Approval Workflow
=========================================

Closes the loop left open by cw_contacts_phase1 + sourcing_reference:
the 2-letter ``client_code`` on a Client partner is required to generate
the sourcing Reference ID, but until now there was no in-system way for
a Merchandiser to request a code or for the General Manager to assign
one in a tracked way. Merchandisers hit the stage-exit block and had to
chase the GM out-of-band.

This module adds:

1. A ``Client Code Approver`` group. Members (Howard, Eva) are the only
   users who can write ``res.partner.client_code``. Everyone else sees
   the field as read-only and the server rejects writes from non-members.
   Assignment is manual via Settings -> Users.

2. A ``mail.activity.type`` "Assign Client Code". When a non-approver
   creates a Client partner with no code, the module:
     * schedules this activity on the partner for every approver, AND
     * posts a chatter message @mentioning every approver, AND
     * surfaces the partner in a dedicated "Clients Pending Codes"
       worklist menu visible only to approvers.

3. The same request fires again (idempotently — never duplicates an
   open activity) if a Merchandiser later tries to move the opportunity
   past Incoming Inquiry while the client_code is still missing.

4. The hard stage-exit block for ``client_code`` moves from "exit
   Incoming Inquiry" to "exit Proforma Invoice". Merchandisers can
   advance leads through Inquiry / Quotation / Proforma Invoice without
   the code in hand; only the QC step requires it. The GS1-segment
   requirement still triggers at Inquiry exit (unchanged — needed to
   pick a segment before quoting).

5. The sourcing Reference ID generator retries on every post-Inquiry
   stage entry instead of only at Quotation. If the code is missing at
   Quotation, the reference is generated the moment the GM assigns the
   code and the lead next moves stage (or via a manual button — future
   enhancement).
""",
    'author': 'Courtwell Internal',
    'website': 'https://courtwell.com.hk',
    'depends': [
        'base',
        'mail',
        'contacts',
        'crm',
        'cw_contacts_phase1',
        'sourcing_reference',
    ],
    'data': [
        'security/cw_client_code_approval_groups.xml',
        'data/mail_activity_type_data.xml',
        'views/res_partner_views.xml',
        'views/menu_action.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
}
