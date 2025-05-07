#!/usr/bin/env python3
"""
Modular PySpice simulation runner with plotting and easy circuit registration.
"""
import os
import argparse
import matplotlib.pyplot as plt
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import *

# Ensure ngspice is on the PATH and set as simulator


def configure_environment():
    # os.environ["PYSPICE_SIMULATOR"] = "ngspice"
    # # If needed, adjust PATH externally or here:
    # os.environ["PATH"] += r";C:\\path\\to\\ngspice\\bin"
    return

# --- Circuit Builders ---a
# Each builder returns a PySpice Circuit object




#RLC control

def RLC(R=1@u_Ω, L=3@u_H, C=1@u_F, V_input=1@u_V, Kd=3, Ki=0.7):
    circuit = Circuit('RLC with Integral + Derivative Feedback')

    # Base input pulse signal
    circuit.PulseVoltageSource("V1", "input_base", circuit.gnd,
        initial_value=0@u_V, pulsed_value=V_input,
        delay_time=1@u_ms, rise_time=1@u_ns,
        fall_time=1@u_us, pulse_width=1@u_s, period=1@u_Ts)

    # RLC path (driven by feedback-controlled input_c)
    circuit.L(1, "input_c", "node1", L)
    circuit.R(1, "node1", "node2", R)
    circuit.C(1, "node2", circuit.gnd, C)

    # Tap V(node2)  = Error  
    circuit.B(2, "v_tap", circuit.gnd, voltage_expression="V(node2)-5")
    # circuit.raw_spice += """B2 v_tap 0 V=cond(time>2, 0, 1)"""


    #P
    circuit.B("P", 'v_tap', 'v_P', voltage_expression="0.6*V(v_tap)")

    # Differentiator (D-control)
    circuit.raw_spice += f"""
A1 v_tap d_out d_model
.model d_model d_dt(gain={Kd} out_offset=0 
+ out_lower_limit=-1e12 out_upper_limit=1e6 
+ limit_range=1e-9)
R2 d_out 0 1Meg
"""

    # Integrator (I-control)
    circuit.raw_spice += f"""
A2 v_tap i_out i_model
.model i_model int(gain={Ki} in_offset=0 
+ out_lower_limit=-1e12 out_upper_limit=1e3
+ limit_range=1e-9 out_ic=0)
R3 i_out 0 1Meg
"""

    # DI action
    circuit.B(3, circuit.gnd, "input_c",
        voltage_expression=" V(input_base)  + V(v_P) + V(d_out) + V(i_out)")
    

    return circuit






# Registry of available circuits
CIRCUIT_REGISTRY = {
    'RLC': RLC
    # add new circuits here, e.g. 'rc_filter': build_rc_filter
}

# --- Simulation and Plotting ---

def run_transient(circuit, step_time=0.1 @ u_s, end_time=50 @ u_s):
    simulator = circuit.simulator()
    simulator.options(max_step_time=step_time, min_step_time=step_time)
    return simulator.transient(step_time=step_time, end_time=end_time)


def plot_node_voltage(circuit, analysis, node_control='input_c',node_controlled='node2', node_error='v_tap'):
    time = analysis.time
    voltage_control = analysis[node_control]
    voltage_controlled = analysis[node_controlled]
    voltage_error = analysis[node_error]
    plt.figure()
    plt.plot(time, voltage_control, label = "Controller Output", zorder = 5)
    plt.plot(time, voltage_controlled, label = "System Output (Capacitor)", zorder = 10)
    plt.plot(time, voltage_error, label = "Error", zorder = 1)
    plt.xlabel('Time [s]')
    plt.ylabel('Voltage [V]')
    plt.title(f"{circuit.title} - Node '{node_controlled}' Voltage")
    plt.legend()
  
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# --- CLI ---

def main():
    configure_environment()
    setup_logging()

    circuit = RLC()
    # Convert step and end to units
    step_time = 0.1
    end_time = 20

    analysis = run_transient(circuit)


    plot_node_voltage(circuit, analysis)


if __name__ == '__main__':
    main()
