# 計算方法と再現手順

## 環境と実行

元の10計算はJulia 1.12.5、PowerDynamics 4.4.0、NetworkDynamics 0.10.16、OrdinaryDiffEq 6.108.0で実行しました。全依存は`provenance/Manifest.toml`、主要バージョンは`provenance/versions.json`に保存しています。

PowerDynamicsには元研究から継承したDroop既定周波数50→60 Hzの変更があります。同梱の`PowerDynamics_used`と元ライセンスを保持し、この配布用Manifestでは該当パッケージを相対pathで固定しています。依存バージョンの更新・解決は行っていません。

リポジトリ直下から、まだ存在しない実行フォルダを指定します。

```bash
python vsm/code/prepare_recompute.py /absolute/path/to/new_vsm_run
cd /absolute/path/to/new_vsm_run

# 初回のみ、固定Manifestに従って依存を取得。Pkg.updateは実行しない。
julia --project=provenance -e 'using Pkg; Pkg.instantiate()'
python -m pip install -r code/requirements.txt

# A～D: Droop / VSMの等価性
OPENBLAS_NUM_THREADS=1 JULIA_NUM_THREADS=1 julia --project=provenance --startup-file=no code/run.jl > logs/phase1.log 2>&1
MPLCONFIGDIR=/tmp/vsm_mpl python code/analyze.py

# 等価性ゲート合格後: Q時定数・SCRと代表例の刻み幅照合
VSM_PHASE=2 OPENBLAS_NUM_THREADS=1 JULIA_NUM_THREADS=1 julia --project=provenance --startup-file=no code/run.jl > logs/phase2.log 2>&1
MPLCONFIGDIR=/tmp/vsm_mpl python code/analyze.py
python code/audit.py

# 任意: Markdown/PDFレポート生成
MPLCONFIGDIR=/tmp/vsm_mpl python code/report.py
```

Python解析にはnumpy 2以降が必要です。PDFレポート生成はLinuxの`/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`を使用します。他環境では`report.py`のフォントパスを変更してください。数値計算・CSV解析にはこの日本語フォントは不要です。

モデル構築には数分かかる場合があります。今回は公開用の選別・Manifest参照先の整理と静的検査のみを行い、この公開配置での300秒計算は再実行していません。reference_resultsは元実行の検証結果です。

## 条件

GFMはBus1,2,3,7、スラックはBus6の60 Hz。Bus4の20 pu受動シャントを絶対時刻1.0 sで投入し、1.15 sで除去すると同時にline7（4–5）を開放します。各条件とも事故前平衡点から積分し、事故除去後300秒まで観測します。

| 条件 | 制御 | P側の等価τp [s] | τq [s] | k |
|---|---|---:|---:|---:|
| A | Droop | 1.087 | 1.087 | 1.0299 |
| B | VSM | 1.087 | 1.087 | 1.0299 |
| C | Droop | 1.000 | 1.000 | 1.0299 |
| D | VSM | 1.000 | 1.000 | 1.0299 |
| E | VSM | 1.087 | 0.02 | 1.0299 |
| F | VSM | 1.087 | 0.02 | 0.8 |
| G | VSM | 1.087 | 0.02 | 1.031 |
| H | VSM | 1.087 | 1.087 | 1.02 |

加えてB,Dの最大刻みを細分化して合計10計算です。`strict`というケース名は、最終結果では最大刻み幅だけを細分化した条件を指します。

kはline2（4–6）とline3（5–6）のR/Xを同率変更します。E/F/Gの比較ではM,D,Q時定数、PI、負荷、指令、事故時間を固定します。H/Bの比較もQ時定数を含め固定制御です。SCR=1/|Zth|は、負荷とLCLを除外し他GFMポートを開放、Bus6を接地した外部回路で評価します。

## 計算の流れ

1. 凍結ソースから詳細DAEを構築し、名前による状態・パラメータ索引を取得。
2. 各条件の事故前・事故後平衡点を既存候補からNewton再計算。残差を確認。
3. 中心差分Jacobianの代数部分をSchur補元で消去し、52次元の全固有値を算出。固定スラックのため自明な角度零固有値を除去する操作はしない。
4. 微分状態を保ってイベント時の代数変数を整合化し、pre/fault/postを積分。
5. A/BとC/Dの全機観測量を同じ時刻で比較。時間や位相を後合わせしない。各記録単位の最大絶対誤差1e-3未満を等価性ゲートとする。
6. ゲート合格後にE～Hと刻み幅照合を実行し、実パラメータ全ベクトルを比較して固定条件を検査。

基準積分はRodas5P、rtol=1e-9、atol=1e-11、dtmax=0.005 s。刻み幅照合は同じ許容誤差でdtmax=0.00125 sです。観測は事故中0.0005 s、事故後0.02 s、イベント直後20 msは0.0001 sです。

## 判定と出力

300秒末尾30秒の|Δf|<1e-4 Hzかつ終端角の安定根との差（2π剰余）が0.002 rad未満なら回復。内部角変化が−2回転を超え、末尾の最大Δf<−0.001 Hzなら負方向持続回転。遠方3機すべてが条件を満たす場合に遠方群負方向回転とします。その他の不安定応答・未判定を分けます。内部角・個別にunwrapした端子角・Bus1との差を保存します。

`data/*_trajectory.csv.gz`が全機観測、`data/*_root.csv`が平衡点、`*_eigen.csv`が全固有値（real,imag）、`checkpoints/`が初期・終端全状態と実パラメータです。VSMの旧Pf位置にはνが入るため、元のPfとして読まないでください。

DONEのあるケースはスキップします。途中失敗の再実行はログ・集計を追記するため、再現には新しい空のフォルダを使ってください。新しいkを追加する際は、対応する平衡点候補とSCR情報も準備する必要があり、現在の入口は任意条件の汎用探索器ではありません。
