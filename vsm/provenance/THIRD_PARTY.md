# 同梱ソースと環境

PowerDynamics 4.4.0の使用済み`src/`、`Project.toml`、`LICENSE`を`PowerDynamics_used/`に収録。登録版git-treeはb2c2d56c664c475b4dbb19280b8420c5b0d68f30。
元配布: https://github.com/JuliaEnergy/PowerDynamics.jl

継承した変更は`src/Library/Renewables/ComposableInverter.jl`のDroopOuterにある既定ω0を2π50から2π60へ変更した1行です。VSM実装はこのパッケージ本体には加えず、`../../code/vsm.jl`にあります。

元の著作権表記・LICENSE（MITおよび該当ファイルのMPL等の説明）とソース内のライセンスヘッダーを保持しています。本追加により第三者コードのライセンスを変更するものではありません。

`source_snapshot/`はcase0788を組み立てる既存研究コードの凍結コピーです。相対参照される小さな`output/*.csv`も必要な入力として保持しています。

今回の追加用ManifestはPowerDynamicsのgit-tree参照を相対path=`PowerDynamics_used`へ変更し、使用済みソースを明示的に選ぶ構成です。他の依存バージョンは元実行と同じです。パッケージ更新はしていません。
