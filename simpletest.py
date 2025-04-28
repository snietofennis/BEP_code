# import os
# os.environ["PATH"] += r";C:\\Users\\kmeli\\BEPCode\\TestCode\\PySpicePlay\\ngspice-44.2_64\\Spice64\\bin"
# os.environ["PYSPICE_SIMULATOR"] = "ngspice"


import PySpice.Logging.Logging as Logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_V, u_kΩ
import numpy as np
# Enable PySpice logging (optional)
Logging.setup_logging()


circuit = Circuit('simple test')
V_input = 10.0

circuit.PulseVoltageSource(1, "input", circuit.gnd, 
                               initial_value=0, pulsed_value=V_input, 
                               delay_time=1, rise_time=1e-9, fall_time=1, 
                               pulse_width=1e-9, period=1e9)

circuit.R(1,'input',circuit.gnd, 1)

simulator = circuit.simulator()
simulator.options(max_step_time=1, min_step_time=1)
analysis = simulator.transient(step_time=1, end_time=10)

time = analysis.time
voltage = np.array(analysis['input'])

print("Time (s):", time)
print("Voltage (V):", voltage)

# 3) Print the voltage at node “1”
voltage = (analysis.nodes['1'])
print(f"Available analysis nodes: {analysis.nodes.keys()}")
# print(f"Node 1 voltage: {voltage:.2f} V")
