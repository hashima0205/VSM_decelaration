"""Rebuild the Drive paper packet using only the compensated VSM studies."""
from pathlib import Path
import csv,hashlib,html,json,re,shutil,zipfile,subprocess
from html.parser import HTMLParser
from urllib.parse import unquote
import markdown

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD=ROOT/'reports/vsm_rotation_paper_20261105/VSM_rotation_paper_materials_2026-11-05'
OUT=HERE/OLD.name
OUT.mkdir(exist_ok=True)
old_manifest={r['bundle_relative_path']:r for r in csv.DictReader((OLD/'SOURCE_MANIFEST.csv').open())}
records=[]
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def copy(rel,dest=None):
    dest=dest or rel
    src=OLD/rel;dst=OUT/dest;dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,dst)
    entry=old_manifest[rel].copy();entry['bundle_relative_path']=dest
    assert sha(src)==entry['sha256']==sha(dst)
    records.append(entry)

figs=[]
for f in csv.DictReader((OLD/'report/FIGURE_CATALOG.csv').open()):
    if f['group']!='main' and f['id']!='H04':continue
    if f['id']=='H04':
        f['id']='F31';f['group']='main'
        f['title']='容量補償あり：D1=0の回転と刻み幅照合'
    for ext in ['png','pdf','svg']:
        if f[ext]:
            dest=f[ext].replace('/historical/','/main/')
            copy(f[ext],dest);f[ext]=dest
    figs.append(f)
assert len(figs)==31 and all(f['group']=='main' for f in figs)

allowed_studies={
 'h2p5_bus5_voltage098_search','h2p5_bus5_voltage098_d1','h2p5_bus5_basins',
 'h2p5_short_timeplots','h2p5_r56_comparison','h2p5_power_mechanism',
 'h2p5_hypothesis_interventions','h2p5_hidden_state_diagnosis',
}
allowed_code={'vsm.jl','model.jl','engine12.jl','adaptive_probe_metrics.jl','plot_single_line.py','export_single_line_data.jl','classify.py','requirements.txt'}
for rel in old_manifest:
    parts=Path(rel).parts
    if not parts or parts[0]!='sources':continue
    keep=(len(parts)>=4 and parts[1]=='studies' and parts[2] in allowed_studies)
    keep|=rel.startswith('sources/VSM_decelaration/data/single_line/')
    keep|=rel in ['sources/VSM_decelaration/data/states.csv','sources/VSM_decelaration/docs/SINGLE_LINE.md','sources/VSM_decelaration/figures/single_line/README.md','sources/STUDY_CONDITIONS.md']
    keep|=len(parts)==4 and parts[1:3]==('VSM_decelaration','code') and parts[3] in allowed_code
    keep|=rel in ['sources/VSM_decelaration/provenance/Project.toml','sources/VSM_decelaration/provenance/Manifest.toml']
    if keep:copy(rel)

