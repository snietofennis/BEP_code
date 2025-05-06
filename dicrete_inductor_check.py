#!/usr/bin/env python3
"""
Linked transient simulations preserving capacitor initial condition,
with validation against a single continuous run.
"""
import matplotlib.pyplot as plt
import numpy as np
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_V, u_s, u_Ω, u_F, u_H, u_A

def configure_environment():
    # os.environ["PYSPICE_SIMULATOR"] = "ngspice"
    # If needed, adjust PATH externally or here:
    # os.environ["PATH"] += r";C:\\path\\to\\ngspice\\bin"
    return

V1 = 10
R1 = 3.5
C1 = 100
L1 = 100
C1_ic = 20
L1_ic = 0

def VRLC(V1=10 @ u_V, R1=3.5 @ u_Ω, C1=10 @ u_F, L1=0.5 @ u_H, last_current = 50 @ u_A):	
    circuit = Circuit("circuit")
    circuit.V("1","node1", circuit.gnd, V1)
    circuit.R("1", "node2", "node1", R1)
    circuit.L("1", "node3", "node2", L1, raw_spice = f'IC={float(last_current):.3f}')   # Adding an inductor
    circuit.C("1", "node3", circuit.gnd, C1)  # Adding a capacitor with initial condition
    # circuit.raw_spice = '.ic I(L1)=50m'
    return circuit


def run_subsim(last_condition, last_current):
    C1_ic = last_condition
    circuit  = VRLC(V1, R1, C1, L1, last_current)
    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    ## initial condition defined with simulator
    simulator.initial_condition(node3=C1_ic) #sets initial condition: voltage at node 1
    # simulator.initial_condition(l1=last_current) #sets initial condition: current at node 2
    analysis = simulator.transient(step_time=u_s(1), end_time=u_s(1000), use_initial_condition=True)
    print(simulator)
    return analysis


def forloop():
    time = np.array([])
    voltage = np.array([])
    current = np.array([])
    
    last_condition = C1_ic
    last_current = L1_ic
    analysis = run_subsim(last_condition, last_current)
    time = np.append(time, analysis.time)
    voltage = np.append(voltage, analysis['node3'])
    current = np.append(current, analysis['L1'])

    return time, voltage, current

    
def plotting(time, voltage, current):
    plt.plot(time, voltage, label="Node voltage before capacitor")
    plt.plot(time, current, label="Inductor current", linestyle='--')
    plt.legend()
    plt.show()





def main():
    # Setting stuff up
    configure_environment()
    setup_logging()

    
    time, voltage, current = forloop()
    plotting(time, voltage, current)

if __name__ == '__main__':
    main()
