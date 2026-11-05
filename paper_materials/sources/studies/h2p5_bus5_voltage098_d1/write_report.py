from pathlib import Path
import json
import pandas as pd
p=Path(__file__).resolve().parent
rows=json.loads((p/'verified.json').read_text())
audit=pd.read_csv(p/'capacitor_audit.csv')
lines=['# Bus5容量補償下のD1感度確認（2026-11-04）','',
'H=2.5 s、M=5 s、Bus5の容量性サセプタンスB=1 puを保持し、D1だけを変えた。全条件の事故前Bus5電圧は0.996594324 puで、指定された0.98 pu以上を満たす。', '',
'| D1 | 確認時間 [s] | 遠方平均内部位相変化 [回転] | 終盤の遠方平均Δf [Hz] | 判定 |',
'|---:|---:|---:|---:|---|']
labels={'negative_running':'負方向回転継続','recovery':'同期回復','recovery_after_slip':'スリップ後同期回復'}
for r in sorted(rows,key=lambda r:(r['horizon'],r['D1'])):
    remote=[m for m in r['machines'] if m['bus'] in [2,3,7]]
    df=sum(m['tail_df_mean_Hz'] for m in remote)/3
    lines.append(f"| {r['D1']:g} | {r['horizon']:g} | {r['remote_internal_turns']:.9f} | {df:.9g} | {labels.get(r['classification_verified'],r['classification_verified'])} |")
lines += ['',
'D1を正値にしても回転は残る。一方、D1を十分増やすと今回の事故軌道は同期回復する。有限時間の軌道の確認であり、厳密な臨界D1や無限時間の回転を証明するものではない。', '',
'## 固定条件とD1の意味','',
'- ドループ由来D=10、D2=100、ウォッシュアウト極ωD=50 s⁻¹、τp=M/D=0.5 s。4台とも同じD1を設定。',
'- 周波数偏差νを用い、Mν̇=Pset−Pcap−Dν−D1ν−D2(ν−z)、ż=ωD(ν−z)。したがって有効な定常ドループ勾配は1/(10+D1)。D1=10では5%、D1=20では約3.33%。D1の変更は過渡減衰と定常特性の両方に作用する。',
'- Bは事故前・事故中・事故後とも保持し、Qcap=B|V5|²。負荷の定コンダクタンスG=2.2682301152333055 pu、倍率1。',
'- 系統係数k=0.6812730259441179を前回補償ケースから保持。元のk=1.0299に対して線路4–6・5–6のR/Xを比率変更した条件であり、元系統そのものへの一般化はしない。',
'- GFM有効電力指令Bus1/2/3/7=0.5/0.4/0.4/0.4 pu。Bus4へ20 puシャントを1.0～1.15秒投入し、除去時に線路4–5を開放。',
'- 事故後安定平衡点のBus5電圧は0.857083394 pu。0.98 pu条件は事故前に適用。', '',
'## 数値確認','',
'- Julia 1.12.5、Rodas5P、rtol=1e-9、atol=1e-11、dtmax=0.005 s。保存間隔0.02 s（事故後）。各計算の正常終了を検査。',
'- 追加フィルタを含む全モデルで事故前・事故後平衡点の局所安定性を確認。',
f"- 最大代数残差：{max(r['max_algebraic_residual'] for r in rows):.3g}。",
f"- 事故前の保存軌道全点でBus5電圧≥{audit.pre_trace_min_V5.min():.12f} pu。イベント間のウォッシュアウト状態差の最大値：{audit.max_washout_event_jump.max():.3g}。",
'- 既存の機別分類器を用い、終盤の周波数・位相誤差・位相幅と複数時間窓の回転方向を判定。分類詳細はverified.jsonに保存。', '',
'## 保存物','',
'- [1000秒比較図](comparison.png) / [PDF](comparison.pdf)',
'- [判定一覧CSV](verified.csv) / [機別判定JSON](verified.json)',
'- [Bus5電圧・補償量監査](capacitor_audit.csv)',
'- [実行コード](sensitivity.jl)、w*.log、全条件screen.csv、provenance.json',
'- 条件別フォルダに全状態・フィルタ状態、観測CSV、Bus5電圧とQcap、全パラメータ、平衡点を保存。', '']
(p/'README.md').write_text('\n'.join(lines))
print('\n'.join(lines[:24]))