# Keep the numerical synthesis but remove discussion of the unused old cases.
body=(OLD/'report/REPORT_JA.md').read_text()
body=body.replace('全70図','全31図')
body=body.replace('主比較は現在の容量補償VSM条件で統一し、初期探索とクローン元のDroop図は付録分類とした。','収録対象をBus5の容量性サセプタンスB=1 pu、H=2.5秒のVSM検討に限定した。主比較30図と、同じ補償条件のD1=0探索図F31を含む。補償前の検討とDroop保存図は収録しない。')
body=re.sub(r'### 3\.2 以前の条件と矛盾しない整理\n.*?(?=\n## 4\.)','''### 3.2 補償後のD1=0探索と刻み幅照合

F31は同じB5=1 pu、k=0.6812730259441179、H=2.5秒でD1=0とした探索結果である。事故前V5=0.996594324 puを満たし、1000秒の遠方平均位相変化は約−1691.482778回転だった。最大刻み0.005秒と0.00125秒の照合で回転数差約1.82×10⁻¹⁰を確認した。主比較のD1=10とは減衰係数が異なる補償後の検証として収録する。
''',body,flags=re.S)
body=body.replace('全背景点表、探索H01–H04、旧Droop図R群は補足へ回す。','全背景点表、補償後D1=0探索F31は補足へ回す。')
body=body.replace('モデル移植の基準コミット・状態変換・検証はsources/VSM_decelaration/docs/VSM.md、D1/D2はVSM_DAMPING.mdに記録する。','状態変換とD1/D2の実装はsources/VSM_decelaration/code/vsm.jl、補償後の検証は収録した各studyの監査表を参照する。')
body=re.sub(r'^3\. 以前の実機H・ドループ係数の比較.*\n','',body,flags=re.M)
assert not any(x in body for x in ['H01','H02','H03','H04','R群','H=30秒','H=29–30','過去の補償なし'])
reportdir=OUT/'report';reportdir.mkdir(exist_ok=True)
(reportdir/'REPORT_JA.md').write_text(body)
(HERE/'report_body.md').write_text(body)

css=re.search(r'<style>(.*?)</style>',(OLD/'report/REPORT_JA.html').read_text(),re.S)[1]
selected=['F01','F02','F03','F06','F11','F09','F07','F16','F17','F19','F21','F25','F26','F27','F30']
def figure(f):
    links=' / '.join(f'<a href="../{f[k]}">{k.upper()}</a>' for k in ['png','pdf','svg'] if f[k])
    return f'<section class="figure-page"><div class="tag">Bus5 B=1 pu · {f["id"]}</div><h2>{f["id"]}　{html.escape(f["title"])}</h2><img src="../{f["png"]}" alt="{html.escape(f["title"])}"><p>{html.escape(f["caption"])}</p><p class="small">{links}<br>元ファイル：{html.escape(f["source"])}</p></section>'
def document(title,content):return '<!doctype html><html lang="ja"><meta charset="utf-8"><title>'+title+'</title><style>'+css+'</style><body>'+content+'</body></html>'
(reportdir/'REPORT_JA.html').write_text(document('容量補償後VSM・統合レポート',markdown.markdown(body,extensions=['tables','fenced_code'])+'<h2>主要図版集</h2>'+''.join(figure(next(f for f in figs if f['id']==fid)) for fid in selected)))
catalog='# 容量補償後VSMの図一覧\n\n全31図。すべてBus5 B=1 pu、H=2.5秒の検討。PIエネルギー蓄積の検討は含めない。\n\n'
for f in figs:
    catalog+=f"## {f['id']}　{f['title']}\n\n{f['caption']}\n\n"
    catalog+=' / '.join(f"[{ext.upper()}](../{f[ext]})" for ext in ['png','pdf','svg'] if f[ext])+f"\n\n出典：`{f['source']}`\n\n"
(reportdir/'FIGURE_CATALOG.md').write_text(catalog)
(reportdir/'FIGURE_CATALOG.html').write_text(document('容量補償後VSM・全31図','<h1>容量補償後VSMの全31図</h1><p>すべてBus5 B=1 pu、H=2.5秒。F31は同じ補償条件でのD1=0探索。PIエネルギー蓄積の検討は含めない。</p>'+''.join(figure(f) for f in figs)))
with (reportdir/'FIGURE_CATALOG.csv').open('w',newline='') as io:
    wr=csv.DictWriter(io,fieldnames=['id','title','group','caption','source','png','pdf','svg']);wr.writeheader();wr.writerows(figs)

