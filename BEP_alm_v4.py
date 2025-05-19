import os
import argparse
import matplotlib.pyplot as plt
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_F, u_H, u_Ω, u_V, u_A, u_s, u_ms, u_us, u_Ts, u_ns, u_mΩ
import numpy as np
from scipy.integrate import cumulative_trapezoid

# Choose type of control
control_loan_desposit = False
control_debt_equity = True
control_tier_1 = False

def configure_environment():
    # os.environ["PYSPICE_SIMULATOR"] = "ngspice"
    # # If needed, adjust PATH externally or here:
    # os.environ["PATH"] += r";C:\\path\\to\\ngspice\\bin"
    return

def add_integrator(circuit, name, input_inductor):
        """Adds an integrator block to the circuit."""
        circuit.B(f'{name}_input', f'{name}_measured', circuit.gnd, voltage_expression=f'I({input_inductor})')
        circuit.raw_spice += f"""
A_{name} {name}_measured {name}_idt i_model
.model i_model int(gain=1 in_offset=0 
+ out_lower_limit=-1e100 out_upper_limit=1e100
+ limit_range=1e-9 out_ic=0)
R_{name} {name}_idt 0 1Meg
"""
        circuit.B(f'{name}_output', circuit.gnd, circuit.gnd, current_expression=f'V({name}_idt)')

def ALM():
    circuit = Circuit('ALM - Asset Liability Management')


    # ─────────────── Parameters ───────────────
    circuit.parameter('Kp',       0.015)       # PID-Kp
    circuit.parameter('Ki',       0.001)       # PID-Ki
    circuit.parameter('Kd',       0.0)         # PID-Kd
    circuit.parameter('tau_d',    1.0)         # derivative filter time constant
    circuit.parameter('q_L0',     48)          # initial Loan balance
    circuit.parameter('q_C0',     20)          # initial Current Acct balance
    circuit.parameter('q_S0',     20)          # initial Savings Acct balance
    circuit.parameter('q_E0',     20)          # initial Equity
    circuit.parameter('IC_Goods', 100e-3)      # initial production constant
    circuit.parameter('IC_Income',100e-3)      # initial income current

    # ─────────────── Inductors (economic flows) ───────────────
    

    circuit.L('Investment',        'N005', circuit.gnd,       0.5   @ u_H) 
    circuit.L('Aggregate_Demand',  'N013', circuit.gnd,       1.5   @ u_H)
    circuit.L('Aggregate_Supply',  'N014', 'N013',            1     @ u_H)
    circuit.L('H_Interest',        'N008', 'N007',           10    @ u_H)
    circuit.L('F_Interest',        circuit.gnd, 'N010',      10    @ u_H)
    circuit.L('NII',               'N009', circuit.gnd,       1     @ u_H)
    circuit.L('Savings',           'N007', 'N001',            1     @ u_H)
    circuit.L('Revenue',           'N012', circuit.gnd,       1     @ u_H)
    circuit.L('Current_Deposits',  'N002', 'N003',           0.9   @ u_H)
    circuit.L('Savings_Deposits',  'N006', 'Incentive_to_Save',2    @ u_H)
    circuit.L('Loans',             'Incentive_to_Borrow','N004',1  @ u_H)
    circuit.L('Wage',              circuit.gnd,'N011',      10    @ u_H)
    circuit.L('Income',            'N011', 'N007',            1.5   @ u_H, raw_spice = 'IC={IC_Income}') # initial income current
    circuit.L('Consumption',       'N007', 'N012',            1     @ u_H, raw_spice = 'IC={IC_Income}') # initial income current


    # ─────────────── Ideal coupling ──────────────────

    circuit.K('H1', 'Consumption', 'Aggregate_Demand',  -0.2)
    circuit.K('H2', 'Income',      'Savings', -0.8)

    circuit.K('F1', 'Aggregate_Supply', 'Wage', -0.6)
    circuit.K('F2', 'Revenue',      'Investment', -0.4)


    # ─────────────── Capacitors (economic storage) ───────────────
    circuit.C('Inventory',         circuit.gnd, 'P001',         70    @ u_F)
    circuit.C('C4',                'N001', circuit.gnd,         0.5   @ u_F)
    circuit.C('C5',                'N001', circuit.gnd,         1     @ u_F)
    circuit.C('C6',                'P002', circuit.gnd,         3     @ u_F)
    circuit.C('C1',                circuit.gnd, 'P003',         70    @ u_F)

    # ─────────────── Resistors (economic friction) ───────────────
    circuit.R(3,                   'N014', 'P001',             0.05  @ u_Ω)
    circuit.R(4,                   'N001', 'N002',             0.5   @ u_Ω)
    circuit.R(6,                   'N006', 'N001',             2     @ u_Ω)
    circuit.R(7,                   'N004', 'N005',             0.4   @ u_Ω)
    circuit.R(10,                  'N005', 'P002',             0.1   @ u_Ω)
    circuit.R(16,                  circuit.gnd, 'N014',        10    @ u_Ω)
    circuit.R(1,                   'N013', 'P003',             0.01  @ u_Ω)
    # circuit.R('Aggregate_Supply_Rser','N014','N013',         10e100  @ u_Ω)  # Rser=1µ
    # circuit.R('F_Interest_Rser',   circuit.gnd,'N010',        10e100  @ u_Ω)  # Rser=1µ
    # circuit.R('Revenue_Rser',      'N012', circuit.gnd,       10e100  @ u_Ω)  # Rser=1µ
    # circuit.R('Wage_Rser',         circuit.gnd,'N011',      10e100  @ u_Ω)  # Rser=1µ



    # ─────────────── Behavioral Sources (financial equations) ───────────────
    circuit.B('Interest_Expense',        'N009', 'N008',
                current_expression='I(BSavings_Account_Balance)*I(BSavings_Interest_Rate)/120')
    circuit.B('Interest_Income',         'N010', 'N009',
                current_expression='I(BLoan_Balance)*I(BLoan_Interest_Rate)/120')
    
    circuit.B('Incentive_to_Save',       'Incentive_to_Save', circuit.gnd,
                voltage_expression='(-8*(I(BSavings_Interest_Rate)-I(BT_rate)+0.02))') #IF(time<0.02,0,
    circuit.B('Incentive_to_Borrow',     'Incentive_to_Borrow', circuit.gnd,
                voltage_expression='-3*(I(BLoan_Interest_Rate)-I(BT_rate)-0.020)') #IF(time<0.02,0,

    circuit.B('Incentive_to_Deposit',    'N003', circuit.gnd,
                voltage_expression='0')


                #----------------Dashboard--------------------


    # ------------------ Integrators -------------------

