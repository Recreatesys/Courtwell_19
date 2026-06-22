from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    cw_knowledge_note = fields.Html(
        string='Knowledge Capture',
        sanitize=True,
        help="Findings to roll up into the project's Knowledge Base article: confirmed specs, "
             "client/supplier clarifications, sourcing learnings, defects to watch, pricing "
             "rationale. Kept separate from the Description, which holds the SOP instructions.",
    )
