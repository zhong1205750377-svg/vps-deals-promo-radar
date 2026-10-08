"""Synthetic documentation checker. No network access or resource modification."""
import json,pathlib
def classify(state,snapshot,volume,ip):
    if state not in ('running','stopped','destroyed'):raise ValueError('Unknown instance state')
    if any(type(x) not in (bool,type(None)) for x in (snapshot,volume,ip)):raise ValueError('Presence must be true, false or unknown')
    known=[];review=[]
    if state!='destroyed':known.append('instance')
    if snapshot is True:known.append('snapshot')
    if volume is True:review.append('block_volume')
    if ip is True:review.append('reserved_ip')
    for name,x in [('snapshot',snapshot),('block_volume',volume),('reserved_ip',ip)]:
        if x is None:review.append(name+'_presence_unknown')
    return {'known_billable_categories':known,'unresolved_categories':review,'within_scope_clear':not known and not review}

if __name__ == "__main__":
    data=json.loads(pathlib.Path(__file__).with_name("audit-inputs.json").read_text())
    for row in data["fixture_inputs_and_results"]:
        actual=classify(row["instance"],row["snapshot"],row["volume"],row["ip"])
        assert actual==row["result"],row["id"]
    print("All saved lifecycle fixtures passed; no real account inspected.")
