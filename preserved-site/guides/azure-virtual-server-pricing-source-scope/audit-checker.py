"""Original evidence-scope register. Synthetic metadata, no account connection."""
def classify(row):
    source=row.get('source');currency=row.get('currency')
    if source=='retail_catalog':
        if currency is None:return 'unresolved currency'
        return 'public USD retail rate' if currency=='USD' else 'non-USD reference rate'
    if source!='calculator':return 'unsupported evidence source'
    linked=row.get('agreement_linked')
    if linked not in (True,False,None):raise ValueError('Explicit agreement flag required')
    if linked is False:return 'retail estimate, not invoice'
    if linked is None:return 'unresolved agreement scope'
    match=row.get('account_matches');profile=row.get('profile_selected')
    if match is False:return 'different account scope'
    if match is not True or profile is not True:return 'unresolved account or profile'
    return 'agreement-linked estimate, not invoice'
if __name__=='__main__':
    import json,pathlib
    cases=json.loads(pathlib.Path(__file__).with_name('audit-inputs.json').read_text(encoding='utf-8'))['fixtures']
    for c in cases:assert classify(c['inputs'])==c['expected'],c['id']
    assert classify({'source':'retail_catalog','currency':'USD','agreement_linked':True})=='public USD retail rate'
    assert classify({'source':'retail_catalog','currency':None})=='unresolved currency'
    assert classify({'source':'unknown'})=='unsupported evidence source'
    try:classify({'source':'calculator','agreement_linked':'yes'})
    except ValueError:pass
    else:raise AssertionError('Unverified text flag accepted')
    print('Six synthetic source cases and currency, provenance and invalid-link checks passed.')