############# INTEGRATING INVESTMENT
    
    add_integrator(circuit, 'Investment', 'LInvestment')

    circuit.B('Production',              circuit.gnd, 'N014',
                current_expression='{IC_Goods} + I(BInvestment_output)*1/120') 

############# INTEGRATING Current Deposits

    add_integrator(circuit, 'Current_Deposits', 'LCurrent_Deposits')

    circuit.B('Current_Account_Balance', circuit.gnd, circuit.gnd,
                current_expression='{q_C0} + I(BCurrent_Deposits_output)') #IF(time<0.0001,0, en #Integrate inductor


############# INTEGRATING Savings Deposits

    add_integrator(circuit, 'Savings_Deposits', 'LSavings_Deposits')

    circuit.B('Savings_Account_Balance', circuit.gnd, circuit.gnd,
                current_expression='{q_S0} + I(BSavings_Deposits_output)') 


############# INTEGRATING Loans

    add_integrator(circuit, 'Loans', 'LLoans')

    circuit.B('Loan_Balance',            circuit.gnd, circuit.gnd,
                current_expression='{q_L0} + I(BLoans_output)')

    
############# INTEGRATING NII

    add_integrator(circuit, 'NII', 'LNII')

    circuit.B('Retained_Earnings',       circuit.gnd, circuit.gnd,
                current_expression='I(BNII_output)') #Integrate inductor



############# INTEGRATING Spread_Err2

    

    # circuit.B('Spread',                  circuit.gnd, circuit.gnd,
    #             current_expression='0.005') # done with if statements to switch between control

    # circuit.B('Spread',                  circuit.gnd, circuit.gnd,
    #             current_expression='0.005-(0.1*I(Spread_Err2)+{Ki}*idt(I(Spread_Err2)))') # IF(time<0.001,0, en PI Current expression, integrate


    # ------------------ If Statements -------------------


#make equivalent pulse, goes from 0.02 to 0.03 at 120s
    circuit.PulseVoltageSource("T_rate_input", "node_t_rate", circuit.gnd,
        initial_value=0.02, pulsed_value=0.03,
        delay_time=120@u_s, rise_time=1@u_ns,
        fall_time=1@u_us, pulse_width=1e100@u_s, period=1@u_Ts)
    circuit.B('T_rate',                  circuit.gnd, circuit.gnd,
                current_expression='V(node_t_rate)') 


