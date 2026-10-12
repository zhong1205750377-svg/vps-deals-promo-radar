"""Original limited document-clock screen; synthetic inputs, not a refund decision."""
def screen(row):
    if row.get('product')!='kvm_vps':return 'outside_scope'
    if row.get('upgrade') is True:return 'excluded_upgrade'
    if row.get('upgrade') is not False:return 'unresolved_product'
    if row.get('crypto') is True:return 'excluded_payment'
    if row.get('crypto') is not False:return 'unresolved_payment'
    age=row.get('transaction_age_days')
    if age is None:return 'unresolved_transaction_clock'
    if age<0:raise ValueError('Negative elapsed time')
    if age>30:return 'outside_transaction_window'
    if age==30:return 'transaction_boundary_review'
    history=row.get('prior_refund')
    if history is False:return 'screen_pass_not_approval'
    if history is not True:return 'unresolved_history'
    i=row.get('initiation_age_days');c=row.get('completion_age_days')
    if i is None or c is None:return 'unresolved_prior_clocks'
    if c<0 or i<c:raise ValueError('Inconsistent event chronology')
    legal=i>180;summary=c>=180
    if legal!=summary:return 'document_clock_disagreement_review'
    if not legal:return 'cooldown_not_met_in_both_screens'
    return 'screen_pass_not_approval'
if __name__=='__main__':
    import json,pathlib
    rows=json.loads(pathlib.Path(__file__).with_name('audit-inputs.json').read_text(encoding='utf-8'))['fixtures']
    for row in rows:assert screen(row['inputs'])==row['expected'],row['id']
    bad=dict(rows[2]['inputs'],initiation_age_days=179,completion_age_days=181)
    try:screen(bad)
    except ValueError:pass
    else:raise AssertionError('Reversed chronology accepted')
    assert screen({'product':'web_hosting'})=='outside_scope'
    print('Eight synthetic document-clock fixtures, reversed chronology and product scope checks passed.')
