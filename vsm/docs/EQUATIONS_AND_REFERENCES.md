# VSMの式・状態写像・出典

## 1. 実コードの定義

確認対象は同梱の`provenance/PowerDynamics_used/src/Library/Renewables/ComposableInverter.jl`の`DroopOuter`と、`provenance/source_snapshot/compornent.jl`の`DroopInverter_addlimit`です。

コンデンサ電圧と系統側フィルタ電流から

\[
P=V_{C,r}i_{g,r}+V_{C,i}i_{g,i},\qquad
Q=V_{C,i}i_{g,r}-V_{C,r}i_{g,i}
\]

を測ります。P正はインバータから系統への供給です。端子電力U conj(Ig)とは区別します。元の制御は

\[
\tau_p\dot P_f=P-P_f,\quad
\omega=\omega_0+K_p(P_{set}-P_f),\quad
\dot\delta=\omega-\omega_0.
\]

ω0=2π60 rad/sです。ソースの説明メタデータに「pu」とある箇所がありますが、角度式と値からωの実単位はrad/sです。KpはP–f Droopゲインで、内側PIの比例ゲインではありません。角度はBus6の固定60 Hzスラックに対する同期回転座標系で表します。

## 2. 今回の導出

pu周波数偏差を

\[
\nu=\frac{\omega-\omega_0}{\omega_0}
=\frac{K_p}{\omega_0}(P_{set}-P_f)
\]

と置きます。Pset、Kp、ω0を一定とすると

\[
\dot\nu=-\frac{K_p}{\omega_0\tau_p}(P-P_f),\qquad
P_f=P_{set}-\frac{\omega_0}{K_p}\nu.
\]

したがって

\[
M\dot\nu=P_{set}-P-D\nu,\qquad
\dot\delta=\omega_0\nu,
\]

\[
D=\frac{\omega_0}{K_p},\qquad
M=\frac{\tau_p\omega_0}{K_p},\qquad
\frac{M}{D}=\tau_p.
\]

puゲインをKp,pu=Kp/ω0と書けば、D=1/Kp,pu、M=τp/Kp,puです。同じ電力ベースの標準pu動揺方程式M=2Hとの対応からH=M/2とします。**τpそのものはHではありません。**

| Bus | τp [s] | Kp [rad/s/pu] | Kp,pu | M [s] | D | H [s] | M/D [s] |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 1.087 | 7.539822369 | 0.02 | 54.35 | 50 | 27.175 | 1.087 |
| 2 | 1.087 | 7.539822369 | 0.02 | 54.35 | 50 | 27.175 | 1.087 |
| 3 | 1.087 | 7.539822369 | 0.02 | 54.35 | 50 | 27.175 | 1.087 |
| 7 | 1.087 | 7.539822369 | 0.02 | 54.35 | 50 | 27.175 | 1.087 |
| 1 | 1.000 | 7.539822369 | 0.02 | 50 | 50 | 25 | 1.000 |
| 2 | 1.000 | 7.539822369 | 0.02 | 50 | 50 | 25 | 1.000 |
| 3 | 1.000 | 7.539822369 | 0.02 | 50 | 50 | 25 | 1.000 |
| 7 | 1.000 | 7.539822369 | 0.02 | 50 | 50 | 25 | 1.000 |

機器/系統容量ベース比1を仮定した値です。比r=Sdevice/Sbaseが異なるなら機器ベースのM,D,Hは表の値をrで除します。モデルだけでは定格MVAやDC蓄積エネルギーは確定せず、MJへの換算や実機での実現可能性は示していません。

## 3. 実装との対応

`code/vsm.jl`は、コンパイルされた全DAE上の4個のPf座標をνへ置換するカスタム制御です。装置全体を簡略Swingモデルに置換する実装ではありません。

- `to_vsm`: 元のPfからνへ写像。
- `to_droop`: νからPf相当値を再構成し、既存回路・Q・PI・観測APIに渡す。
- `vsm_rhs!`: 既存右辺のPフィルタ4行を捨て、独立に記述した動揺方程式で上書き。角度4行もω0νで上書き。
- 状態位置はVIndexの名前から取得。新しい配列に独立したPf状態は存在しない。

VSMの保存パラメータ配列は既存APIのτp,Kpを保持し、右辺内でM=τpω0/Kp、D=ω0/Kpと変換します。τpというパラメータ名が残ることは、Pフィルタが別に動いていることを意味しません。観測CSVのPf列もVSMでは再構成量です。生状態の意味は`reference_results/state_mapping.csv`を参照してください。

事故でPset,Kp,ω0を変更しないため写像は連続です。微分状態を固定して代数変数だけ整合化します。Psetが時変なら写像微分に指令の時間微分が現れるため、ここで用いた単純な等価式を無条件には使えません。Q制御と制限機構も両方式で同一であることが比較の前提です。

## 4. 一次文献と確認範囲

S. D'Arco and J. A. Suul, “Equivalence of Virtual Synchronous Machines and Frequency-Droops for Converter-Based MicroGrids,” IEEE Transactions on Smart Grid, vol. 5, no. 1, pp. 394–395, 2014. DOI: [10.1109/TSG.2013.2288000](https://doi.org/10.1109/TSG.2013.2288000).

- [IEEE出版ページ](https://ieeexplore.ieee.org/document/6683080/)
- [SINTEFの書誌・概要](https://www.sintef.no/en/publications/publication/0198cc5ca830-234d2b07-123e-4c6a-9adc-8847aec66b01/)
- [著者公開PDF](https://www.researchgate.net/profile/Jon-Suul/publication/260058589_Equivalence_of_Virtual_Synchronous_Machines_and_Frequency-Droops_for_Converter-Based_MicroGrids/links/0c96052f52c68ecacf000000/Equivalence-of-Virtual-Synchronous-Machines-and-Frequency-Droops-for-Converter-Based-MicroGrids.pdf)

2026-10-29の調査で書誌・本文を確認しました。IV節の一定周波数基準・一定有効電力指令における一次フィルタ付きDroopと動揺方程式の等価性が本実装の基礎です。上の式は、その考え方を今回のコードのrad/sとpuベースに合わせて導出したもので、論文から今回の数値を引用したものではありません。

この文献は今回のH=27.175 sの実機設計妥当性や、Q側τq=1.087 sを正当化する根拠にはしていません。論文PDF自体はGitへ再配布しません。
