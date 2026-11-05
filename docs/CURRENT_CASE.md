# 現在の基準ケース

2026-11-05更新。標準入力は `data/representative.csv`。D₁=0、H=2.5秒、mₚ=0.10（10%）を全4機に適用する。mₚ=10という無次元値を設定する意味ではない。

| 項目 | 基準値 |
|---|---:|
| H / M=2H | 2.5 s / 5 s |
| mₚ / D=1/mₚ | 0.10 / 10 |
| D₁ / D₂ / ωD | 0 / 100 / 50 s⁻¹ |
| VSM換算用τp=M/D | 0.5 s |
| Q測定時定数 | 0.02 s |
| Bus5容量性サセプタンスB | 1 pu、全期間接続 |
| 負荷G | 2.2682301152333055 pu |
| 系統係数k | 0.6812730259441179 |
| P指令 Bus1/2/3/7 | 0.5 / 0.4 / 0.4 / 0.4 pu |
| 事故前Bus5電圧 | 0.996594324 pu（要求下限0.98 pu） |
| 事故 | Bus4の20 pu受動シャント、1.00–1.15秒 |
| 除去時操作 | 線路4–5を開放 |
| 事故後の確認時間 | 1000秒 |

```text
ν=(ω−ω0)/ω0
M νdot = Pset−Pcap−(D+D1)ν−D2(ν−z)
zdot=ωD(ν−z)
δdot=ω0ν
D=1/mp, M=2H, τp=M/D
```

## 実行

リポジトリ直下で実行する。引数なしは標準ケース、smoke.csvは事故後30秒、demo.csvはD₁=0/10/20を比較する。

```bash
julia --project=provenance -e 'using Pkg; Pkg.instantiate()'
python -m pip install -r code/requirements.txt
julia --project=provenance --startup-file=no code/run.jl
julia --project=provenance --startup-file=no code/run.jl smoke.csv
julia --project=provenance --startup-file=no code/run.jl demo.csv
python code/analyze_current.py runs/current/current_D1_0_H2p5_mp0p10_B1
```

新CSVではH・mp・D1等を列に明記し、`current_case.jl`が実パラメータを生成する。新CSVのD1/D2/omega_dが優先され、旧入口用環境変数VSM_D1/VSM_D2は新CSVの値を上書きしない。条件を変更したらcase名も変える。同じ名前の異なる条件・コードで保存軌道を再使用することは拒否する。

`data/current_reference/` は今回の補償条件で確認済みの事故前・事故後平衡点と全パラメータである。毎回Newton補正・局所安定性確認を行う。CSVのB・k・負荷等を変更して補正や事故前電圧条件を満たせない場合は停止し、存在しない平衡点を仮定して計算しない。

出力は無視対象の `runs/current/<case>/`。段ごとの全状態・D2状態、全期間の観測CSV、実パラメータ、根、機別分類を保存する。各イベントでは14代数変数だけを整合化し、D2内部状態を引き継ぐ。再開署名はCSV行、コード、参照入力を含む。

## 保存図とDrive資料

主ケースの保存図は [figures/current](../figures/current/)、圧縮時系列は [results/current_reference](../results/current_reference/)。Git上の小さな参照データだけでPythonによる再描画ができる。

[paper_materials](../paper_materials/README.md)にはGoogle Driveで整理した補償後31図、統合レポート、図用CSV、元レポート、監査表を収録した。元の図の条件・数値は書き換えない。この資料のF01–F30にはD₁=10/20の過去比較が含まれ、F31が今回のD₁=0の回転例である。**標準設定をD₁=0に変更したことは、以前のD₁=10の引き込み領域をD₁=0で再計算したことを意味しない。**

旧Droop保存結果は [LEGACY_DROOP.md](LEGACY_DROOP.md)、旧CSVは `data/legacy/` に残す。旧設定の実行例は `VSM_D1=0 VSM_D2=0 julia --project=provenance code/run.jl legacy/smoke.csv`。新規実行の標準には使わない。

## 判定の範囲

主ケースでは遠方3機が1000秒の負方向回転、Bus1が同期回復する。分類は位相・周波数・複数時間窓による有限時間判定で、永久回転の数学的証明ではない。H・mₚの値はモデルの電力ベースに対する設定であり、全VSMの標準値や実機定格にそのまま対応するとはしない。
