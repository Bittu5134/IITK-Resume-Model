import json
for role in ['sde','quant','consulting','core']:
    with open(f'outputs/golden_{role}.json', encoding='utf-8') as f:
        d = json.load(f)
    s = d['score']
    print(f'=== {role.upper()} === score={s["score"]:.1f}/100  coverage={s["coverage"]:.0%}')
    for c in s['competency_scores']:
        if c['strength'] > 0:
            print(f'  {c["competency"]:<28} str={c["strength"]:.3f}  contrib={c["contribution"]:.1f}')
    if s['penalties']:
        for p in s['penalties']:
            print(f'  PENALTY [{p["code"]}] -{p["points"]}pts')
    print()
