# Hartmann 三相 Delta-switch 整流器：PLECS 开关级复现

[中文](README_zh.md) | [English](README_en.md)

本目录包含实际在 **PLECS Standalone** 中运行的开关级模型，不是平均模型，也不是用 Python 替代 PLECS 求解。模型文件为 PLECS 4.9 格式；`results/` 中的三相 baseline 由 PLECS 4.9 产生，缺相工况由本机 PLECS 5.0.2 运行（5.0 可直接打开 4.9 模型，无需转换）。

## 打开和运行

1. 在 PLECS 打开 `Hartmann_DeltaSwitch.plecs`。
2. 从 **Simulation** 菜单启动仿真，默认运行 0.12 s。
3. 双击 `Main_Waveforms`：依次显示三相电源电压、三相输入电流、直流母线电压、电流参考。
4. 双击 `MOSFET_Gates`：信号顺序为 `s12, s21, s23, s32, s13, s31`。
5. 在 **Simulation Parameters → Initialization** 中修改参数。模型内嵌完整初始化代码，不依赖外部 MATLAB 文件。`parameters.m` 是这份代码的便于阅读副本，单独修改该副本不会自动改变模型。

默认是论文 Fig.8(a) 的 **800 Hz、115 V 相电压有效值、400 V、5 kW** 工况。改 `fline=400` 可检查 400 Hz 工况；改 `Vinit=280` 可检查预充电后电压恢复。

缺相工况用单独生成的变体 `Hartmann_DeltaSwitch_PhaseLoss.plecs`，见下文「缺相运行」。

## 与论文的对应

来源：Hartmann, Miniboeck, Ertl, Kolar, *A Three-Phase Delta Switch Rectifier for Use in Modern Aircraft*, IEEE Transactions on Industrial Electronics, 59(9), 3635–3647, 2012, DOI: 10.1109/TIE.2011.2158770。原 PDF 位于本目录的上一级。

| 模型内容 | 论文位置 | 实现 |
|---|---|---|
| 三相电源、升压电感、六二极管桥、直流电容 | Fig.1(b) | 原生电气元件组成的实际开关电路 |
| Delta 双向开关 | Fig.2(a) | 三组共源背靠背 MOSFET，共六只，包含体二极管 |
| 电流参考 | Fig.6 | `i_ref[k] = Gref * v_grid[k]` |
| 电流 P 调节和电网电压前馈 | Fig.6 | `vr[k] = v_grid[k] - Kcurrent*(i_ref[k]-i[k])` |
| 星—三角变换 | 式(12)–(14) | `vr_ij = vr[i]-vr[j]` |
| 三角波 PWM | Fig.7，式(15)–(17) | 单一 0–1 三角载波；比较 `carrier > vr_ij/Vdc` |
| 扇区钳位 | Table III | 两相电压同号时，该双向支路两只 MOSFET 均关断；反向器件常通，正向器件 PWM |
| 外环 | Fig.6，VI 节 | PI 输出电导，带电导限幅和积分抗饱和 |
| 缺相运行 | Fig.8(b)、Fig.14 | 见下文：单相断开后控制器不加改动继续两相运行 |

表 III 的六扇区控制可由三相电压符号统一实现，因此无需切换电流调节器本身。`Hartmann_Control` 是可编辑的 C-Script，代码同时保存为 `controller_*.c` 阅读副本。三角载波是 PLECS 原生模块，PWM 比较和相电压过零均注册了零交叉事件，门极只在求解器主步更新。

## 参数和明确的补充假设

| 参数 | 值 | 来源/说明 |
|---|---:|---|
| 相电压有效值 `Vph` | 115 V | 论文 IV 节；线电压约 199.19 Vrms |
| 电源频率 `fline` | 800 Hz | 默认对应 Fig.8(a)，另验证 400 Hz |
| 开关频率 `fsw` | 72 kHz | 论文 IV 节 |
| 每相电感 `Lboost` | 330 µH | Fig.8 仿真值；实物表 VI 为 326 µH |
| 输出电容 `Cdc` | 1476 µF | 表 VI：18×82 µF 并联 |
| 输出参考 `Vref` | 400 V | 论文 |
| 负载电阻 `Rload` | 32 Ω | 为 400 V、5 kW 工况选择的电阻负载 |
| 每相串联电阻 `RL` | 20 mΩ | 本模型补充假设 |
| 开关/二极管导通电阻 | 各 1 mΩ | 数值模型假设，不是论文器件的实际导通参数 |
| 二极管正向压降 | 0 V | 理想化功率电路假设 |
| 初始电容电压 `Vinit` | 400 V | 默认预充电状态；初始电感电流为 0 |
| 电流环增益 `Kcurrent` | 8.2938 V/A | 依据 `2*pi*4000*Lboost` 整定 |
| 电压环 `Kpv` | 0.00264417 S/V | 20 Hz 自然频率、约 0.707 阻尼比的工程整定 |
| 电压环 `Kiv` | 0.234990 S/(V·s) | 与上项配套 |
| 电导上限 `Gmax` | 0.25 S | 本模型补充的饱和限制 |

