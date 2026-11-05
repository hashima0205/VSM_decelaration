# slack母線Bus6基準の引き込み領域図

固定slack母線Bus6の位相0 rad、周波数60 Hzを基準とした。遠方3機Bus2・3・7の平均内部角を横軸に用い、事故前点を原点へ移す操作や±πへの折返しは行っていない。

- [引き込み領域と事故軌道 PNG](basins_slack.png) / [PDF](basins_slack.pdf)
- [事故後30秒の広域表示 PNG](basins_slack_wide.png) / [PDF](basins_slack_wide.pdf)
- 事故前点：-0.323414656765 rad。事故後安定点：-1.669678512825 rad。
- D1=10はslack母線に対して位相が負方向へ進み続ける。主図の表示範囲を左へ離れるため、広域図に30秒までの軌道全体を示した。D1=20は安定点へ戻る。
- 背景はBus5基準図と同じ各43初期値・分類・三角形。初期全70状態からslack基準の位相を直接計算している。背景は初期値断面の条件付き領域であり、事故軌道は断面外の投影を含む。斜線は分類混在域で厳密な境界ではない。
- この座標では内部角と周波数は系統切替時にも連続。Bus5基準図での代数電圧位相の跳びは横軸に現れない。
- [描画用背景点](samples_slack.csv)、trajectory_slack_D1_10.csv / trajectory_slack_D1_20.csv、[基準・検証情報](slack_definition.json)。
- 再描画：`MPLCONFIGDIR=/tmp/vsm_mpl /home/students1/miniconda3/envs/julia/bin/python studies/h2p5_bus5_basins/plot_slack_basins.py`。再積分は不要。

[Bus5基準・元計算の詳細](README.md)
