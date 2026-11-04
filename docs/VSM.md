> D₁・D₂の追加後の設定・状態数は[VSM_DAMPING.md](VSM_DAMPING.md)を参照してください。以下の等価性・参照値照合は追加減衰を無効にした場合です。

# Droop環境へのVSM適用

## 基準と変更範囲

基準は `hashima0205/gfm-deceleration-separated-equilibria` のコミット
`3569b4cba0f5d6bee9e7bf1377ec9c52a599cc11` です。284ファイルをGitHubのGit blobハッシュと照合しました。取得にはローカルの同リポジトリのクローンとGitHub APIによる最新差分の同期を使用しました。

入力CSV、平衡点候補、ネットワークの凍結ソース、Project.toml、Manifest.toml、解析用Python、保存結果・図はこの基準からそのまま引き継ぎます。旧VSMパッケージのcase0788入力、独自の依存環境、同梱PowerDynamicsは使用しません。

変更はVSMの追加、VSM積分への接続、再開判定へのVSMコードハッシュ追加、READMEの案内です。新たにVSM検証コードとこの文書・出典記録を加えています。

## 方程式と状態

旧VSMの `vsm/code/vsm.jl`（コミット `91f98f7c193d43b5f407b574e2166f1beccdec66`）を移植しました。
4台の有効電力フィルタ状態Pfを、pu周波数偏差νに置換します。

```text
ν = (Kp / ωbase) (Pset − Pf)
D = ωbase / Kp
M = τp D = 2H
M dν/dt = Pset − Pcap − Dν
dδ/dt = ωbase ν
Pcap = VCr Igr + VCi Igi
```

Kpは元モデルのrad/s/pu単位のゲインです。M,D,Hは各ケースの実パラメータから計算するため、旧VSM中心例のH=27.175 sを全条件へ固定することはありません。P側フィルタ状態を別に追加することもありません。

元ネットワークの右辺をDroop座標へ戻した状態で評価し、4個のPフィルタ行と4個の角度行を上式で上書きします。Q–V、PI、LCL回路、負荷、線路、電流指令制限、代数制約は元モデルのままです。52微分状態＋14代数変数と質量行列も保持します。

## 積分とファイル互換性

`code/model.jl`から`code/vsm.jl`を読み込みます。実際にODEProblemを作る4か所（共通engine、trajectory_voltage_probes、tau010_basin、tau010_chord_basin）はすべて`solve_vsm`を使います。他の入口はこれらを呼び出すため同じVSMを使用します。

`solve_vsm`は初期値をν座標へ写し、VSMのODEFunctionを積分し、観測・保存前にDroop座標へ戻します。元のRodas5P/Rodas4P選択、許容誤差、最大刻み、保存時刻は呼出側から引き継ぎます。代数初期化も元コードです。

保存する66状態CSVや波形のPf列は、解析互換のために復元したPfです。VSM積分器ではその4スロットはνです。`solve_vsm`の返り値`vsm_u`でネイティブ状態も確認できます。角度・回路・PI・Q状態の座標は変わりません。既存の平衡点探索と固有値評価は元のDroop座標を使います。定数パラメータでの可逆な座標変換なので、平衡点と固有値は対応します。

事故切替の前後では元コードのパラメータと代数整合化を使用します。周波数写像に関わるKp、Pset、ωbaseをイベントで変更するケースはこの既存事故シナリオには含まれません。そのようなイベントを追加する場合は、νの連続性を別途設計・検証してください。

主ケースと探索の再開判定にはVSMコードのハッシュを追加しています。元Droopの生成済みチェックポイントを混ぜず、新規クローンで実行してください。

## 保存済み結果と再計算

`results/`、`figures/`、`tests/reference/`および元のREADME本文はDroop版の保存結果です。VSMで全探索を再実行した結果という意味ではありません。VSMの全300～1000秒計算や全領域探索は今回の適用確認には含めません。

検証コマンド：

```bash
julia --project=provenance --startup-file=no code/check_vsm.jl
julia --project=provenance --startup-file=no code/run.jl smoke.csv
python code/check_reference.py --smoke
```

`check_vsm.jl`は元のパラメータ生成を利用し、τp=0.1/1.16/1.18/1.2 sの事故前・事故中・事故後について、座標往復・変更しない状態・右辺の変換等価性を確認します。τp=1.2 sでは各トポロジーの20 ms軌道も元Droop積分と比較します。smokeケースは元入力の事故後30秒を使用し、既存の`check_reference.py`で全66状態の終端値・各機設定・平衡点を照合します。

## 今回の検証結果（2026-11-03）

- クローン元との差分検査：269ファイルが完全一致。既存15ファイルの変更は上記のVSM接続・再開判定・README案内。
- `check_vsm.jl`：77項目すべて合格。右辺の変換誤差は最大1.90×10⁻¹⁴、20 ms軌道の全状態差は最大1.62×10⁻¹⁰。
- `run.jl smoke.csv`：事故前・事故中・事故後30秒がすべてSuccess。
- 元の`check_reference.py --smoke`：全66状態と各機設定・平衡点の照合が合格。終端差の最大値は事故前7.55×10⁻¹⁵、事故除去時2.45×10⁻¹¹、事故後30秒9.72×10⁻¹⁴（状態ごとの単位が混在する絶対差）。
- 元の`check_saved_basins.py`：保存済み281ケース・264点・初期状態・波形・SHA-256一覧が合格。これはDroop保存結果の整合性検査です。
- Julia/Python構文検査を実施。

Julia 1.12.5、1スレッド、OPENBLAS_NUM_THREADS=1で実行しました。Project.tomlとManifest.tomlはクローン元から変更していません。既存キャッシュだけを使う`--compiled-modules=existing`ではモデル初期化中にLinearSolveのworld-ageエラーが発生したため、一時領域にキャッシュを生成できる通常のJulia起動で検証しました。依存ソースの修正やバージョン更新はしていません。

Python照合にはローカルに導入済みのnumpy 2.3.4 / pandas 2.3.3を使用しました。配布用requirements.txtは元の指定を保持しています。

非VSM部分の一致は次のコマンドで再確認できます。

```bash
python code/check_vsm_base.py
```
