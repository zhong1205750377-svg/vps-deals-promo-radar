"""Original evidence-completeness checker, not a licensing decision or live quote tool."""
def classify(row):
    mode=row.get('mode','unknown')
    if mode not in ('unknown','included','separate','bring_your_own'): raise ValueError('Invalid evidence mode')
    if row.get('scope_matches') is not True: return 'unresolved_scope'
    if mode=='unknown': return 'unresolved_inclusion'
    if mode=='included': return 'included_claim_documented'
    if mode=='separate': return 'separate_charge_documented' if row.get('charge_evidence') is True else 'unresolved_charge'
    if row.get('eligibility_evidence') is not True: return 'unresolved_eligibility'
    return 'customer_license_route_documented'
if __name__=='__main__':
    import json,pathlib
    data=json.loads(pathlib.Path(__file__).with_name('audit-inputs.json').read_text(encoding='utf-8'))
    for row in data['fixtures']: assert classify(row)==row['expected'],row['id']
    assert classify({'mode':'included','scope_matches':None})=='unresolved_scope'
    assert classify({'mode':'separate','scope_matches':True,'charge_evidence':None})=='unresolved_charge'
    try: classify({'mode':'free_forever','scope_matches':True})
    except ValueError: pass
    else: raise AssertionError('Invalid mode accepted')
    print('Six fixtures plus missing scope, missing charge and invalid mode checks passed.')
