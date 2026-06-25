"""Membership wiring for cw_access_lockdown.

Group memberships are assigned by login (which is stable across DB
transplants) rather than by record xml_id (the CW users are real-DB
records without ir.model.data anchors).

Logins are matched case-insensitively against res.users; missing users
are logged as warnings rather than raising, so partial-environment
installs (dev DBs without all named users) succeed.
"""
import logging

_logger = logging.getLogger(__name__)


SHIPPING_LOGINS = (
    'evawong@courtwell.com.hk',     # Eva
    # Aris (shipping@) and Howard (howardcheng@) are already members of
    # cw_shipping_workflow.group_shipping_user. We only add Eva.
)

SOURCING_LOGINS = (
    'evawong@courtwell.com.hk',     # Eva
    'howardcheng@courtwell.com.hk',  # Howard
)


def _users_by_login(env, logins):
    """Look up res.users by login, log a warning per missing one."""
    found = env['res.users']
    for login in logins:
        u = env['res.users'].search([('login', '=', login)], limit=1)
        if u:
            found |= u
        else:
            _logger.warning(
                "cw_access_lockdown: login %r not found; "
                "skipping group membership for this login.",
                login,
            )
    return found


def post_init_hook(env):
    """Assign the configured users to the gating groups.

    For the shipping group we add (relation tuple 4) rather than replace,
    so Aris and Howard — who are already members from the original
    cw_shipping_workflow install — stay in.

    For the new sourcing-manager group we replace (relation tuple 6) so
    membership reflects the intended set exactly, even on re-install.
    """
    shipping_group = env.ref(
        'cw_shipping_workflow.group_shipping_user',
        raise_if_not_found=False,
    )
    sourcing_group = env.ref(
        'cw_access_lockdown.group_sourcing_manager',
        raise_if_not_found=False,
    )

    if shipping_group:
        users = _users_by_login(env, SHIPPING_LOGINS)
        if users:
            shipping_group.sudo().write({
                'user_ids': [(4, u.id) for u in users],
            })
            _logger.info(
                "cw_access_lockdown: added %s to %s",
                users.mapped('login'), shipping_group.name,
            )
    else:
        _logger.warning(
            "cw_access_lockdown: cw_shipping_workflow.group_shipping_user "
            "not found; menu lockdown will reference an undefined group.",
        )

    if sourcing_group:
        users = _users_by_login(env, SOURCING_LOGINS)
        sourcing_group.sudo().write({
            'user_ids': [(6, 0, users.ids)],
        })
        _logger.info(
            "cw_access_lockdown: set %s members to %s",
            sourcing_group.name, users.mapped('login') or '(none)',
        )