readme='''# 容量補償後のVSM回転現象：論文執筆用資料

2026-11-05更新。収録対象は**Bus5に容量性サセプタンスB=1 puを加え、事故前電圧0.996594324 pu（指定の0.98 pu以上）を確保したH=2.5秒のVSM検討のみ**。

- report/REPORT_JA.pdf：条件、結果の解釈、反例、論文構成案、主要15図の統合レポート。
- report/FIGURE_CATALOG.pdf：補償後の全31図と個別説明。
- figures/main/：既存の主比較30図と、同じ補償条件のD1=0探索図F31。原PNG/PDF/SVGを保存。
- sources/：補償後の各studyの元レポート・CSV・監査JSON、状態対応・ソースコード。
- SOURCE_MANIFEST.csv / SHA256SUMS.txt：コピー元と原本ハッシュ、収録ファイルのハッシュ。

補償前の検討、Droop参考図、混在していた古い係数比較、今回省くPIエネルギー蓄積の検討は収録していない。新しい時間積分は行っていない。

主条件はH=2.5 s、M=5 s、D=10、D2=100、ωD=50 s⁻¹、k=0.6812730259441179、B5=1 pu。D1=10の回転、D1=20の回復、D1=10で事故除去時にR56を25%低減した回復例を区別する。0.98 pu条件は事故前に適用する。

一括ZIPを展開してindex.htmlを開くと、図・表へ移動できる。元レポートの相対リンクは作成当時の作業ツリーに対するものなので、図への入口にはreport/FIGURE_CATALOG.html / CSVを使う。

大容量binやソルバチェックポイント、元論文PDFは含めない。収録コードは出典・再作図用の参照であり、完全な再実行環境ではない。有限1000秒の回転確認は永久回転の証明と区別する。
'''
(OUT/'README.md').write_text(readme)
(OUT/'index.html').write_text(document('容量補償後VSM・論文資料',markdown.markdown(readme)+'<ul><li><a href="report/REPORT_JA.pdf">統合レポートPDF</a></li><li><a href="report/REPORT_JA.html">統合レポートHTML</a></li><li><a href="report/FIGURE_CATALOG.pdf">全31図の図版集PDF</a></li><li><a href="report/FIGURE_CATALOG.html">全図HTML</a></li></ul>'))

# Reuse the tested renderer with the cleaned directory and scope description.
renderer=(ROOT/'reports/vsm_rotation_paper_20261105/render_pdf.py').read_text()
renderer=renderer.replace('既存70図を分類して収録。','補償後の既存31図を収録。')
renderer=renderer.replace('F01–F30：現在の容量補償VSM検討。H01–H04：以前のVSM条件。R01–R36：クローン元のDroop保存結果。','F01–F30：容量補償後の主比較。F31：同じB5=1 pu、H=2.5秒でD1=0とした探索。補償前の図とDroop保存図は収録していない。')
renderer=renderer.replace('全70図','全31図')
renderer=renderer.replace('    s=escape(s)','    s=escape(s.replace("≥", ">=").replace("≤", "<="))')
(HERE/'render_pdf.py').write_text(renderer)
for name in ['build_compensated.py','render_pdf.py','report_body.md','validate_and_zip.py']:
    src=HERE/name;dest=OUT/'sources/assembly'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    records.append({'source_relative_to_workspace':str(src.relative_to(ROOT)),'bundle_relative_path':str(dest.relative_to(OUT)),'bytes':str(src.stat().st_size),'sha256':sha(src)})
with (OUT/'SOURCE_MANIFEST.csv').open('w',newline='') as io:
    wr=csv.DictWriter(io,fieldnames=['source_relative_to_workspace','bundle_relative_path','bytes','sha256']);wr.writeheader();wr.writerows(sorted(records,key=lambda x:x['bundle_relative_path']))
meta={'updated':'2026-11-05','scope':'Only capacitor-compensated VSM studies: B5=1 pu, H=2.5 s, prefault V5>=0.98 pu','figures':31,'main_comparison_figures':30,'compensated_D1_zero_search_figures':1,'new_simulations':False,'source_files':len(records),'selected_report_figures':selected}
(OUT/'bundle_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':print(json.dumps(meta,ensure_ascii=False,indent=2))
