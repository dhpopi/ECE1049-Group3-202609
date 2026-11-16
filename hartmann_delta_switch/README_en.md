# Hartmann Three-Phase Delta-Switch Rectifier: Switched-Level PLECS Reproduction

[中文](README_zh.md) | [English](README_en.md)

This directory contains a switched-level model that actually runs in **PLECS Standalone**; it is not an averaged model, and PLECS is not replaced by a Python solver. The model file is in the PLECS 4.9 format: the three-phase baselines in `results/` were produced with PLECS 4.9, while the phase-loss cases were run with PLECS 5.0.2 on this machine (5.0 opens 4.9 models directly, no conversion needed).

## Open and run

1. Open `Hartmann_DeltaSwitch.plecs` in PLECS.
2. Start the simulation from the **Simulation** menu; the default run is 0.12 s.
3. Double-click `Main_Waveforms`: grid voltages, input currents, dc-bus voltage, current reference (in that order).
4. Double-click `MOSFET_Gates`: signal order is `s12, s21, s23, s32, s13, s31`.
5. Edit parameters under **Simulation Parameters → Initialization**. The complete initialization code is embedded in the model; no external MATLAB file is required. `parameters.m` is a readable copy of that code, and editing the copy does not change the model.

The default operating point is that of paper Fig.8(a): **800 Hz, 115 V rms phase voltage, 400 V, 5 kW**. Set `fline=400` for the 400 Hz case, and `Vinit=280` to test recovery from a discharged bus.

The phase-loss case uses a separately generated variant, `Hartmann_DeltaSwitch_PhaseLoss.plecs`; see "Phase-loss operation" below.

## Correspondence with the paper

Source: Hartmann, Miniboeck, Ertl, Kolar, *A Three-Phase Delta Switch Rectifier for Use in Modern Aircraft*, IEEE Transactions on Industrial Electronics, 59(9), 3635–3647, 2012, DOI: 10.1109/TIE.2011.2158770. The PDF is one level above this directory.

| Model content | Paper | Implementation |
|---|---|---|
| Three-phase source, boost inductors, six-diode bridge, dc capacitor | Fig.1(b) | Real switching circuit built from native electrical components |
| Delta bidirectional switches | Fig.2(a) | Three common-source back-to-back MOSFET pairs (six devices), body diodes included |
| Current reference | Fig.6 | `i_ref[k] = Gref * v_grid[k]` |
| P current control and mains-voltage feedforward | Fig.6 | `vr[k] = v_grid[k] - Kcurrent*(i_ref[k]-i[k])` |
| Star–delta transformation | Eqs. (12)–(14) | `vr_ij = vr[i]-vr[j]` |
| Triangular-carrier PWM | Fig.7, Eqs. (15)–(17) | Single 0–1 carrier; compare `carrier > vr_ij/Vdc` |
| Sector clamping | Table III | When two phase voltages share a sign, both MOSFETs of that bidirectional branch are off; the reverse device is permanently on, the forward device is PWM-modulated |
| Outer loop | Fig.6, Sec. VI | PI controller outputting a conductance, with conductance limit and integral anti-windup |
| Phase-loss operation | Fig.8(b), Fig.14 | See below: with one phase open the controller keeps working in two-phase mode without modification |

The six-sector Table III control reduces to a sign test on the three phase voltages, so the current controller itself never has to change. `Hartmann_Control` is an editable C-Script; the code is also stored as `controller_*.c` for reading. The triangular carrier is a native PLECS block; both the PWM comparisons and the phase-voltage zero crossings are registered as zero-crossing events, and the gates are updated only on major solver steps.

## Parameters and explicit additional assumptions

| Parameter | Value | Source / note |
|---|---:|---|
| Phase voltage rms `Vph` | 115 V | Paper Sec. IV; line-to-line ≈ 199.19 V rms |
| Mains frequency `fline` | 800 Hz | Default matches Fig.8(a); 400 Hz also verified |
| Switching frequency `fsw` | 72 kHz | Paper Sec. IV |
| Boost inductance per phase `Lboost` | 330 µH | Fig.8 simulation value; Table VI prototype is 326 µH |
| Output capacitance `Cdc` | 1476 µF | Table VI: 18 × 82 µF in parallel |
| Output reference `Vref` | 400 V | Paper |
| Load resistance `Rload` | 32 Ω | Resistive load chosen for 400 V / 5 kW |
| Series resistance per phase `RL` | 20 mΩ | Additional model assumption |
| Switch / diode on-resistance | 1 mΩ each | Numerical assumption, not the datasheet on-state values |
| Diode forward voltage | 0 V | Idealized power-stage assumption |
| Initial capacitor voltage `Vinit` | 400 V | Precharged default; initial inductor currents are zero |
| Current-loop gain `Kcurrent` | 8.2938 V/A | Set from `2*pi*4000*Lboost` |
| Voltage-loop `Kpv` | 0.00264417 S/V | 20 Hz natural frequency, damping ≈ 0.707 |
| Voltage-loop `Kiv` | 0.234990 S/(V·s) | Companion to the above |
| Conductance limit `Gmax` | 0.25 S | Additional saturation limit of this model |

