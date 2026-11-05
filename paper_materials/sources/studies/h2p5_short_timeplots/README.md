# メカニズム確認用の短時間応答

横軸は事故前の初期化時刻を0秒とする時間。事故投入1.00秒、事故除去と線路4–5開放1.15秒。通常図は0～11.15秒（事故除去後10秒）、拡大図は0.9～1.7秒。

| 対象 | PNG | PDF |
|---|---|---|
| GFM 4機の電圧・電流・有効電力・無効電力・位相 | [PNG](gfm_responses.png) | [PDF](gfm_responses.pdf) |
| 上記の事故投入・除去付近の拡大 | [PNG](gfm_fault_zoom.png) | [PDF](gfm_fault_zoom.pdf) |
| Bus5の負荷・コンデンサとslackへの連系線5–6 | [PNG](bus5_slack_responses.png) | [PDF](bus5_slack_responses.pdf) |
| 補足：Pcapと端子P、内部角、フィルタ側電流 | [PNG](internal_power_and_current.png) | [PDF](internal_power_and_current.pdf) |

各図は左列D1=10（負方向回転）、右列D1=20（同期回復）。H=2.5 s、M=5、ドループ由来D=10、D2=100、ωD=50 s⁻¹、B5=1 pu、k=0.6812730259441179を共通とする。前段で行ったR変更等の仮想介入は使用していない。

## 表示量

- 主図の電圧はGFM端子の複素電圧の大きさ、電流は系統側電流Igの大きさ。
- 主図のP/Qは母線端子での供給電力（正が系統へ注入）。内部のPcapとは異なり、補足図で両者を比較する。
- 主図の位相は端子電圧位相をslack Bus6=0 rad基準でアンラップしたもの。事故前点を0へ平行移動していない。補足図にはVSM内部角δも表示する。
- 電圧・電流はシミュレーションの複素量の大きさ[pu]で、60 Hz搬送波の瞬時波形ではない。
- Bus5/slack図のP6to5・Q6to5はBus6から線路5–6へ注入する送端電力で、線路損失を差し引く前の値。負荷PとコンデンサQを別表示する。負荷電流はG|V5|、コンデンサ電流はB|V5|。
- 事故区間を薄赤、投入を赤点線、除去を灰破線で示す。

元の保存間隔は事故前0.01秒、事故中0.0005秒、事故後0.02秒。平滑化・補間・再積分を行っていない。全保存点から指定時間範囲を切り出した。事故中は固定した区間パラメータで積分しているため、各切替時刻には直前・直後の値の両方を保持している。

## 確認事項とデータ

各機でP+jQ=U×conj(Ig)の一致を1e-9 pu以内で検査。連系線5–6の両端Pの和がR|I|²と一致することを検査。Bus5位相データと各機観測データの時刻・区間を照合している。

入力は ../h2p5_bus5_voltage098_d1 のD1=10/20の保存結果、および ../h2p5_bus5_basins/trajectory_D1_*.csv。gfms_D1_*.csv と network_D1_*.csv に、実際にプロットした時間範囲の数値を出力。definition.jsonに基準と保存刻みを記録。

再作図：`MPLCONFIGDIR=/tmp/vsm_mpl /home/students1/miniconda3/envs/julia/bin/python studies/h2p5_short_timeplots/plot.py`。
