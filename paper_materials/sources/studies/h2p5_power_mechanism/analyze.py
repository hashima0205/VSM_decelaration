from pathlib import Path
import json
import numpy as np,pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
frames={n:pd.read_csv(P/f'budget_D1_{n}.csv') for n in [10,20]}
rows=[]
for n,d in frames.items():
 assert d.balance_error_pu.abs().max()<1e-8
 d['total_load_and_line_loss_pu']=d.load_P_pu+d.line_loss_P_pu
 d['remote_required_terminal_P_pu']=d.load_P_pu+d.remote_internal_loss_P_pu+d.P5_to_6_pu+d.P5_to_4_pu
 # Remote subnetwork has only the 5-6 tie after the 4-5 opening.
 assert np.max(abs(d.remote_required_terminal_P_pu-d.remote_Pterminal_pu))<1e-8
 for label,a in [('prefault',d[d.stage=='pre']),('post_5s',d[(d.stage=='post')&np.isclose(d.t_post_s,5)]),('tail_950_1000s',d[(d.stage=='post')&(d.t_post_s>=950)])]:
  if len(a)==1:values=a.select_dtypes('number').iloc[0].to_dict()
  else:
   t=a.t_absolute_s.to_numpy();values={c:float(np.trapezoid(a[c],t)/(t[-1]-t[0])) for c in a.select_dtypes('number').columns}
  rows.append(dict(D1=n,window=label,**values))
summary=pd.DataFrame(rows);summary.to_csv(P/'summary.csv',index=False)
fig,axes=plt.subplots(4,2,figsize=(11,10.5),sharex=True)
for column,(n,d) in enumerate(frames.items()):
 post=d[(d.stage=='post')&(d.t_post_s<=10)];t=post.t_post_s
 phase5=np.unwrap(d.theta5_terminal_slack_rad.to_numpy());d['theta5_unwrapped_rad']=phase5
 phase=post.index
 axes[0,column].plot(t,post.theta_remote_slack_rad,label='Remote mean internal phase',lw=1)
 axes[0,column].plot(t,d.loc[phase,'theta5_unwrapped_rad'],label='Bus5 terminal phase',lw=1,ls='--')
 axes[1,column].plot(t,post.remote_Pcap_pu,label='Remote 3: Pcap sum',lw=1)
 axes[1,column].axhline(1.2,color='black',ls=':',label='Pset sum = 1.2 pu')
 axes[2,column].plot(t,post.line_loss_P_pu,label='All line losses',lw=1)
 axes[2,column].plot(t,post.tie56_loss_P_pu,label='Line 5-6 loss',ls='--',lw=1)
 axes[2,column].plot(t,post.load_P_pu,label='Bus5 load',lw=1)
 axes[3,column].plot(t,post.slack_P_pu,label='Net slack injection',lw=1)
 axes[3,column].plot(t,post.P6_to_5_pu,label='Sending power 6 to 5',ls='--',lw=1)
 axes[3,column].axhline(0,color='gray',lw=.7)
 axes[0,column].set_title(f'D1 = {n}')
 for ax in axes[:,column]:ax.grid(alpha=.25);ax.legend(fontsize=7,loc='best')
 axes[3,column].set_xlabel('Time after fault clearance [s]')
for ax,label in zip(axes[:,0],['Phase relative to slack Bus6 [rad]','Remote Pcap / Pset [pu]','Load and dissipated power [pu]','Slack-side active power [pu]']):ax.set_ylabel(label)
fig.suptitle('Power balance and negative-running mechanism: H=2.5 s, B5=1 pu');fig.tight_layout()
for ext in ['png','pdf']:fig.savefig(P/f'power_mechanism.{ext}',dpi=190)
plt.close(fig)
text='''# 位相差・線路損失・遠方3機の出力と負方向回転

2026-11-04。ユーザーの「事故→slackとの位相差拡大→線路損失増加→遠方3機が指令値を超えて出力→負方向回転」という見解を保存済み全状態から検討した。

## 検証した内容

- 元の全66状態とD2フィルタ状態を使用。線路のR/Xと開閉状態はモデルから抽出済みの単線結線図用データから取得。事故中は事故前の線路構成にBus4の20 puシャントを投入。
- 全保存時刻でGFM端子注入+slack注入=Bus5負荷+事故負荷+全線路損失を確認。
- 事故後は線路4–5が開き、遠方群（Bus2,3,5,7,8）がslack側に接続する経路は線路5–6だけ。その部分系統でも毎時刻の電力収支を確認。
- 図のPcapはスイング方程式で使われるVC・Igからの有効電力。Pterminalは母線端子電力で、GFMフィルタの損失・蓄積のため一致しない。

## 電力の比較

数値はpu。終盤は事故除去950～1000秒の時間加重平均で、厳密な一周期平均ではない。回転時は電力が周期的に変動する。

| 条件 | 遠方Pcap合計 | 遠方端子P合計 | 全線路損失 | Bus5負荷P | 負荷+線路損失 | slack全体P注入 | P5→6（5側端子） |
|---|---:|---:|---:|---:|---:|---:|---:|
'''
for row in rows:
 if row['D1']==20 and row['window']=='prefault':continue
 label='事故前（共通）' if row['window']=='prefault' else f"D1={row['D1']} / "+('除去5秒後' if row['window']=='post_5s' else '終盤平均')
 text+='| '+label+' | '+' | '.join(f"{row[c]:.6f}" for c in ['remote_Pcap_pu','remote_Pterminal_pu','line_loss_P_pu','load_P_pu','total_load_and_line_loss_pu','slack_P_pu','P5_to_6_pu'])+' |\n'
