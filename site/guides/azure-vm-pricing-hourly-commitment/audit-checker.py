"""Original isolated hourly model. Fictional units, not Azure quotes or bills."""
from decimal import Decimal as D
def hour(commitment, usage, savings_rate, paygo_rate):
    c,u,s,p=map(lambda x:D(str(x)),(commitment,usage,savings_rate,paygo_rate))
    if c<0 or u<0 or s<=0 or p<s:raise ValueError('Nonnegative amounts and paygo >= positive savings rate required')
    covered=min(u,c/s);extra=u-covered;applied=covered*s
    return {'covered_units':str(covered),'excess_units':str(extra),'unused_commitment':str(c-applied),'total_model_cost':str(c+extra*p),'paygo_baseline':str(u*p)}
if __name__=='__main__':
    import json,pathlib
    rows=json.loads(pathlib.Path(__file__).with_name('audit-inputs.json').read_text(encoding='utf-8'))['fixtures']
    results=[hour(**r['inputs']) for r in rows]
    for r,out in zip(rows,results):
        for key,value in r['expected'].items():assert D(out[key])==D(str(value)),r['id']
    assert D(results[0]['total_model_cost'])+D(results[1]['total_model_cost'])==D('6')
    pooled=hour(4,4,1,2);assert D(pooled['total_model_cost'])==D('4')
    assert hour(0,2,1,2)['total_model_cost']=='4'
    for bad in [(-1,1,1,2),(2,-1,1,2),(2,1,0,2),(2,1,2,1)]:
        try:hour(*bad)
        except ValueError:pass
        else:raise AssertionError('Invalid input accepted')
    print('Five hourly fixtures, no-rollover regression, zero commitment and four invalid-input checks passed.')
