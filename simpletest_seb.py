#!/usr/bin/env python3
"""
Modular PySpice simulation runner with plotting and easy circuit registration.
"""
import os
import argparse
import matplotlib.pyplot as plt
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_V, u_s, u_Ω, u_F, u_H

# Ensure ngspice is on the PATH and set as simulator
def configure_environment():
    # os.environ["PYSPICE_SIMULATOR"] = "ngspice"
    # If needed, adjust PATH externally or here:
    # os.environ["PATH"] += r";C:\\path\\to\\ngspice\\bin"
    return

# --- Circuit Builders ---
# Each builder returns a PySpice Circuit object

def build_simple_test(V_input=10 @ u_V, R_value=1 @ u_Ω):
    """
    Simple pulse source driving a resistor to ground, matching the user's example.
    """
    circuit = Circuit('simple test')
    circuit.PulseVoltageSource(
        name='V1', node_plus="input", node_minus=circuit.gnd,
        initial_value=0 @ u_V,
        pulsed_value=V_input,
        delay_time=1 @ u_s,
        rise_time=1e-9 @ u_s,
        fall_time=1 @ u_s,
        pulse_width=1e-9 @ u_s,
        period=1e9 @ u_s
    )
    circuit.PulseVoltageSource(
        name='V2', node_plus='1', node_minus='input',
        initial_value=0 @ u_V,
        pulsed_value=V_input,
        delay_time=5 @ u_s,
        rise_time=1e-9 @ u_s,
        fall_time=1 @ u_s,
        pulse_width=1e-9 @ u_s,
        period=1e9 @ u_s
    )    
    circuit.R(1,'1', circuit.gnd, R_value) #voeg toe de namen
    

    return circuit


def rl(V_input=10 @ u_V, R_value=1 @ u_Ω,inductance = 3 @ u_H):
    circuit = Circuit('RL')

    circuit.PulseVoltageSource(
        name='V1', node_plus="input", node_minus=circuit.gnd,
        initial_value=0 @ u_V,
        pulsed_value=V_input,
        delay_time=1 @ u_s,
        rise_time=1e-9 @ u_s,
        fall_time=1 @ u_s,
        pulse_width=1e-9 @ u_s,
        period=1e9 @ u_s
    )

    circuit.L(2,2, 'input', inductance)
    
    circuit.R(1,circuit.gnd, 2, R_value) #voeg toe de namen
    return circuit

# Registry of available circuits
CIRCUIT_REGISTRY = {
    'simple_test': build_simple_test,
    'RL' : rl
    # add new circuits here, e.g. 'rc_filter': build_rc_filter
}

# --- Simulation and Plotting ---

def run_transient(circuit, step_time=1 @ u_s, end_time=10 @ u_s):
    simulator = circuit.simulator()
    simulator.options(max_step_time=step_time, min_step_time=step_time)
    return simulator.transient(step_time=step_time, end_time=end_time)


def plot_node_voltage(circuit, analysis, node='2'):
    time = analysis.time
    voltage = analysis[node]
    plt.figure()
    plt.plot(time, voltage)
    plt.xlabel('Time [s]')
    plt.ylabel('Voltage [V]')
    plt.title(f"{circuit.title} - Node '{node}' Voltage")
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# --- CLI ---

def main():
    configure_environment()
    setup_logging()

    circuit = rl()
    # Convert step and end to units
    step_time = 1
    end_time = 10

    analysis = run_transient(circuit, step_time=step_time, end_time=end_time)


    plot_node_voltage(circuit, analysis)


if __name__ == '__main__':
    main()