text+='''
## 読み取り

位相がBus5に対して有限範囲内でも、Bus5自体が遠方群とともにslackに対して回っている。Bus5基準図だけではこの共通の位相進行が除かれる。

線路5–6の損失は `R/(R²+X²) × (|V5|² + |V6|² − 2|V5||V6|cos(θ5−θ6))`。位相差と電圧振幅の両方に依存する。位相を一方向へ巻き続けても損失が無限に単調増加するわけではなく、cosに対応して変動する。

D1=10で全線路損失は事故前より増えるが、定インピーダンス負荷P=G|V5|²が電圧低下によって減るため、系統全体の「負荷+線路損失」は終盤平均で事故前より小さい。一方、slack全体は供給から吸収へ変わり、線路5–6のBus5側も平均で受電から線路への流出へ反転する。ただし同線路のBus6側も平均約0.350 puを線路へ供給しており、両側からの供給約0.491 puが線路で損失になる。Bus5側の正の流出がそのままslackへ到達しているという意味ではない。したがって遠方3機の必要な端子供給は増えている。全系統の必要供給量の増加と、遠方3機の負担増加は区別する。

事故後の部分系統の収支：

`Pterminal,remote = Pload + Ploss,remote_internal + P5→6`

ここでremote_internalは線路3–5、2–3、2–5、2–8、2–7、7–8、5–8の損失。P5→6はBus5から線路5–6へ流出する送端Pで、slack側への実際の到達電力とは区別する。終盤平均ではBus5負荷約1.584 + 内部損失約0.197 + 5側流出約0.141 = 遠方端子供給約1.922 pu。

D1=20も事故前より大きい損失で回復する。従って「損失の大きさだけが脱調を決める」とは言えず、過渡の状態、slackからの受電、P–δ特性、減衰の組合せを見る必要がある。保存結果は見解の一部と整合するが、介入比較によって主因を特定したものではない。

## 事故前からの遠方群の負担変化

事故前にはBus4→5から約0.677 pu、Bus6→5からBus5受端で約0.435 puを受けていた。事故後は前者が開放で失われ、後者もBus5から線路への流出約0.141 puへ反転する。終盤の遠方端子P増分約0.727 puは、4–5経由の受電喪失+0.677、5–6側の負担変化+0.576、遠方内部線路損失増加+0.143、Bus5負荷減少−0.669の和として説明できる。これは同時刻の電力収支の分解であり、独立した介入による因果の分解ではない。

## スイング方程式との対応

`M νdot = Pset − Pcap − Ddroop ν − D1 ν − D2(ν−z)`、`zdot=ωD(ν−z)`、`δdot=ω0 ν`。

Pcap>Psetは負方向の加速度へ作用する。一方、ν<0のときのドループ・D1項は正方向へ作用して減速を抑える。平均してνdotと洗い流し項が小さい持続回転では、`Pcap−Pset ≈ −(Ddroop+D1)ν`。D1=10、Ddroop=10、遠方平均Δf≈−0.7385 Hzなら3機の超過出力は約0.7385 puで、観測の約0.7398 puと整合する（有限窓・周期振動による差を含む）。

「出力が増えたから制御が回転を命令する」という意味ではない。電気側の出力が指令入力を上回ることがスイング方程式に負の加速成分を与え、負周波数偏差に対する制御項との釣合いで、同期しない回転状態が維持されるという説明がモデルに沿う。定常偏差中の超過出力と負周波数は同じ釣合いの両側であり、両者の相関だけで発端の因果を確定しない。

## 保存物

- [比較図](power_mechanism.png) / [PDF](power_mechanism.pdf)
- [窓別集計](summary.csv)
- budget_D1_10.csv / budget_D1_20.csv：全保存時刻の電力収支とスイング方程式の各項。
- export_budget.jl / analyze.py：抽出と作図・集計。新しい積分は実施していない。
'''
(P/'README.md').write_text(text)
print(summary[['D1','window','remote_Pcap_pu','line_loss_P_pu','load_P_pu','slack_P_pu','P5_to_6_pu']].to_string(index=False))
print('max_balance_error',max(d.balance_error_pu.abs().max() for d in frames.values()))
