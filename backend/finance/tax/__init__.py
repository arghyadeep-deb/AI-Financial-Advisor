"""Owned structured synthetic field reconciliation, never document inference."""


def reconcile(inputs, resolutions=()):
    sources = {s.source_id: s for s in inputs.sources}
    if len(sources) != len(inputs.sources):
        raise ValueError('Duplicate source IDs require distinct evidence references.')
    mapping = {'identity': 'identity_ref', 'period': 'financial_year',
               'income': 'salary_paise', 'withholding': 'withholding_paise'}
    chosen = {r.field: r for r in resolutions}
    if len(chosen) != len(resolutions):
        raise ValueError('One resolution per field required.')
    result, evidence, conflicts = {}, {}, []
    for field, attr in mapping.items():
        values = {getattr(s, attr) for s in sources.values()}
        expected = inputs.identity_ref if field == 'identity' else inputs.financial_year if field == 'period' else None
        mismatch = len(values) != 1 or (expected is not None and values != {expected})
        resolution = chosen.get(field)
        if resolution:
            if resolution.source_id not in sources:
                raise ValueError('Resolution must reference a retained case source.')
            source = sources[resolution.source_id]
        else:
            source = next(iter(sources.values()))
        value = getattr(source, attr)
        if (mismatch and not resolution) or (expected is not None and value != expected) or value is None:
            conflicts.append(field)
        # Never bind salary/withholding from a different taxpayer or period merely
        # because the reviewer selected a matching identity from another source.
        if field in {'income', 'withholding'}:
            if source.identity_ref != inputs.identity_ref and 'identity' not in conflicts:
                conflicts.append('identity')
            if source.financial_year != inputs.financial_year and 'period' not in conflicts:
                conflicts.append('period')
        result[attr] = value
        evidence[field] = {'source_id': source.source_id, 'field': attr,
            'value': value, 'resolution': resolution.model_dump(mode='json') if resolution else None}
    return {'status': 'needs_review' if conflicts else 'reconciled',
            'conflicts': conflicts, 'fields': result, 'evidence': evidence}
