from pathlib import Path
import csv,hashlib,json,re,subprocess,zipfile
from html.parser import HTMLParser
from urllib.parse import unquote
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=HERE/'VSM_rotation_paper_materials_2026-11-05'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
forbidden=['h2p5_rotation_search','h2p5_d1_sensitivity','damping_rotation_1000s','vsm_parameter_comparison','droop_reference','conditional_basins','01_original','02_voltage_adjusted','controller_energy']
for f in OUT.rglob('*'):
 assert not any(x in str(f.relative_to(OUT)) for x in forbidden),f
records=list(csv.DictReader((OUT/'SOURCE_MANIFEST.csv').open()))
for r in records:assert sha(ROOT/r['source_relative_to_workspace'])==sha(OUT/r['bundle_relative_path'])==r['sha256']
figs=list(csv.DictReader((OUT/'report/FIGURE_CATALOG.csv').open()))
assert [f['id'] for f in figs]==[f'F{i:02}' for i in range(1,32)]
assert len(set(f['png'] for f in figs))==31
# The only studies with a capacitor column must contain exactly B=1.
capacitor_tables=0
for f in (OUT/'sources/studies').rglob('*.csv'):
 with f.open() as io:
  reader=csv.DictReader(io);cols=reader.fieldnames or []
  for key in ['Bcap','B','capacitor_B_pu']:
   if key in cols:
    vals=[float(r[key]) for r in reader if r.get(key)]
    assert vals and all(abs(v-1)<1e-12 for v in vals),(f,key)
    capacitor_tables+=1;break
for f in (OUT/'sources/VSM_decelaration/data/single_line').rglob('metadata.csv'):
 row=next(csv.DictReader(f.open()));assert float(row['capacitor_B_pu'])==1 and float(row['H_s'])==2.5
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  for key,value in attrs:
   if key in ['src','href'] and value and not re.match(r'\w+://|#',value):self.links.append(value)
for f in [OUT/'index.html',OUT/'report/REPORT_JA.html',OUT/'report/FIGURE_CATALOG.html']:
 parser=Links();parser.feed(f.read_text())
 for value in parser.links:assert (f.parent/unquote(value)).exists(),(f,value)
pages={}
for name in ['REPORT_JA','FIGURE_CATALOG']:
 file=OUT/'report'/f'{name}.pdf'
 info=subprocess.check_output(['pdfinfo',str(file)],text=True);pages[name]=int(re.search(r'Pages:\s+(\d+)',info)[1])
 text=subprocess.check_output(['pdftotext','-layout',str(file),'-'],text=True)
 assert not any(x in text for x in ['H01','H02','H03','H04','R01','R36','H=30秒','70図'])
 if name=='FIGURE_CATALOG':
  assert pages[name]==32
  for f in figs:assert f['id'] in text
 else:
  for x in ['734.219117','0.031536690','F31','1691.482778']:assert x in text,x
summary={'status':'PASS','scope':'capacitor-compensated VSM only','figures':31,'source_hashes_verified':len(records),'capacitor_column_tables_verified_B_equals_1':capacitor_tables,'snapshot_metadata_B_equals_1_H_equals_2p5':True,'unwanted_study_files_absent':True,'generated_HTML_links_verified':True,'pdf_pages':pages,'new_simulations':False}
(OUT/'validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with (OUT/'SHA256SUMS.txt').open('w') as io:
 for f in sorted(OUT.rglob('*')):
  if f.is_file() and f.name!='SHA256SUMS.txt':io.write(f'{sha(f)}  {f.relative_to(OUT)}\n')
archive=HERE/(OUT.name+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(OUT.rglob('*')):
  if f.is_file():z.write(f,str(Path(OUT.name)/f.relative_to(OUT)))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(json.dumps({**summary,'ZIP_bytes':archive.stat().st_size,'ZIP_sha256':sha(archive)},ensure_ascii=False,indent=2))
