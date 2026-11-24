"""Seeded, stratified sample for hand verification: 2 apps per category. Run once; output is committed."""
import csv, json, random
from collections import defaultdict
by_cat = defaultdict(list)
for r in csv.DictReader(open("apps.csv")):
    by_cat[r["category"]].append(r["id"])
rng = random.Random(2026)
ids = sorted((i for c in sorted(by_cat) for i in rng.sample(by_cat[c], 2)), key=int)
json.dump(ids, open("truth/sample_ids.json", "w"))
print(ids)