**The controller is not a device-level copy of the hardware gains.** The paper specifies a P current controller with `kp = 0.25` and a bandwidth of about 4 kHz, but does not give enough sensor/modulator scaling to interpret 0.25 directly as a V/A gain in SI units. The gains here are derived in physical units and the formulas are stated. For the outer loop the paper states about 20 Hz bandwidth but does not publish the full PI values; a 20 Hz natural frequency is used as an initial design and no claim is made about reproducing the hardware closed-loop bandwidth.

The native `ThreePhaseVoltageSource` takes its phase argument in radians; `pi/2` makes phase A start at its cosine peak. The three-phase neutral is tied to the reference ground and the dc side is left floating.

## Checks that have been run

Numerical values are in `results/verification.json`, waveforms in the matching PNGs, uniformly sampled data in the NPZ files, and the last four line cycles in the CSVs. All results come from PLECS on this machine.

| Case | Mean Vdc | Output power | Irms per phase | PF per phase | Current THD (orders 2–40) |
|---|---:|---:|---:|---:|---:|
| 800 Hz / 5 kW | ≈ 400.000 V | ≈ 5000.0 W | ≈ 14.749 A | ≈ 0.98528 | ≈ 3.80% |
| 400 Hz / 5 kW | ≈ 400.000 V | ≈ 5000.0 W | ≈ 14.601 A | ≈ 0.99527 | ≈ 2.30% |
| 800 Hz, bus initially at 280 V | ≈ 400.000 V steady state | ≈ 5000.0 W steady state | ≈ 14.749 A | ≈ 0.98528 | ≈ 3.80% |

The 280 V recovery case peaks at about 406.58 V on the bus with a transient phase current of about 40.79 A. This is a closed-loop recovery test; it does **not** include inrush/precharge hardware starting from zero volts.

The script also checks the three-phase current sum, the sector clamping, finite values, output regulation and power. **A note on the convergence check:** the two runs lower `MaxStep` from `1/(72k*10)` to `1/(72k*40)`, but their `ΔVdc`, `ΔP` and `ΔIrms` are only 5e-11 V, 1e-9 W and 2e-10 A, i.e. the step-size parameter never binds (the step is set by the 0.5 µs output instants and by error control). This is therefore **not a valid convergence proof**; it needs a comparison that really changes the step size (a fixed-step solver, or much coarser output sampling).

THD is computed over the last eight complete line cycles, resampled uniformly at 2 MHz, using harmonics 2–40 of the line frequency and normalized to the fundamental, so switching harmonics around 72 kHz are excluded. PF is the true time-domain power divided by Vrms × Irms and does include the current ripple. Do not conflate the two metrics.

At 800 Hz the P-type current loop shows a visible fundamental tracking error and phase shift, which explains the PF being lower than in the 400 Hz case; no resonant control or current-derivative feedforward was added, to keep the paper's control structure.

## Phase-loss operation (Fig.8(b) / Fig.14)

The variant model `Hartmann_DeltaSwitch_PhaseLoss.plecs` is generated in one shot by:

```text
python build_model.py --phase-loss
```

Only three things are added relative to the baseline; **the controller and the rest of the power stage are unchanged**:

| Added element | Purpose |
|---|---|
| `K1` | Ideal switch in series with grid phase A, `s_init=1`, opened at `t_loss` |
| `C_loss` + `R_loss` | 100 nF + 10 Ω across the break, standing in for the stray capacitance across the interrupting contact and providing a path plus damping for the disconnected phase current; with 3.4 µF that phase still carried about 3.8 A at 800 Hz, hence 100 nF |
| `LossStep` | Step block (1→0 at `t_loss`) driving the gate of `K1` |

`t_loss` is a new model variable (default 0.06 s) that can be overridden through `ModelVars`. The voltage measurement `v1` stays on the grid side of the switch, so the controller sees a normal three-phase voltage before and after the loss — which is exactly the premise of the paper's "controller structure unchanged" claim.

Running and plotting (the script calls `plecs.close()` after every run, so no model is left open in PLECS):

