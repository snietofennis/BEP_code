import os
import argparse
import matplotlib.pyplot as plt
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit, SubCircuitFactory
from PySpice.Unit import *


# measured has to be a component so that we can measure the current through it
# i_out is the integrated current output, but is given as a voltage
circuit.B('1', 'name_measured', circuit.gnd, voltage_expression='I(component)')


circuit.raw_spice += f"""
A2 mname_measured idt_name i_model
.model i_model int(gain=1 in_offset=0 
+ out_lower_limit=-1e12 out_upper_limit=1e3
+ limit_range=1e-9 out_ic=0)
R3 i_out 0 1Meg
"""
        
circuit.B('2', circuit.gnd, circuit.gnd, current_expression='V(idt_name) / R3')

