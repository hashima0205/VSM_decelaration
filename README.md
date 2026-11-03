# VSMを含む電力系統の同期回復と減速脱調

詳細GFMモデルの有効電力フィルタ状態をpu周波数偏差へ変換し、仮想同期機（VSM）の動揺方程式として実装したシミュレーションです。Droop制御との等価性と、事故後に同期を回復する条件・基準位相に対して負方向に回転し続ける条件を比較します。

**保存済みの結果表は環境構築なしで確認できます。** 再計算にはJulia、解析・作図にはPythonを使用します。今回収録する結果は2026-10-30の元実行によるもので、この配置で新たに時間積分した結果ではありません。

## 1. 最初に見る結果

[10計算の比較表](vsm/reference_results/comparison.csv)と[検証結果・限界](vsm/docs/VALIDATION.md)を参照してください。以下は事故除去後300秒の結果です。

| 条件 | 制御 | τq [s] | 系統係数k | 遠方群の内部位相変化 [回転] | 結果 |
|---|---|---:|---:|---:|---|
| A / B | Droop / 等価VSM | 1.087 | 1.0299 | −43.677485 | 遠方3機が負方向回転、Bus1は回復 |
| C / D | Droop / 等価VSM | 1.000 | 1.0299 | −0.215983 | 全機回復 |
| E | VSM | 0.020 | 1.0299 | −0.216261 | 全機回復 |
| F | VSM | 0.020 | 0.8000 | −0.113389 | 全機回復 |
| G | VSM | 0.020 | 1.0310 | −0.219639 | 全機回復 |
| H | VSM | 1.087 | 1.0200 | −0.200975 | 全機回復 |

遠方群はBus2・3・7の等重み平均です。回転数は事故除去時からの内部角変化を2πで割った値で、回復時に0へ戻る必要はありません。B / Dには最大刻み幅を細分化した追加計算があり、計10計算です。

DroopとVSMの比較観測量の最大絶対誤差は約1.26×10⁻⁸（各記録単位）。中心例Bでは、局所安定な事故後平衡点が存在しながら負方向の位相スリップが継続しました。波形CSVや図は同梱していないため、表から時系列を再作図することはできません。

## 2. 何を模擬しているか

| 項目 | 設定 |
|---|---|
| GFM / 固定外部系統 | Bus1・2・3・7 / Bus6、60 Hz |
| モデル | 52微分状態＋14代数変数の詳細DAE |
| 事故 | 絶対時刻1.0 sにBus4へ20 pu受動シャントを投入 |
| 事故除去 | 1.15 sにシャント除去と線路4–5の開放 |
| 中心例のVSM換算値 | H=27.175 s、D=50、M=54.35 s（全4機） |
| C / Dの換算値 | H=25 s、D=50、M=50 s（全4機） |
| 系統係数k | 線路4–6・5–6のRとXを同率で変更する倍率 |

LCL回路、電圧・電流PI、Q–V制御、仮想インピーダンス、電流指令制限を保持します。独立したPフィルタを慣性に重ねて追加する実装ではありません。kとSCRは別の量です。[数式・単位・出典](vsm/docs/EQUATIONS_AND_REFERENCES.md)と[全条件・判定基準](vsm/docs/CALCULATION.md)に詳細を示します。

## 3. シミュレーションを再計算する

元実行の環境はJulia 1.12.5です。Python依存は[requirements.txt](vsm/code/requirements.txt)、Julia依存は固定Manifestと使用済みPowerDynamicsソースを同梱しています。

リポジトリ直下から、まだ存在しない実行フォルダを準備します。

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r vsm/code/requirements.txt
python vsm/code/prepare_recompute.py runs/vsm_run_001
cd runs/vsm_run_001
julia --project=provenance -e 'using Pkg; Pkg.instantiate()'

# A～D: Droop / VSMの等価性
OPENBLAS_NUM_THREADS=1 JULIA_NUM_THREADS=1 julia --project=provenance --startup-file=no code/run.jl > logs/phase1.log 2>&1
MPLCONFIGDIR=/tmp/vsm_mpl python code/analyze.py

# 等価性ゲート合格後: E～HとB / Dの刻み幅照合
VSM_PHASE=2 OPENBLAS_NUM_THREADS=1 JULIA_NUM_THREADS=1 julia --project=provenance --startup-file=no code/run.jl > logs/phase2.log 2>&1
MPLCONFIGDIR=/tmp/vsm_mpl python code/analyze.py
python code/audit.py
```

再実行は新しいフォルダ名を指定してください。モデル構築・積分には時間がかかります。任意のPDF生成、出力列、精度、再開時の注意は[計算手順](vsm/docs/CALCULATION.md)に記載しています。

## 4. ファイル構成とコード案内

[参考リポジトリ](https://github.com/hashima0205/gfm-deceleration-separated-equilibria)と同様に、コード・入力・説明・結果・依存環境を分離しています。既存コードの相対参照を保持するため、実験一式は`vsm/`に収めています。

| 場所 | 役割 |
|---|---|
| [vsm/code/](vsm/code/) | 計算入口、VSM変換、詳細モデル、解析・監査・報告 |
| [vsm/inputs/](vsm/inputs/) | 事故・制御・回路の設定と状態対応 |
| [vsm/data/seeds/](vsm/data/seeds/) | 事故前後の平衡点候補 |
| [vsm/docs/](vsm/docs/) | 数式、再現手順、方法、検証範囲 |
| [vsm/reference_results/](vsm/reference_results/) | 元実行の比較・誤差・平衡点・監査結果 |
| [vsm/provenance/](vsm/provenance/) | Julia固定環境、モデルの凍結ソース、第三者ライセンス |
| [vsm/tables/SCR_source.csv](vsm/tables/SCR_source.csv) | SCR計算に用いる回路値 |
| [UPLOAD_MANIFEST.csv](UPLOAD_MANIFEST.csv) | 配布ファイルのサイズとSHA-256（一覧自身を除く） |

`runs/`、仮想環境、生成ログ・チェックポイントはGit管理から除外します。ルートの`README_VSM.md`と`VSM_TRANSFER.json`はローカル移動時の記録として残し、配布には含めません。

## 5. 結果から言える範囲

有限時間の計算であり、無限時間の持続回転や全状態空間の吸引域を証明していません。H=27.175 sは数学的な等価換算値で、実機設計の妥当性を示すものではありません。DC側・PWM・保護・熱容量は対象外です。完了した精度確認は最大刻み幅の細分化であり、極小許容誤差への収束確認は未完了です。

第三者コードのライセンスと変更点は[THIRD_PARTY.md](vsm/provenance/THIRD_PARTY.md)を参照してください。
