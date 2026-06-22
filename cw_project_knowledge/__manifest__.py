{
    'name': 'CW Project → Knowledge Base',
    'version': '19.0.1.0.0',
    'category': 'Services/Project',
    'summary': "Auto-creates one Knowledge article per project and rolls merchandiser task "
               "notes into it.",
    'description': """
CW Project → Knowledge Base
===========================
Connects the Project app to the Knowledge app so merchandiser learnings become company memory.

* Adds a **Knowledge Capture** Html field on every task (separate from the SOP Description).
* On project creation, auto-creates one **Knowledge article** per project, filed under a shared
  workspace article "Project Knowledge Base".
* A **Sync to Knowledge Base** button on the project rebuilds that article from every task's
  Knowledge Capture note, grouped by stage.

Designed for the CW001 merchandising template. See docs/CW19_merchandiser_project_workflow.md.
""",
    'author': 'Courtwell',
    'depends': ['project', 'knowledge'],
    'data': [
        'views/project_views.xml',
        'views/project_task_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
