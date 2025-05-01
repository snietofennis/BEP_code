#!/usr/bin/env python3
"""
Linked transient simulations preserving capacitor initial condition,
with validation against a single continuous run.
"""
import matplotlib.pyplot as plt
import numpy as np
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_V, u_s, u_Ω, u_F

def configure_environment():
    # os.environ["PYSPICE_SIMULATOR"] = "ngspice"
    # If needed, adjust PATH externally or here:
    # os.environ["PATH"] += r";C:\\path\\to\\ngspice\\bin"
    return

V1 = 10
R1 = 3.5
C1 = 100
C1_ic = 20
def VRC(V1=10 @ u_V, R1=3.5 @ u_Ω, C1=100 @ u_F):
    circuit = Circuit("circuit")
    circuit.V("1","node2", circuit.gnd, V1)
    circuit.R("1", "node1", "node2", R1)
    circuit.C("1", "node1", circuit.gnd, C1)

    return circuit


def run_subsim(last_condition):
    C1_ic = last_condition
    circuit  = VRC(V1, R1, C1)
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    ## initial condition defined with simulator
    simulator.initial_condition(node1=C1_ic)            #sets initial condition: voltage at node 1
    analysis = simulator.transient(step_time=u_s(1), end_time=u_s(100))
    
    return analysis


def forloop():
    time = np.array([])
    voltage = np.array([])
    for i in range(1, 11):
        if i == 1:
            last_condition = C1_ic
            analysis = run_subsim(last_condition)
            time = np.append(time, analysis.time)
            voltage = np.append(voltage, analysis['node1'])
        else: 
            last_condition = analysis["node1"][-1]    
            analysis = run_subsim(last_condition)
            time = np.append(time, np.array(np.array(analysis.time)+time[-1]))
            voltage = np.append(voltage, np.array(analysis['node1']))
    
    return time, voltage

    
def plotting(time, voltage):
    plt.plot(time, voltage, label="Node voltage before capacitor")
    plt.legend()
    
    # Add vertical lines at the start of each subsimulation
    for i in range(1, 11):
        plt.axvline(x=i * 100, color='red', linestyle='--', label=f'Subsim {i}' if i == 1 else None)
    

    plt.show()





def main():
    # Setting stuff up
    configure_environment()
    setup_logging()

    
    time, voltage = forloop()
    plotting(time, voltage)

if __name__ == '__main__':
    main()
