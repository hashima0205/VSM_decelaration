> 現在の標準はD1=0、H=2.5秒、mp=0.10。[CURRENT_CASE.md](CURRENT_CASE.md)。pre/post入力を現在の基準から更新し、data/single_line/D1_0_post_t5を追加しました。D1=10/20の保存図も元の比較条件として残します。

# 今回の8母線系統専用の単線結線図

`code/plot_single_line.py` は、参考画像 `ref_file/4gfm_bus_system_ver2.png` の配置・表現に合わせた描画コードです。太い母線、交流電源記号、無限大母線、負荷矢印、コンデンサ・接地、開放スイッチを使用します。4台のGFM（Bus1・2・3・7）、固定slack（Bus6）、Bus5の定インピーダンス負荷・並列容量性シャント、全11線路を描きます。

## すぐに描く

以下はリポジトリ直下で実行します。Python依存は `code/requirements.txt` と同じ NumPy / pandas / Matplotlib です。作図にJuliaの起動や再積分は必要ありません。

```bash
python code/plot_single_line.py
```

既定の入力は `data/single_line/pre_equilibrium/`、出力は `figures/single_line/pre_equilibrium.png` / `.pdf` / `.svg`。母線表・線路両端の電力表・検証JSONも同時に保存します。PDFとSVGはベクトル出力です。

数値・潮流を省いた系統図：

```bash
python code/plot_single_line.py --schematic-only --output figures/single_line/schematic
```

事故後の安定平衡点：

```bash
python code/plot_single_line.py --input data/single_line/post_equilibrium --output figures/single_line/post_equilibrium
```

D1=10 / 20 の事故除去5秒後：

```bash
python code/plot_single_line.py --input data/single_line/D1_10_post_t5 --output figures/single_line/D1_10_post_t5
python code/plot_single_line.py --input data/single_line/D1_20_post_t5 --output figures/single_line/D1_20_post_t5
```

`--flow p` はPだけ、`--flow q` はQだけ、`--flow none` は線路の電力表示を省きます。`--digits 4` で小数桁、`--title "My snapshot"` でタイトルを変えられます。出力先は拡張子なしで指定してください。この環境でMatplotlibの設定先が書き込み不可の場合は、コマンド先頭に `MPLCONFIGDIR=/tmp/vsm_mpl` を付けてください。

## 数値の意味

- 母線：端子電圧の大きさ[pu]とBus6を0°とした端子電圧位相[°]。GFMの内部角δとは異なります。
- GFMとslackのP/Q：系統へ注入する端子電力。正は供給、負は吸収。GFMの有効電力指令やフィルタ・コンデンサ側の電力と区別します。
- 線路ラベル `L2 (4 / 6)`：1番目の数値はBus4から線路に入る電力、2番目はBus6から線路に入る電力です。両端とも「母線→線路」を正とします。
- **青がP、緑がQの矢印**。各線路の両端に、その端の電力の符号に応じた向きで描きます。Qが両端で正なら、両側から線路へ無効電力が供給され、線路で吸収されています。Pと同じ向きにQも流れるとは仮定しません。
- 計算式：`Iab=(Va−Vb)/(R+jX)`、`Sab=Va*conj(Iab)`、`Sba=Vb*conj(−Iab)`。線路損失は両端電力の和。開放線路はI=P=Q=0。
- Bus5：`Pload=G|V5|²`、コンデンサ注入 `Qcap=B|V5|²`。負荷とコンデンサを別記号で描きます。
- 事故後系統では線路4–5を開放スイッチで示します。

## 同梱した4スナップショット

今回の条件は H=2.5 s、M=5 s、ドループ由来D=10、D2=100、ωD=50 s⁻¹、B5=1 pu、k=0.6812730259441179、負荷G=2.2682301152333055 pu。

| 入力フォルダ | 内容 |
|---|---|
| pre_equilibrium | 事故前平衡点。Bus5電圧0.996594324 puで、指定の0.98 pu以上 |
| post_equilibrium | 事故後の安定平衡点。Bus5電圧0.857083394 pu |
| D1_10_post_t5 | D1=10の実事故応答。除去5秒後、絶対時刻6.15秒 |
| D1_20_post_t5 | D1=20の実事故応答。同時刻 |

両D1で平衡点の位置は共通です。`post_equilibrium` は事故除去直後でも、D1=10の回転軌道が到達した状態でもありません。実事故応答の図には「Saved dynamic state」と時刻を表示します。

元の入力は `studies/h2p5_bus5_voltage098_d1/D1_10p0_h1000/full_states.bin` および `D1_20p0_h1000/full_states.bin`。同梱CSVだけで再作図でき、元のbinがなくてもこの4枚を生成できます。元binのSHA-256は各 `metadata.csv` に保存しています。

## 新しい計算結果を取り込む

`code/export_single_line_data.jl` が、保存済みの全状態binからモデルの**実際のR・X・開閉状態・負荷G・B**を抽出します。描画側がkから線路定数を推測する構成ではありません。入力binは今回の `parts / pre / target / H / M / db / c` を持つSerialization形式です。

```bash
julia --project=provenance code/export_single_line_data.jl \
  --bundle /path/to/D1_10/full_states.bin \
  --compare-bundle /path/to/D1_20/full_states.bin \
  --output data/single_line_new \
  --post-time 5
```

`--compare-bundle` は省略できます。`--post-time` は事故除去後の時刻です。保存時刻に最も近い状態を選び、実際の時刻をmetadataに記録します。範囲外の時刻は拒否します。補間・再積分はしません。別の `--output` へ出すと既存入力を保持できます。

エクスポートフォルダのファイル：

| ファイル | 内容 |
|---|---|
| voltages.csv | 全8母線の複素電圧とモデルから取得した照合用P/Q注入 |
| branches.csv | 線路番号、両端母線、R、X、active（1=閉、0=開） |
| metadata.csv | 状態名、時刻、平衡点か否か、制御係数、G/B、残差、出典ハッシュ |
| state.csv | 元の全66状態（既存のDroop座標入出力形式） |

自分でこの3つの入力CSVを用意しても描画できます。`reference_*_injection` はBus6以外で必須で、モデルとの照合に使います。

## 変更箇所と検証

`TOPOLOGY` が今回の11線路の接続、`BARS` が母線の端点、`PATHS` が配線経路、`BUS_LABELS` / `LINE_LABELS` が注記位置です。配置変更はここにまとめてあります。`draw_single_line(...)` はFigureを返す関数なので、別の作図コードからも使用できます。

出力前に全母線の注入電力と線路電流の整合性、Bus5負荷・コンデンサ、各線路の複素電力損失、全系統の有効電力収支を検査します。照合不一致は描画エラーにします。今回の4状態で母線注入誤差は3.4×10⁻¹⁵ pu以下。事故前・事故後の結果は従来の独立したB=1潮流表とも照合し、最大差1.2×10⁻¹⁴ pu以下でした。配線経路の22端点がすべて正しい母線上にあることも確認しています。

[図の一覧](../figures/single_line/README.md)