########
    # circuit.B('FTP_Rate1',               circuit.gnd, circuit.gnd,
    #             current_expression='0.025') # this is done no with if statements to switch between control

    # circuit.B('Spread1',                 circuit.gnd, circuit.gnd,
    #             current_expression='0.005') # done with if statements to switch between control
    


    

    circuit.B('Loan_Interest_Rate',      circuit.gnd, circuit.gnd,
            current_expression='I(BFTP_Rate)+I(BSpread)')

    circuit.B('Savings_Interest_Rate',   circuit.gnd, circuit.gnd,
                current_expression='I(BFTP_Rate)-I(BSpread)')
    
    circuit.B('Loan-to-Deposit_Ratio1',  circuit.gnd, circuit.gnd,
                current_expression='I(BLoan_Balance)/I(BTotal_Liabilities)')




######################## Add control done with if statements
    # circuit.B('Spread3',                 circuit.gnd, circuit.gnd,
    #             current_expression='0.005+(0.05*I(Spread_Err3)+0.00*idt(I(Spread_Err3)))')     # Integrate current expression
#########################   
    # circuit.B('Spread3',                 circuit.gnd, circuit.gnd,
    #             current_expression='0.005+(0.05*I(BSpread_Err3))')
##########




###### add control

    # circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
    #             current_expression='0.025') #0.025-(2*0.06*I(BFTP_Err2)+1.5*0.003*I(BFTP_Err2_output))


    # circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
    #             current_expression='0.025-(2*0.06*I(FTP_Err2)+1.5*0.003*idt(I(FTP_Err2)))') # Integrate current expression
    


    # ------------------ Normal behavioral probs -------------------

    circuit.B('Total_Liabilities',       circuit.gnd, circuit.gnd,
                current_expression='I(BCurrent_Account_Balance)+I(BSavings_Account_Balance)')
    circuit.B('Initial_Equity',          circuit.gnd, circuit.gnd,
                current_expression='({q_E0})') #IF(time<0.0001,0,
    circuit.B('Total_Equity',            circuit.gnd, circuit.gnd,
                current_expression='I(BRetained_Earnings)+I(BInitial_Equity)')
    circuit.B('Cash_Reserves',           circuit.gnd, circuit.gnd,
                current_expression='I(BTotal_Liabilities)+I(BTotal_Equity)-I(BLoan_Balance)')
    circuit.B('Total_Assets',            circuit.gnd, circuit.gnd,
                current_expression='I(BLoan_Balance)+I(BCash_Reserves)')

    circuit.B('Loan-to-Deposit_Ratio',   circuit.gnd, circuit.gnd,
                current_expression='I(BLoan_Balance)/I(BTotal_Liabilities)')
    circuit.B('Return_on_Equity',        circuit.gnd, circuit.gnd,
                current_expression='I(LNII)/I(BTotal_Equity)')
    circuit.B('Debt_to_Equity_Ratio',    circuit.gnd, circuit.gnd,
                current_expression='I(BTotal_Liabilities)/I(BTotal_Equity)')
    
    circuit.B('Net_Stable_Funding_Ratio',circuit.gnd, circuit.gnd,
                current_expression='(I(BTotal_Equity)+0.9*I(BCurrent_Account_Balance)'
                                    '+0.9*I(BSavings_Account_Balance))'
                                    '/(0*I(BCash_Reserves)+0.85*I(BLoan_Balance))') 
    circuit.B('Liquidity_Coverage_Ratio',circuit.gnd, circuit.gnd,
                current_expression='I(BCash_Reserves)/(0.1*I(BCurrent_Account_Balance)'
                                    '+0.1*I(BSavings_Account_Balance))') 
    circuit.B('Tier_1_Capital_Ratio',    circuit.gnd, circuit.gnd,
                current_expression='I(BTotal_Equity)/I(BLoan_Balance)')
    circuit.B('Return_on_Assets',        circuit.gnd, circuit.gnd,
                current_expression='I(LNII)/I(BTotal_Assets)')
    circuit.B('Net_Interest_Margin',     circuit.gnd, circuit.gnd,
                current_expression='I(LNII)/I(BLoan_Balance)')
    circuit.B('Average_Cost_of_Debt',    circuit.gnd, circuit.gnd,
                current_expression='I(BInterest_Expense)/I(BTotal_Liabilities)')

    circuit.B('Target_Debt-to-Equity_Ratio',circuit.gnd, circuit.gnd,
                current_expression='2')
    circuit.B('Debt_to_Equity_Ratio1',   circuit.gnd, circuit.gnd,
                current_expression='I(BTotal_Liabilities)/I(BTotal_Equity)')

    circuit.B('Target_Loan-to-Deposit_Ratio',circuit.gnd, circuit.gnd,
                current_expression='1.2')
    circuit.B('Target_Tier_1_Capital_Ratio',circuit.gnd, circuit.gnd,
                current_expression='0.35')

    circuit.B('Tier_1_Capital_Ratio1',   circuit.gnd, circuit.gnd,
                current_expression='I(BTotal_Equity)/I(BLoan_Balance)')

