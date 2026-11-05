"""Audit the public default, frozen inputs and copied compensated paper packet."""
from pathlib import Path
import csv,hashlib,json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1]
with (ROOT/'data/representative.csv').open() as io:row=next(csv.DictReader(io))
assert float(row['D1'])==0 and float(row['H'])==2.5 and float(row['mp'])==.10
assert float(row['Bcap'])==1 and float(row['horizon'])==1000
ref=ROOT/'data/current_reference';provenance=json.loads((ref/'provenance.json').read_text())
for name,expected in provenance['source_sha256'].items():assert hashlib.sha256((ref/name).read_bytes()).hexdigest()==expected
paper=ROOT/'paper_materials'
figures=pd.read_csv(paper/'report/FIGURE_CATALOG.csv').fillna('')
assert len(figures)==31 and list(figures.id)==[f'F{i:02}' for i in range(1,32)]
for f in figures.to_dict('records'):
 for ext in ['png','pdf','svg']:
  if f[ext]:assert (paper/f[ext]).is_file()
for line in (paper/'SHA256SUMS.txt').read_text().splitlines():
 digest,name=line.split('  ',1);assert hashlib.sha256((paper/name).read_bytes()).hexdigest()==digest,name
assert not any(any(x in str(p.relative_to(paper)) for x in ['controller_energy','droop_reference','01_original']) for p in paper.rglob('*'))
print('PASS: D1=0, H=2.5, mp=0.10, B5=1 default; frozen input hashes; all 31 compensated figures and paper packet hashes')
