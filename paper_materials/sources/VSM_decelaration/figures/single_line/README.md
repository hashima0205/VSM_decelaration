# 単線結線図・電圧・P/Q潮流

参考画像の配置に合わせ、母線・配線・交流電源・無限大母線・負荷・補償コンデンサを描いた今回の8母線系統専用図です。

| 図 | PNG | PDF | SVG |
|---|---|---|---|
| 数値なしの系統図 | [PNG](schematic.png) | [PDF](schematic.pdf) | [SVG](schematic.svg) |
| 事故前の電圧・潮流 | [PNG](pre_equilibrium.png) | [PDF](pre_equilibrium.pdf) | [SVG](pre_equilibrium.svg) |
| 事故後安定平衡点 | [PNG](post_equilibrium.png) | [PDF](post_equilibrium.pdf) | [SVG](post_equilibrium.svg) |
| D1=10：事故除去5秒後 | [PNG](D1_10_post_t5.png) | [PDF](D1_10_post_t5.pdf) | [SVG](D1_10_post_t5.svg) |
| D1=20：事故除去5秒後 | [PNG](D1_20_post_t5.png) | [PDF](D1_20_post_t5.pdf) | [SVG](D1_20_post_t5.svg) |

![事故前の電圧とP/Q潮流](pre_equilibrium.png)

Pは青、Qは緑。線路ラベルの母線順に両端の符号付き電力を示します。正は各母線から線路への流入。両端の和が線路損失です。各図に対応する `_buses.csv` / `_lines.csv` / `_audit.json` も保存しています。

事故後安定平衡点の図は、回転軌道の到達状態を示すものではありません。過渡応答はD1=10/20の別図に示しました。

[コード・入力・再作図方法](../../docs/SINGLE_LINE.md)
