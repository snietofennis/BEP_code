#!/usr/bin/env python3
"""
Modular PySpice simulation runner with plotting and easy circuit registration.
"""
import os
import argparse
import matplotlib.pyplot as plt
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_V, u_s, u_ms, u_us, u_ns, u_Ω, u_H, u_F, u_A
import numpy as np

# Ensure ngspice is on the PATH and set as simulator


C1_ic = 0
L1_ic = 0
step_size = 1 #s
total_time = 50 #s
add_plot_lines = False

number_of_steps = int(np.round(total_time/step_size)+1)

def configure_environment():
    # os.environ["PYSPICE_SIMULATOR"] = "ngspice"
    # # If needed, adjust PATH externally or here:
    # os.environ["PATH"] += r";C:\\path\\to\\ngspice\\bin"
    return


#RLC control

def RLC(R=1@u_Ω, L=3@u_H, C=1@u_F, V_input=10@u_V, kp=0.6, kd=0, ki=0, v_d=0, v_i=0, i=0,  last_current=0, v_input =0):


    circuit = Circuit('RLC with PID Feedback')
    
    circuit.PulseVoltageSource("V1", "input_base", circuit.gnd,
        initial_value=0@u_V, pulsed_value=V_input,
        delay_time=1@u_ms, rise_time=1@u_ns,
        fall_time=1@u_us, pulse_width=1@u_s, period=10e20@u_s)

    # RLC path (driven by your B-source on 'input_c')
    circuit.L(
        "1", "input_c", "node1", L,
        raw_spice = f"IC={float(last_current):.3f}"
    )
    circuit.R("1", "node1", "node2", R)
    circuit.C("1", "node2", circuit.gnd, C)

    # error tap = V(node2) – 5 V
    circuit.B(
        "2", "v_tap", circuit.gnd,
        voltage_expression = "V(node2)"
    )

    circuit.V("5","nodeint", circuit.gnd, ki*v_i)
    circuit.V("6","nodediff", circuit.gnd,kd*v_d)


    # PID feedback B-source (wrap the whole thing in braces {})
    expr = f"{{V(input_base) + {kp}*V(v_tap) + V(nodeint) + V(nodediff)}}"
    circuit.B("3", circuit.gnd, "input_c", voltage_expression=expr)
    # print(circuit)
    return circuit






def run_subsim(last_condition, last_current, step_size, v_d, v_i, i, v_input):
    C1_ic = last_condition
    circuit  = RLC(R=1@u_Ω, L=3@u_H, C=1@u_F, V_input=1@u_V, kd=1, ki=0.7, kp=0.6, v_d=v_d, v_i=v_i, i=1, last_current=last_current, v_input=v_input)
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    ## initial condition defined with simulator
    simulator.initial_condition(node2=C1_ic) #sets initial condition: voltage at node 1
    # simulator.initial_condition(l1=last_current) #sets initial condition: current at node 2
    analysis = simulator.transient(step_time=u_s(step_size/100), end_time=u_s(step_size), use_initial_condition=True)
    # print(simulator)
    return analysis


def forloop():
    time = np.array([])
    voltage = np.array([])
    current = np.array([])
    int_error = np.array([])
    dif_error = np.array([])
    control_times = np.array([])
    error = np.array([])
    for i in range(1, number_of_steps):
        if i == 1:
            last_condition = C1_ic
            last_current = L1_ic
            analysis = run_subsim(last_condition, last_current, step_size, 0, 0, i, 10)
            time = np.append(time, analysis.time)

            voltage = np.append(voltage, analysis['node2'])
            current = np.append(current, analysis['L1'])

            control_times = np.append(control_times, time[-1])

            #control 
            error = np.append(error, analysis['v_tap'][-1]-1)
            # current_at_control_time = np.append(current_at_control_time, current[-1])
            int_error = np.append(int_error, np.trapezoid(y = error, dx = step_size))
            # dif_current = np.append(dif_current, np.gradient(current_at_control_time, step_size)[-1])
            dif_error = np.append(dif_error, 0)

        else: 
            last_condition = analysis["node2"][-1]
            last_current = analysis["L1"][-1]    
            analysis = run_subsim(last_condition, last_current, step_size, dif_error[-1], int_error[-1], i, 0)
            time = np.append(time, np.array(np.array(analysis.time)+time[-1]))
            
            voltage = np.append(voltage, np.array(analysis['node2']))
            current = np.append(current, np.array(analysis['L1']))

            control_times = np.append(control_times, time[-1])

            #control 
            error = np.append(error, analysis['v_tap'][-1]-1)
            # current_at_control_time = np.append(current_at_control_time, current[-1])
            int_error = np.append(int_error, np.trapezoid(y = error, dx = step_size))
            # dif_current = np.append(dif_current, np.gradient(current_at_control_time, step_size)[-1])
            dif_error = np.append(dif_error, np.gradient(error, step_size)[-1])
            if i == 2:
                dif_error = np.append(dif_error, np.gradient(error, step_size)[-1])
        # print(int_current)
    return time, voltage, current, int_error, control_times, dif_error, error

def plot_error(control_times, error):
    """
    Plots the error signal against time.
    """
    plt.figure()
    plt.plot(control_times, error, label="Error Signal", color="red")
    plt.xlabel("Time [s]")
    plt.ylabel("Error [V]")
    plt.title("Error Signal vs Time")
    plt.legend()
    plt.grid(True)
    plt.show()

def main():
    configure_environment()
    setup_logging()

    forloop()
    time, voltage, current, int_error, control_times, dif_error, error = forloop()
    # plot_int_output(analysis, circuit, node_controlled='node_int')
    plot_error(control_times, error)
    plot_error(time, voltage)
    # plot_node_voltage(circuit, analysis)


if __name__ == '__main__':
    main()
