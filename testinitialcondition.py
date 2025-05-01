import matplotlib.pyplot as plt
import numpy as np
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_ms, u_s, u_V, u_Ω, u_F, u_H

V1 = 10
R1 = 3.5
C1 = 100
C1_ic = 20

circuit = Circuit("circuit")

circuit.V("1","node2", circuit.gnd, V1)
circuit.R("1", "node1", "node2", R1)
circuit.C("1", "node1", circuit.gnd, C1)

simulator = circuit.simulator(temperature=25, nominal_temperature=25)
## initial condition defined with simulator
simulator.initial_condition(node1=C1_ic)
analysis = simulator.transient(step_time=u_s(1), end_time=u_s(1000))

print(simulator)

plt.plot(analysis.time, analysis["node1"], label="node1")
plt.plot(analysis.time, analysis["node2"], label="node2")
plt.legend()
plt.show()