"""Original limited Azure access-path quote screen; synthetic flags only."""
def screen(row):
    if row.get('provider')!='azure':return 'outside documented provider scope'
    route=row.get('route')
    if route=='direct_public':
        fields=['vm_running','public_ip','rdp_source_allowed']
        if any(row.get(f) is None for f in fields):return 'public route evidence incomplete'
        if any(not isinstance(row[f],bool) for f in fields):raise ValueError('Explicit boolean route flags required')
        if not row['public_ip']:return 'no target public IP for this route'
        if not row['vm_running'] or not row['rdp_source_allowed']:return 'public route prerequisite not recorded'
        return 'public route fields recorded; connection and price untested'
    if route!='bastion':return 'unresolved access route'
    sku=row.get('sku');mode=row.get('mode')
    if sku not in ('Developer','Basic','Standard','Premium'):return 'unresolved Bastion tier'
    if mode not in ('browser','native'):return 'unresolved client method'
    if mode=='native' and sku in ('Developer','Basic'):return 'native client feature mismatch'
    if sku=='Developer':
        if row.get('region_available') is not True:return 'Developer availability unconfirmed'
        return 'free Developer tier scope; other resource costs unknown'
    if row.get('gateway_in_quote') is not True:return 'priced gateway scope missing from quote'
    return 'gateway quote scope recorded; actual total uncomputed'
if __name__=='__main__':
    import json,pathlib
    cases=json.loads(pathlib.Path(__file__).with_name('audit-inputs.json').read_text(encoding='utf-8'))['fixtures']
    for c in cases:assert screen(c['inputs'])==c['expected'],c['id']
    assert screen({'provider':'other'})=='outside documented provider scope'
    try:screen(dict(cases[0]['inputs'],public_ip='yes'))
    except ValueError:pass
    else:raise AssertionError('Text flag accepted as verified evidence')
    print('Eight route/tier/quote fixtures, provider scope and invalid evidence checks passed.')
