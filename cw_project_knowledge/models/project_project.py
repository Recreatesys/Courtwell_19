import logging

from markupsafe import Markup

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# Name of the shared workspace article that parents every per-project article.
ROOT_ARTICLE_NAME = "Project Knowledge Base"
_EMPTY_HTML = ('', '<p><br></p>', '<p></p>')


class ProjectProject(models.Model):
    _inherit = 'project.project'

    knowledge_article_id = fields.Many2one(
        'knowledge.article',
        string='Knowledge Article',
        copy=False,
        help="The Knowledge article that aggregates this project's captured task notes.",
    )

    # ------------------------------------------------------------------
    # Article provisioning
    # ------------------------------------------------------------------
    @api.model
    def _get_knowledge_root(self):
        """Find-or-create the shared 'Project Knowledge Base' workspace article."""
        Article = self.env['knowledge.article'].sudo()
        root = Article.search(
            [('name', '=', ROOT_ARTICLE_NAME), ('parent_id', '=', False)], limit=1)
        if not root:
            root = Article.create({
                'name': ROOT_ARTICLE_NAME,
                'internal_permission': 'write',
                'icon': '📚',
                'body': Markup('<p>Auto-generated. One child article per project — '
                               'notes roll up from each project\'s tasks.</p>'),
            })
        return root

    def _ensure_knowledge_article(self):
        """Create the per-project article if it does not exist yet. Never raises."""
        Article = self.env['knowledge.article'].sudo()
        for project in self:
            if project.knowledge_article_id:
                continue
            try:
                article = Article.create({
                    'name': project.display_name or _("Project"),
                    'parent_id': project._get_knowledge_root().id,
                    'icon': '🗂️',
                })
                project.knowledge_article_id = article.id
            except Exception as err:  # pragma: no cover - defensive on a live DB
                _logger.warning(
                    "cw_project_knowledge: could not create article for %s: %s",
                    project.display_name, err)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        projects = super().create(vals_list)
        # Skip templates and explicit opt-outs (e.g. data imports).
        if not self.env.context.get('cw_skip_knowledge'):
            targets = projects.filtered(lambda p: not p.is_template)
            targets._ensure_knowledge_article()
        return projects

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------
    def action_sync_knowledge(self):
        """Rebuild each project's Knowledge article from its tasks' Knowledge Capture notes."""
        self._ensure_knowledge_article()
        for project in self:
            if project.knowledge_article_id:
                project.knowledge_article_id.sudo().body = project._render_knowledge_body()
        return True

    def action_open_knowledge_article(self):
        self.ensure_one()
        self._ensure_knowledge_article()
        article = self.knowledge_article_id
        if not article:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': _("Knowledge Article"),
            'res_model': 'knowledge.article',
            'res_id': article.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _render_knowledge_body(self):
        """Build the article HTML: tasks with a Knowledge Capture note, grouped by stage."""
        self.ensure_one()
        tasks = self.task_ids.sorted(
            key=lambda t: (t.stage_id.sequence or 0, t.sequence or 0, t.id))
        parts = [Markup('<h1>%s — Knowledge Capture</h1>') % (self.display_name or '')]
        parts.append(Markup(
            '<p><em>Auto-synced from project tasks. Add findings in each task\'s '
            '"Knowledge Capture" tab, then click "Sync to Knowledge Base".</em></p>'))
        current_stage = None
        wrote_any = False
        for task in tasks:
            note = (task.cw_knowledge_note or '').strip()
            if note in _EMPTY_HTML:
                continue
            stage_name = task.stage_id.name or _("Unsorted")
            if stage_name != current_stage:
                parts.append(Markup('<h2>%s</h2>') % stage_name)
                current_stage = stage_name
            parts.append(Markup('<h3>%s</h3>') % (task.name or _("Untitled task")))
            # note is already sanitized HTML from the Html field; wrap as Markup.
            parts.append(Markup(note))
            wrote_any = True
        if not wrote_any:
            parts.append(Markup(
                '<p>No knowledge notes captured yet. Fill the "Knowledge Capture" '
                'tab on this project\'s tasks, then sync again.</p>'))
        return Markup('').join(parts)
