from pathlib import Path
import pandas as pd,numpy as np,json,textwrap,sys,unicodedata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
P=Path(__file__).resolve().parents[1];T=P/'tables';D=P/'data'
c=pd.read_csv(T/'classifications.csv');r=pd.read_csv(D/'roots.csv').drop_duplicates(['case','stage'],keep='last');e=pd.read_csv(T/'waveform_errors.csv');m=pd.read_csv(T/'machine_metrics.csv');sc=pd.read_csv(T/'SCR_verified.csv')
settings={'A_droop_center':(1.087,1.087,1.0299),'B_vsm_center':(1.087,1.087,1.0299),'C_droop_recovery':(1,1,1.0299),'D_vsm_recovery':(1,1,1.0299),'E_shortQ_center':(1.087,.02,1.0299),'F_shortQ_strong':(1.087,.02,.8),'G_shortQ_weak':(1.087,.02,1.031),'H_longQ_strong':(1.087,1.087,1.02),'B_vsm_strict':(1.087,1.087,1.0299),'D_vsm_strict':(1,1,1.0299)}
rows=[]
for x in c.to_dict('records'):
 tp,tq,k=settings[x['case']];pr=r[(r['case']==x['case'])&(r.stage=='post')].iloc[0];pre=r[(r['case']==x['case'])&(r.stage=='pre')].iloc[0]
 x.update(M=tp*50,D=50,H=tp*25,tauq=tq,k=k,SCR_bus2_post=float(sc[(sc.k==k)&(sc.stage=='post')&(sc.bus==2)].SCR.iloc[0]),post_max_real=pr.max_real,pre_max_real=pre.max_real,post_residual=pr.residual)
 rows.append(x)
out=pd.DataFrame(rows);out.to_csv(T/'comparison.csv',index=False)
def tab(df):
 return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(f'{v:.9g}' if isinstance(v,float) else str(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))
mp=pd.read_csv(D/'mapping.csv').drop_duplicates(['bus','tau_p']);mp.to_csv(T/'parameter_mapping.csv',index=False)
q=out[out['case'].isin(['E_shortQ_center','F_shortQ_strong','G_shortQ_weak'])]
short='全3条件で同期回復' if len(q)==3 and (q.classification=='recovery').all() else '比較表の分類を参照'
err=e[e.comparison.isin(['B_vsm_center','D_vsm_recovery'])]
errsummary=[]
for suffix in ['delta_rad','omega_rad_s','Pcap_pu','Qcap_pu','U_r_pu','U_i_pu','Ig_r_pu','Ig_i_pu']:
 a=err[err.variable.str.endswith(suffix)];errsummary.append(dict(variable=suffix,max_error=a.max_abs_error.max()))
