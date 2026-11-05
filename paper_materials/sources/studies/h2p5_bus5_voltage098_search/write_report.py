from pathlib import Path
import json,pandas as pd,numpy as np
p=Path(__file__).resolve().parent;rs=json.loads((p/'verified.json').read_text());aud=pd.read_csv(p/'capacitor_audit.csv')
a=next(r for r in rs if r['case'].endswith('_h1000'));b=next(r for r in rs if r['case'].endswith('_fine'))
assert all(r['classification_verified']=='negative_running' and r['pre_V5']>=.98 and r['pre_max_real']<0 and r['post_max_real']<0 and r['max_algebraic_residual']<1e-8 for r in [a,b])
for r in [a,b]:assert all(m['classification']=='negative_running' for m in r['machines'] if m['bus'] in [2,3,7])
errors=[]
for stage in ['pre','fault','post']:
 x=pd.read_csv(p/a['case']/(stage+'.csv'));y=pd.read_csv(p/b['case']/(stage+'.csv'))
 assert np.array_equal(x.t_absolute_s,y.t_absolute_s)
 for q in ['delta_rad','omega_rad_s','Pcap_pu','U_r_pu','U_i_pu']:
  cs=[f'b{i}_{q}' for i in [1,2,3,7]]
  errors.append(dict(stage=stage,quantity=q,max_abs_difference=float(np.max(abs(x[cs].to_numpy()-y[cs].to_numpy())))))
pd.DataFrame(errors).to_csv(p/'step_refinement.csv',index=False)
r=aud.set_index('case').loc[a['case']]
lines=['# Bus5電圧を補償したH=2.5秒での回転例（2026-11-04）','','## 条件と結果','','ユーザー指定に基づき、Bus5の並列容量性サセプタンスによって事故前電圧0.98 pu以上を確保する条件を必須とした。Bを単に微小な正値へ変更したケースではない。','','| 項目 | 値 |','|---|---:|',f"| B | {a['Bcap']:g} pu |",f"| 事故前Bus5電圧 | {a['pre_V5']:.9f} pu |",f"| 事故後の安定平衡点のBus5電圧 | {r.post_root_V5:.9f} pu |",f"| 事故前の容量性無効電力注入 | {r.pre_Qcap_injection:.9f} pu |",f"| 事故後安定点の容量性無効電力注入 | {r.post_root_Qcap_injection:.9f} pu |",'| H / M | 2.5 s / 5 s |',f"| ドループ由来D / 追加D1 / D2 | {a['Ddroop']:g} / {a['D1']:g} / {a['D2']:g} |",'| ウォッシュアウト極ωD | 50 s⁻¹ |','| τp=M/D | 0.5 s |','| P–fドループ勾配 | 10% |',f"| 系統係数k | {a['grid_k']:.12f} |",'| 負荷の定コンダクタンスG | 2.2682301152333055 pu（倍率1、元と同じ） |',f"| 事故前の実負荷P | {r.pre_load_P:.9f} pu |",f"| 事故後安定点の実負荷P | {r.post_root_load_P:.9f} pu |",'| GFM P指令 Bus1/2/3/7 | 0.5 / 0.4 / 0.4 / 0.4 pu |','| 事故 | Bus4の20 puシャントを1.0～1.15秒に投入し、除去時に線路4–5を開放 |','','**事故前Bus5電圧0.99659 puを確保した条件でも、Bus2・3・7の負方向回転が1000秒間継続した。**','','| 計算 | 遠方平均内部位相変化 [回転] | 判定 |','|---|---:|---|']
for z in sorted(rs,key=lambda x:(x['horizon'],x['case'])):
 lines.append(f"| {int(z['horizon'])}秒 / {'細分化' if z['case'].endswith('_fine') else '基準'} | {z['remote_turns']:.9f} | {z['classification_verified']} |")
lines+=['','## 調整と採否の考え方','','- Bは公称周波数での定サセプタンス。元の定インピーダンス負荷へQ_load_p=−B×vref2を設定し、事故前・事故中・事故後とも保持。容量性注入はQcap=B|V5|²となる。','- 元のk=1.0299のままでは、B追加後の事故後根を安定枝に沿って追跡できなかった。通常Newton法の失敗を「根が存在しない証明」とは扱わない。失敗ログは別study h2p5_bus5_capacitor_searchに保持。','- 事故後の局所安定平衡点との共存を調べるため、既存の補償検討で用いられたB=1、k≈0.681273を候補とした。kの変更は線路4–6・5–6のR/Xだけを元のkとの比で変更する。トポロジーは同じ。','- 負荷のGは変更していないが、定インピーダンス負荷のため電圧上昇とともに実消費Pは変わる。','- 事故前0.98 pu以上を条件にした。事故後も常に0.98 pu以上という条件ではない。','- B=1 puは設定例であり、実機の補償容量の最適化・妥当性を実証するものではない。モデルの電力ベースと実機定格の対応は別途必要。','','## 平衡点と数値検証','',f"- 事故前根の最大固有値実部：{a['pre_max_real']:.9g} s⁻¹。事故後根：{a['post_max_real']:.9g} s⁻¹。追加減衰の状態を含む全モデルで双方が局所安定。",'- Julia 1.12.5、Rodas5P、rtol=1e-9、atol=1e-11。基準dtmax=0.005秒と細分化dtmax=0.00125秒を比較。',f"- 遠方平均回転数の差：{abs(a['remote_turns']-b['remote_turns']):.3e}回転。両計算で遠方3機がnegative_running。",f"- 最大代数残差：{max(a['max_algebraic_residual'],b['max_algebraic_residual']):.3e}以下。",'- 各イベントでD2のフィルタ状態を引き継ぐ。前段終端と次段初期の差は監査表で確認。','- 有限1000秒の確認であり、無限時間の回転の証明ではない。系統条件は追跡された折返しに近いので、広い運転範囲に一般化しない。','','## 各機の終盤指標','']
for m in a['machines']:lines.append(f"- Bus{m['bus']}: {m['classification']}、内部角変化{m['internal_turns']:.9f}回転、終盤平均Δf={m['tail_df_mean_Hz']:.9g} Hz")
lines+=['','## 保存物','','- [比較図PNG](comparison.png)／[PDF](comparison.pdf)','- [Bus5電圧・補償量・状態継続の監査表](capacitor_audit.csv)','- [事故前電圧の採否](voltage_screen.csv)','- [判定JSON](verified.json)／[一覧CSV](verified.csv)','- [刻み幅照合の誤差](step_refinement.csv)','- [探索コード](search.jl)／[実行ログ](run.log)','- 条件別フォルダ：全機観測CSV、Bus5電圧とQcapのCSV、全状態とD2状態のbin、全パラメータ、平衡点。','']
(p/'README.md').write_text('\n'.join(lines)+'\n')
print('Report complete; prefault voltage, roots, rotation classification and numerical residuals verified.')