**控制器不是原硬件增益逐项照抄。** 论文给出电流 P 增益 `kp=0.25` 和约 4 kHz 带宽，但没有给出足够的传感器/调制器缩放信息，不能直接把 0.25 当成 SI 单位下的 V/A 增益。这里按物理单位整定并公开了计算式。外环论文给出约 20 Hz 带宽，但未完整公开 PI 数值；这里使用 20 Hz 自然频率进行初始设计，未声称精确复现硬件的闭环带宽。

原生 `ThreePhaseVoltageSource` 的相位参数使用弧度，设置 `pi/2` 使 A 相从余弦峰值开始。三相中性点接参考地，直流侧保持浮置。

## 已运行的检查

实际数值见 `results/verification.json`，波形见相应 PNG，完整均匀采样数据见 NPZ，最后四个工频周期见 CSV。所有结果均来自本机 PLECS。

| 工况 | 平均 Vdc | 输出功率 | 每相 Irms | 每相 PF | 电流 THD（2–40 次） |
|---|---:|---:|---:|---:|---:|
| 800 Hz / 5 kW | 约 400.000 V | 约 5000.0 W | 约 14.749 A | 约 0.98528 | 约 3.80% |
| 400 Hz / 5 kW | 约 400.000 V | 约 5000.0 W | 约 14.601 A | 约 0.99527 | 约 2.30% |
| 800 Hz，初始母线 280 V | 稳态约 400.000 V | 稳态约 5000.0 W | 约 14.749 A | 约 0.98528 | 约 3.80% |

280 V 恢复工况的母线峰值约 406.58 V，瞬态最大相电流约 40.79 A。这是闭环恢复测试，**没有包含从零电压上电的预充电硬件**。

脚本还检查三相电流和、各扇区的关断钳位、有限数值、输出稳压和功率。**关于收敛性检查的说明：** 现有两版结果把 `MaxStep` 从 `1/(72k*10)` 改为 `1/(72k*40)`，但两者的 `ΔVdc`、`ΔP`、`ΔIrms` 分别只有 5e-11 V、1e-9 W、2e-10 A，说明该步长参数实际上没有起约束作用（步长由 0.5 µs 的输出时刻和误差控制决定）。因此这一项**不构成有效的收敛性证明**，需要改成真正会改变步长的对照（例如改用固定步长求解器，或把输出采样放粗）。

THD 使用最后 8 个完整工频周期，均匀 2 MHz 采样，取 2–40 次工频谐波，除以基波有效值；因此不包含 72 kHz 附近的开关谐波。PF 则由时域真实功率除以 Vrms×Irms 计算，包含电流纹波。不要将这两个指标混为一谈。

800 Hz 下 P 型电流环有可见基波跟踪误差与相移，这解释了 PF 低于 400 Hz 工况；本版未用额外谐振控制或电流导数前馈改变论文的控制结构。

## 缺相运行（Fig.8(b) / Fig.14）

变体模型 `Hartmann_DeltaSwitch_PhaseLoss.plecs` 由生成器一次性产出：

```text
python build_model.py --phase-loss
```

相对 baseline 只加了三样东西，**控制器和主电路其余部分一行未改**：

| 新增元件 | 作用 |
|---|---|
| `K1` | A 相电源侧串联理想开关，`s_init=1`，在 `t_loss` 时刻断开 |
| `C_loss` + `R_loss` | 100 nF + 10 Ω 跨接断口，代表断口杂散电容，给断相电感电流提供通路并阻尼；若用 3.4 µF 则该相在 800 Hz 仍残留约 3.8 A，故取 100 nF |
| `LossStep` | Step（1→0，时刻 `t_loss`），驱动 K1 栅极 |

`t_loss` 是新的模型变量（默认 0.06 s），可在 `ModelVars` 中覆盖。电压测量 `v1` 仍接在开关的电网侧，因此控制器看到的三相电压在缺相前后都保持正常——这正是论文「控制器结构不变」的前提。

运行与出图（每次运行结束后脚本自动 `plecs.close()`，不在 PLECS 里留下打开的模型）：

```text
python run_phase_loss.py --pnom 3000 --tloss 0.06    --tag phase_loss_3kW
python run_phase_loss.py --pnom 3000 --tloss 0.00085 --tag phase_loss_3kW_papertiming
python run_phase_loss.py --pnom 5000 --tloss 0.06    --tag phase_loss_5kW
python run_phase_loss.py --pnom 5000 --tloss 0.06 --gmax 0.5 --tag phase_loss_5kW_gmax05
```