```text
python run_phase_loss.py --pnom 3000 --tloss 0.06    --tag phase_loss_3kW
python run_phase_loss.py --pnom 3000 --tloss 0.00085 --tag phase_loss_3kW_papertiming
python run_phase_loss.py --pnom 5000 --tloss 0.06    --tag phase_loss_5kW
python run_phase_loss.py --pnom 5000 --tloss 0.06 --gmax 0.5 --tag phase_loss_5kW_gmax05
```

Results at 800 Hz (post-fault window: last eight line cycles):

| Case | i1 (rms) | i2 / i3 (rms) | THD | Mean Vdc | Actual power | Limit |
|---|---:|---:|---:|---:|---:|---|
| 3 kW, loss at 60 ms | 0.43 A | 19.8 / 19.7 A | 23.7% | 400.1 V | 3002 W | not hit |
| 3 kW, loss at 0.85 ms (paper timing) | 0.41 A | 18.1 / 18.0 A | 21.9% | 399.9 V | 2999 W | not hit |
| 5 kW, loss at 60 ms, Gmax=0.25 | 0.45 A | 27.3 / 27.2 A | 27.0% | 340.5 V (still falling) | 3624 W | hit (Gref=0.25 S) |
| 5 kW, loss at 60 ms, Gmax=0.5 | 0.48 A | 45.2 / 45.1 A | 17.7% | 337.5 V | 3560 W | hit (Gref=0.5 S) |

Observations:

1. **Two-phase operation works at 3 kW.** After the loss `i1 ≈ 0`, the two remaining phases carry about 18–20 A each, the bus returns to 400 V and the full 3 kW is maintained. With the loss at 60 ms the bus dips to about 384.6 V and recovers in roughly 50 ms. Losing the phase at 0.85 ms (the paper's Fig.8(b) timing) gives essentially the same steady state.
2. **Two-phase operation does not work at 5 kW.** With the default Gmax the outer loop saturates and the bus falls to about 340 V. With Gmax relaxed to 0.5 S, `Gref` saturates at 0.5 S and the currents rise to 45 A while the bus stays at about 337 V. The limit is therefore **modulator duty-cycle saturation**, not the conductance limit added by this model: the maximum voltage the converter can synthesize on two phases is simply not enough.
3. This is consistent with the paper, which demonstrates two-phase operation at 3 kW (Fig.8(b)) and 2.25 kW (Fig.14) and never at 5 kW.
4. In two-phase operation `i2 = -i3` must hold at every instant, so the per-phase power factors are necessarily asymmetric (about 0.97 and about 0.4). That is a property of the topology, not a model error.

Limitations: without an EMI filter the ring-down of the disconnected phase inductor current seen in Fig.14(b) does not appear; the additional "clamp S12 after detecting the loss" logic is not implemented; and the current loop is still P-type (PF 0.985), so the absolute two-phase power limit may be slightly conservative compared with the hardware.

## Scope of this version

Covered: the power topology, the paper's PWM/clamping control structure, closed-loop dc-bus regulation, normal three-phase steady state, bus recovery, and **two-phase operation after a phase loss**.

Not covered: EMI filter, parasitic/common-mode paths, real device losses, nonlinear magnetics, precharge resistor/diode/thyristor, and the phase-loss detection and clamping logic. The model therefore cannot be used to claim a reproduction of the paper's efficiency, common-mode EMI, hardware start-up, or complete phase-loss fault ride-through. The 400 Hz THD happens to be close to the paper's value, but this is still not a full hardware reproduction: filter, power level and loss conditions differ.

## Re-running the automated verification or rebuilding

Open PLECS and enable the local RPC port 1080 in Preferences, then run in this directory:

```text
python run_verify.py
```

This needs Python with `numpy` and `matplotlib`; XML-RPC is from the standard library. Opening and running the model by hand does not require Python or RPC.

```text
python build_model.py                # regenerate baseline plus parameter/controller copies
python build_model.py --phase-loss   # generate the phase-loss variant (baseline untouched)
```

`build_model.py` overwrites generated files of the same name in this directory, so save manual schematic edits first. `--phase-loss` writes only `Hartmann_DeltaSwitch_PhaseLoss.plecs` and leaves the baseline, `parameters.m` and `controller_*.c` alone. The automated verification never changes the initialization parameters; it only overrides run options for each case.

Two PLECS conventions worth knowing (both were hit while debugging): a terminal may appear in only one `Connection`, so fan-out must use `Branch`; and loading a model with the same name again does not reload it from disk, so `close` it before `load` after editing the file.

The scripting interface and C-Script event handling follow the Plexim documentation: [Simulation Scripts](https://docs.plexim.com/plecs/latest/scripting/), [C-Scripts](https://docs.plexim.com/plecs/latest/c-scripts/). The model was generated against the PLECS 4.9 component and example file formats, the phase-loss variant was verified in PLECS 5.0.2, and all statements are based on actual runs on this machine.