# Control
    #Errors

    circuit.B('FTP_Err2',                circuit.gnd, circuit.gnd,
                current_expression='I(BTarget_Loan-to-Deposit_Ratio)-I(BLoan-to-Deposit_Ratio1)')
    
    circuit.B('Spread_Err2',             circuit.gnd, circuit.gnd,
                current_expression='I(BTarget_Debt-to-Equity_Ratio)-I(BDebt_to_Equity_Ratio1)')
    
    circuit.B('Spread_Err3',             circuit.gnd, circuit.gnd,
                current_expression='I(BTarget_Tier_1_Capital_Ratio)-I(BTier_1_Capital_Ratio1)')
    
    # Controllers

    if control_loan_desposit == False:
        circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
                current_expression='0.025') # keep constant without control
            


    if control_debt_equity == False and control_tier_1 == False:
        circuit.B('Spread',                  circuit.gnd, circuit.gnd,
                current_expression='0.005')


    if control_loan_desposit:
        add_integrator(circuit, 'FTP_Err2', 'BFTP_Err2')
        circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
                current_expression='0.0.025 - ({Kp}*I(BFTP_Err2) + {Ki}*I(BFTP_Err2_output))') 



    if control_debt_equity:
        add_integrator(circuit, 'Spread_Err2', 'BSpread_Err2')
        circuit.B('Spread',                  circuit.gnd, circuit.gnd,
                current_expression='0.010 - ({Kp}*I(BSpread_Err2) + {Ki}*I(BSpread_Err2_output))')



    if control_tier_1:
        add_integrator(circuit, 'Spread_Err3', 'BSpread_Err3')
        circuit.B('Spread',                 circuit.gnd, circuit.gnd,
                current_expression='0.005 + ({Kp}*I(BSpread_Err3) + {Ki}*I(BSpread_Err3_output))')
         



    print(circuit)
    return circuit 




CIRCUIT_REGISTRY = {
    'ALM': ALM
    # add new circuits here, e.g. 'rc_filter': build_rc_filter
}

def run_transient(circuit, step_time=0.05 @ u_s, end_time=600 @ u_s):
    simulator = circuit.simulator()
    return simulator.transient(step_time=step_time, end_time=end_time, use_initial_condition=True)


def plot_node_voltage(circuit, analysis, node_control='N013',node_controlled='LSavings', node_error='BIncentive_to_Borrow'):
    time = analysis.time
    voltage_control = analysis[node_control]
    voltage_controlled = analysis[node_controlled]



    x = time
    y = voltage_control

    cum_int = cumulative_trapezoid(y, x, initial=0.0)

    voltage_error = analysis[node_error]
    plt.figure()
    plt.plot(time, voltage_control, label = f"{node_control}")
    # plt.plot(time, voltage_controlled, label = "System Output (Capacitor)")
    # plt.plot(time, cum_int, label = "Integral of Controller Output")

    # plt.plot(time, voltage_error, label = "Error")
    plt.xlabel('Time [s]')
    plt.ylabel('V or A')
    # plt.title(f"{circuit.title} - Node '{node_controlled}' Voltage")
    plt.legend()
  
    plt.grid(True)
    plt.tight_layout()
    plt.show()

# --- CLI ---

def main():
    configure_environment()
    setup_logging()

    circuit = ALM()
    # Convert step and end to units
    step_time = 0.1
    end_time = 20

    analysis = run_transient(circuit)


    plot_node_voltage(circuit, analysis)


if __name__ == '__main__':
    main()