"""Install/upgrade hooks for sourcing_reference.

The pre-init hook adopts pre-existing ``crm.stage`` records into this module's
xml_id namespace so the bundled data file UPDATEs them instead of creating
duplicates. The post-init hook merges any leftover unowned stages by name.
"""
import logging

_logger = logging.getLogger(__name__)


# Map: existing stage name (case-insensitive) -> our xml_id (without module prefix)
# 'Archived' is intentionally renamed to 'On Hold' to match the spec.
NAME_TO_XMLID = {
    'incoming inquiry': 'crm_stage_incoming_inquiry',
    'sourcing': 'crm_stage_sourcing',
    'quotation': 'crm_stage_quotation',
    'quotation sent': 'crm_stage_quotation',
    'proforma invoice': 'crm_stage_proforma_invoice',
    'qc': 'crm_stage_qc',
    'enroute': 'crm_stage_enroute',
    'en route': 'crm_stage_enroute',
    'upsell/reorder': 'crm_stage_upsell_reorder',
    'upsell': 'crm_stage_upsell_reorder',
    'reorder': 'crm_stage_upsell_reorder',
    'lost': 'crm_stage_lost',
    'archived': 'crm_stage_on_hold',
    'on hold': 'crm_stage_on_hold',
}


def _stage_name_text(stage):
    """Return a plain-string lowercase rep of a crm.stage name.

    Odoo translatable Char fields return dicts in some contexts; coerce.
    """
    raw = stage.name
    if isinstance(raw, dict):
        raw = raw.get('en_US') or next(iter(raw.values()), '')
    return (raw or '').strip().lower()


def pre_init_hook(env):
    """Adopt existing crm.stage records into this module's xml_id namespace.

    Runs BEFORE the data file is loaded, so the data file will resolve
    each xml_id to an existing record (UPDATE) rather than creating a duplicate.
    """
    Stage = env['crm.stage']
    IrModelData = env['ir.model.data']

    seen_xmlids = set()
    for stage in Stage.search([]):
        key = _stage_name_text(stage)
        xml_name = NAME_TO_XMLID.get(key)
        if not xml_name or xml_name in seen_xmlids:
            continue
        existing = IrModelData.search([
            ('module', '=', 'sourcing_reference'),
            ('name', '=', xml_name),
        ], limit=1)
        if existing:
            seen_xmlids.add(xml_name)
            continue
        IrModelData.create({
            'module': 'sourcing_reference',
            'name': xml_name,
            'model': 'crm.stage',
            'res_id': stage.id,
            'noupdate': False,
        })
        seen_xmlids.add(xml_name)
        _logger.info(
            "sourcing_reference pre_init_hook: adopted crm.stage id=%s name=%r as %s",
            stage.id, key, xml_name,
        )


def post_init_hook(env):
    """Cleanup pass: merge any unowned duplicate stages by name into ours.

    Re-points crm.lead.stage_id from old → new, then deletes orphan stages.
    """
    Stage = env['crm.stage']
    Lead = env['crm.lead']

    # Build name → our_stage map
    our_xmlids = {
        'crm_stage_incoming_inquiry',
        'crm_stage_sourcing',
        'crm_stage_quotation',
        'crm_stage_proforma_invoice',
        'crm_stage_qc',
        'crm_stage_enroute',
        'crm_stage_upsell_reorder',
        'crm_stage_lost',
        'crm_stage_on_hold',
    }
    our_stages_by_xmlid = {}
    for x in our_xmlids:
        ref = env.ref(f'sourcing_reference.{x}', raise_if_not_found=False)
        if ref:
            our_stages_by_xmlid[x] = ref

    if not our_stages_by_xmlid:
        return

    our_stage_ids = {s.id for s in our_stages_by_xmlid.values()}

    for stage in Stage.search([]):
        if stage.id in our_stage_ids:
            continue
        key = _stage_name_text(stage)
        target_xmlid = NAME_TO_XMLID.get(key)
        if not target_xmlid:
            continue
        target = our_stages_by_xmlid.get(target_xmlid)
        if not target:
            continue
        leads = Lead.with_context(skip_sourcing_validation=True).search(
            [('stage_id', '=', stage.id)]
        )
        if leads:
            leads.with_context(skip_sourcing_validation=True).write(
                {'stage_id': target.id}
            )
            _logger.info(
                "sourcing_reference post_init_hook: re-pointed %d leads "
                "from stage id=%s (%r) -> id=%s (%s)",
                len(leads), stage.id, key, target.id, target_xmlid,
            )
        try:
            stage.unlink()
            _logger.info("sourcing_reference post_init_hook: removed orphan stage id=%s name=%r", stage.id, key)
        except Exception as e:
            _logger.warning(
                "sourcing_reference post_init_hook: could not remove stage %s (%r): %s",
                stage.id, key, e,
            )