结果（800 Hz；断相后窗口取最后 8 个工频周期）：

| 工况 | i1 (rms) | i2 / i3 (rms) | THD | 平均 Vdc | 实际功率 | 限幅 |
|---|---:|---:|---:|---:|---:|---|
| 3 kW，60 ms 断相 | 0.43 A | 19.8 / 19.7 A | 23.7% | 400.1 V | 3002 W | 未触发 |
| 3 kW，0.85 ms 断相（论文时序） | 0.41 A | 18.1 / 18.0 A | 21.9% | 399.9 V | 2999 W | 未触发 |
| 5 kW，60 ms 断相，Gmax=0.25 | 0.45 A | 27.3 / 27.2 A | 27.0% | 340.5 V（仍在下降） | 3624 W | 触发（Gref=0.25 S） |
| 5 kW，60 ms 断相，Gmax=0.5 | 0.48 A | 45.2 / 45.1 A | 17.7% | 337.5 V | 3560 W | 触发（Gref=0.5 S） |

观察：

1. **3 kW 两相运行成立**：断相后 `i1≈0`，剩余两相各约 18–20 A，母线回到 400 V、功率维持 3 kW；60 ms 断相时母线瞬态最低约 384.6 V，约 50 ms 恢复。0.85 ms 断相（论文 Fig.8(b) 的时序）终态与之基本一致。
2. **5 kW 两相运行不成立**：默认 Gmax 下外环饱和、母线跌到约 340 V；把 Gmax 放宽到 0.5 S 后 `Gref` 又顶到 0.5 S、电流涨到 45 A，母线仍停在约 337 V。说明限制来自**调制器占空比饱和**而不是模型自加的电导限幅，即该硬件参数下两相可输出的最大电压不足。
3. 这与论文自洽：Fig.8(b) 两相跑 3 kW、Fig.14 两相跑 2.25 kW，论文没有在 5 kW 下演示缺相。
4. 两相时 `i2 = -i3` 必须逐时刻成立，所以两相 PF 必然不对称（一个约 0.97、一个约 0.4），这是拓扑性质，不是模型错误。

局限：没有 EMI 滤波器，因此看不到论文 Fig.14(b) 中滤波器电容引起的断相电感电流振荡；没有实现「检测到缺相后把 S12 钳死」的附加逻辑；电流环仍是 P 型（PF 0.985），绝对的两相功率上限可能比硬件略保守。

## 本版范围

已完成基本功率拓扑、论文所述 PWM/钳位控制结构、直流闭环稳压、正常三相稳态、母线恢复以及**缺相两相运行**。

尚未建立 EMI 滤波器、寄生电容/共模路径、实际器件热损耗、非线性电感、预充电电阻/二极管/晶闸管；缺相检测与钳位逻辑也未实现。因此不能用此模型宣称复现了论文的效率、共模 EMI、实物启动过程或完整的缺相容错性能。400 Hz 的 THD 数值接近论文结果，仍不代表完整硬件复现；滤波器、功率等级和损耗条件不同。

## 重新自动验证或重建

打开 PLECS，并在 Preferences 中启用本地 RPC 端口 1080。终端在此目录运行：

```text
python run_verify.py
```

需要 Python 的 `numpy`、`matplotlib`，XML-RPC 使用标准库。普通手动打开运行模型不依赖 Python 或 RPC。

```text
python build_model.py                # 重新生成 baseline 及参数/控制器阅读副本
python build_model.py --phase-loss   # 生成缺相变体（不覆盖 baseline）
```

`build_model.py` 会覆盖当前目录中同名生成文件，手动修改原理图后请先另存；`--phase-loss` 只写 `Hartmann_DeltaSwitch_PhaseLoss.plecs`，不会改动 baseline、`parameters.m` 或 `controller_*.c`。自动验证不会改动初始化参数，只通过本次仿真覆盖选项设置测试工况。

PLECS 的两条使用约束（调试时踩过）：一个端子只能出现在一条 `Connection` 里，多路连接必须用 `Branch`；同名模型重复 `load` 不会从磁盘重载，改了文件要 `close` 后再 `load`。

接口及 C-Script 事件处理参考 Plexim 官方文档：[Simulation Scripts](https://docs.plexim.com/plecs/latest/scripting/)、[C-Scripts](https://docs.plexim.com/plecs/latest/c-scripts/)。模型按 PLECS 4.9 元件及示例文件格式生成，缺相变体在 PLECS 5.0.2 中验证运行，并以本机实际运行结果为准。
