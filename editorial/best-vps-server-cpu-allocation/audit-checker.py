"""Original quote-field comparison, synthetic records only. Never ranks throughput."""
def compare(left,right):
    fields=['provider','product','region','plan_family','vcpu_count','allocation','generation']
    for row in (left,right):
        if row.get('vcpu_count') is not None and (not isinstance(row['vcpu_count'],int) or isinstance(row['vcpu_count'],bool) or row['vcpu_count']<=0):raise ValueError('Positive integer vCPU count required')
        if row.get('allocation') not in ('shared','dedicated',None):raise ValueError('Explicit allocation or unknown required')
    missing=[f for f in fields if left.get(f) is None or right.get(f) is None]
    differences=[f for f in fields if f not in missing and left[f]!=right[f]]
    return {'missing':missing,'differences':differences,'result':'unknown fields' if missing else 'different quote fields' if differences else 'matching labels, performance untested'}
if __name__=='__main__':
    import json,pathlib
    cases=json.loads(pathlib.Path(__file__).with_name('audit-inputs.json').read_text(encoding='utf-8'))['fixtures']
    for c in cases:assert compare(c['left'],c['right'])==c['expected'],c['id']
    assert compare(cases[0]['right'],cases[0]['left'])['differences']==['allocation']
    for n in [0,-1,True,2.5]:
        bad=dict(cases[0]['left'],vcpu_count=n)
        try:compare(bad,cases[0]['right'])
        except ValueError:pass
        else:raise AssertionError('Invalid CPU count accepted')
    print('Six comparison fixtures, swapped-record test and four malformed CPU counts passed.')