es=pd.DataFrame(errsummary);es.to_csv(T/'equivalence_summary.csv',index=False)
refined=e[e.comparison.isin(['B_vsm_strict','D_vsm_strict'])].groupby('comparison',as_index=False).max_abs_error.max()
refined.to_csv(T/'step_refinement_errors.csv',index=False)
report=f'''# VSM置換と負方向回転の検証

開始識別子run_20261029、完了整理2026-10-30。既存研究から独立した出力で、原稿・Overleafは変更していない。

## 主要結論

1. P側の一次フィルタ状態Pfをpu周波数偏差へ置換し、全回路・内側PI・Q制御・仮想インピーダンス・制限を保持したVSMを実装した。52微分状態・14代数変数のままで、Pフィルタと慣性を二重に追加していない。実装はコンパイル済みDAEの状態変換＋外側制御の明示的な右辺置換で、装置全体の簡略Swingモデル化ではない。
2. τp=1.087 sは全機H=27.175 s、D=50、M=54.35 s。τp=1 sはH=25 s。Kpの単位はrad/s/puであり、puゲインは0.02。等価換算は成立するが、その値の実機設計妥当性は今回実証していない。
3. 中心例のDroopとVSMは、300秒で遠方群約−43.677485回転、Bus1回復を再現。τp=τq=1 sの比較例は双方回復。全比較観測量の最大絶対誤差は{err.max_abs_error.max():.4g}（各記録単位）。
4. M=54.35、D=50を固定しτqだけ0.02 sにすると、中心系統で回復した。短いQ時定数のSCR比較は{short}。制御を調整して回転例を作ることはしていない。
5. 元のτq=1.087 sを固定した比較では、k=1.02（SCR2≈0.596691）で回復、k=1.0299（SCR2≈0.591552）で負方向回転に分かれた。短いτq=0.02 sでは今回の3点に同様の分岐は確認できない。全SCR範囲についての結論ではない。
6. 中心VSMの事故後安定根は最大固有値実部≈−0.00183243 s^(-1)。局所安定平衡点と、同じ事故後回路での300秒の負方向位相スリップが共存する。

## 条件と結果

事故は全条件でBus4の20 pu受動シャントを1.0～1.15 s投入し、除去時にline7=4–5を開放。kはline2、3のR/X倍率。SCRは負荷・LCLを除外し、他GFMポートを開放した外部回路のBus2評価値。事故前から同一事故を与えた結果で、過去波形の転用ではない。

{tab(out[['case','H','tauq','k','SCR_bus2_post','classification','remote_turns','post_max_real']])}

回転数は事故除去直後からの遠方3台の内部角変化平均。回復例でも初期の負方向移動はあり、Δf<0や負の総移動量だけでは脱調としない。中心例ではBus1との相対回転も約−43.70回転で、全機共通の周波数偏差とは異なる。負方向回転は60 Hz基準に対する相対位相スリップを指し、絶対周波数や物理的回転方向が負になったことではない。端子角は個別unwrapで別途確認し、中心例約−43.631495回転。

## 等価性とパラメータ

{tab(mp[['bus','tau_p','Kp_rad_s','Kp_pu','M','D','H','M_over_D']])}

ν=Kp(Pset−Pf)/ω0、Pf=Pset−Dν。一定指令・一定周波数基準でMν̇=Pset−Pcap−Dν、δ̇=ω0ν。Pcapはコンデンサ電圧と系統側電流の積で計測する。機器/系統容量比1を仮定する。具体的な定格MVA/DC蓄積量は与えられていない。

各観測量のDroop/VSM最大誤差（全機・両ペア・全保存点、位相/時間合わせなし）：

{tab(es)}

## 数値検証と制限

最大刻み幅細分化の全観測量最大絶対誤差：

{tab(refined)}

代表回転・回復をRodas5P、rtol/atol=1e−9/1e−11、dtmax=0.005 sから、Rodas5P、同じ許容誤差1e−9/1e−11のまま最大刻み0.00125 sへ変更して照合。詳細誤差はwaveform_errors.csv。Rodas4PおよびRodas5Pの100倍厳しい許容誤差試行は長時間化により最終結果前に停止し、完了した精度検証には数えない。許容誤差の厳格化への収束確認は未完了であり、今回完了した確認は刻み幅細分化による分類照合である（provenance/accuracy_trial_note.md）。各条件の全平衡点・固有値・イベント状態連続性はdataとtablesに保存。固定スラックが角度基準なので自明な零固有値はなく、near_zeroも別に検査する。根の候補は既存study60から取り、各パラメータでNewton再計算・残差と全52固有値を確認した。

電流制限は電圧PIの電流指令の円形制限で、実電流の瞬時クランプではない。中心例ではBus1の電流指令制限が事故時に作動し、全期間の系統側電流最大値は約1.98 pu。遠方3機の制限作動は保存点で観測されなかった。制限を取り除いて再現した結果ではない。有限DC電源、DC電圧、エネルギー制約、PWM、保護、熱容量は対象外。Hの大きさに必要な電源能力は検証していない。文献の等価性は今回の換算を支えるが、H=27.175 sやτq=1.087 sの実機採用を保証しない。τq=0.02 sは比較値であり標準値の主張ではない。300秒の結果は無限時間の持続・安定極限周期の証明ではない。

文献：D’Arco and Suul, IEEE TSG 5(1),394–395 (2014), [DOI](https://doi.org/10.1109/TSG.2013.2288000)。本文の一定指令での等価性を確認。詳細な読込ソース・導出・分類基準はMETHODS.md。

## 成果物

- code/vsm.jl, run.jl：外側制御・計算。provenance/implementation.patch：今回の実装差分。
- tables/parameter_mapping.csv, state_mapping.csv：パラメータ・状態写像。
- figures：比較図PDF/PNG。data/*trajectory.csv.gz：全機の波形、P/Q、複素電圧・電流、制限動作。
- data/*root.csv, *eigen.csv：平衡点と全固有値（real,imag）。roots.csv：残差・安定性。
- checkpoints：各区間の実パラメータ、初期・終端全状態と観測CSV。
- provenance：凍結モデル、Manifest、登録版との差分、実行コミットとハッシュ。
- REPRODUCE.md：別の空フォルダでの再現コマンド。既存成果物へ上書きしない。
'''
(P/'REPORT.md').write_text(report)
# Japanese text report PDF, rendered with an installed CJK font (no extra package install).
font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
def wrap_display(s,width=108):
 result=[];line='';n=0
 for ch in s:
  k=2 if unicodedata.east_asian_width(ch) in ['W','F'] else 1
  if n+k>width:result.append(line);line='';n=0
  line+=ch;n+=k
 return result+[line]
lines=[]
in_table=False
for line in report.splitlines():
 if line.startswith('|'):
  if not in_table:lines.append('（表は本PDF末尾に掲載）')
  in_table=True;continue
 in_table=False
 lines.extend(wrap_display(line))
with PdfPages(P/'REPORT.pdf') as pdf:
 for start in range(0,len(lines),46):
  fig=plt.figure(figsize=(8.27,11.69));fig.text(.07,.95,'\n'.join(lines[start:start+46]),fontproperties=font,fontsize=8.5,va='top',linespacing=1.8);pdf.savefig(fig);plt.close(fig)
 for title,df in [('条件比較',out[['case','H','tauq','k','SCR_bus2_post','classification','remote_turns','post_max_real']]),('パラメータ対応',mp[['bus','tau_p','Kp_rad_s','Kp_pu','M','D','H','M_over_D']]),('等価性の最大絶対誤差',es),('刻み幅細分化の最大絶対誤差',refined)]:
  fig,ax=plt.subplots(figsize=(11.69,8.27));ax.axis('off');ax.set_title(title,fontproperties=font)
  df=df.copy()
  for col in df.select_dtypes('number'):df[col]=df[col].map(lambda x:f'{x:.7g}')
  table=ax.table(cellText=df.values,colLabels=df.columns,loc='center',cellLoc='center');table.auto_set_font_size(False);table.set_fontsize(7);table.scale(1,1.7);pdf.savefig(fig,bbox_inches='tight');plt.close(fig)
print('REPORT.md, REPORT.pdf and comparison tables written.')
