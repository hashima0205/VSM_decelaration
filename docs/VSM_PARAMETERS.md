# 現在のVSM係数

全4機でH=2.5秒、mp=0.10（10%）、D1=0、D2=100、ωD=50 s⁻¹を使用する。D=1/mp=10、M=2H=5秒、換算用τp=M/D=0.5秒。

mpはDroopのP–f勾配、Dはその逆数であり、独立した2つの指定ではない。コードのKpはrad/s/puなのでKp=ω0mpとなる。Hとmpは独立に選択でき、τpを両者に合わせて計算する。H=2.5秒にしたためにmp=10%が不可避になったという意味ではない。

REGFM_B1の表1の設定例はH=0.5秒、mp=0.02、D1=0、D2=100、ωD=50。同じ電力ベースを仮定すると、現在の**VSM主要係数**ではHとmpが各5倍で、D1/D2/ωDは例と一致する。この表は一律の推奨範囲・許容限度ではない。各機定格と共通puベースの対応は別途確定する必要がある。

出典：Du et al., *Virtual Synchronous Machine Grid-Forming Inverter Model Specification (REGFM_B1)*, UNIFI-2024-6-1 / NREL/TP-5D00-90260, June 2024, Table 1。[国立研究所の公開版](https://docs.nlr.gov/docs/fy24osti/90260.pdf)。ωDは伝達関数sD2/(s+ωD)の極として扱い、[PowerWorldの定義](https://www.powerworld.com/WebHelp/Content/TransientModels_HTML/Machine%20Model%20REGFM_B1.htm)の1/sと対応させる。

ここではVSMの慣性・周波数制御の主要係数を比較する。GFM全体の電圧・電流制御や電流制限を含めてREGFM_B1全体を同一に実装したという意味ではない。
