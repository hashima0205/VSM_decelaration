# 現在の標準入口の検証

2026-11-05。`julia --project=provenance --startup-file=no code/run.jl` を引数なしで実行し、data/representative.csvからD1=0、H=2.5秒、mp=0.10を読み込んだ。

- 事故前・事故中・事故後1000秒が全てSuccess。
- M=5、D=10、換算用τp=0.5秒、D2=100、ωD=50 s⁻¹、Bus5 B=1を保持。
- 事故前V5=0.996594323887 pu。事故前の全保存点で0.98 pu以上。
- Bus1はrecovery、Bus2・3・7はnegative_running。
- 遠方平均内部角変化：−1691.482777875211回転。
- 代数残差の最大値：9.981×10⁻¹⁴。イベント前後のD2状態差：0。
- Pythonで機別分類を独立に照合し、保存済みの同一条件の圧縮時系列と全保存点を比較。時刻・区間が一致し、角度・周波数・Pcap・Q・Igを含む比較列の最大絶対差は1.819×10⁻¹²（列ごとの単位が混在）。

実行環境はJulia 1.12.5、Rodas5P、rtol=1e-9、atol=1e-11、dtmax=0.005秒。依存環境・元のネットワーク凍結ソースは変更していない。元モデルの265ファイルのGit blobハッシュ一致を確認した。

[実際の設定](../results/current_reference/settings.csv) / [分類と残差](../results/current_reference/result.csv) / [独立照合](../results/current_reference/validation.json)
