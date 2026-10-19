"""Original DigitalOcean Droplet route classifier; synthetic fixtures only."""
def classify(row):
    if row.get('product')!='droplet':return 'outside_scope'
    direction=row.get('direction');route=row.get('route');version=row.get('ip_version');dropped=row.get('provider_firewall_drop')
    if direction not in ('inbound','outbound',None):raise ValueError('Invalid direction')
    if route not in ('public','vpc_private',None):raise ValueError('Invalid route')
    if version not in (4,6,None):raise ValueError('Invalid IP version')
    if dropped not in (True,False,None):raise ValueError('Invalid firewall evidence')
    if direction is None:return 'unresolved_direction'
    if direction=='inbound':return 'inbound_not_counted'
    if dropped is True:return 'provider_dropped_not_counted'
    if version==6 and route=='vpc_private':return 'inconsistent_route_evidence'
    if version==6:return 'counts_team_pool'
    if route=='vpc_private':return 'vpc_private_not_counted'
    if route=='public':return 'counts_team_pool'
    return 'unresolved_route'
if __name__=='__main__':
    import json,pathlib
    rows=json.loads(pathlib.Path(__file__).with_name('audit-inputs.json').read_text(encoding='utf-8'))['fixtures']
    for row in rows:assert classify(row)==row['expected'],row['id']
    assert classify({'product':'droplet','direction':None})=='unresolved_direction'
    assert classify({'product':'spaces','direction':'outbound','route':'public'})=='outside_scope'
    try:classify({'product':'droplet','direction':'sideways'})
    except ValueError:pass
    else:raise AssertionError('Invalid direction accepted')
    print('Seven routing fixtures plus missing direction, product scope and invalid input checks passed.')
