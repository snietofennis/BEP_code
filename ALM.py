import os
import argparse
import matplotlib.pyplot as plt
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_F, u_H, u_Ω, u_V, u_A, u_s, u_ms, u_us, u_Ts, u_ns, u_mΩ



def configure_environment():
    # os.environ["PYSPICE_SIMULATOR"] = "ngspice"
    # # If needed, adjust PATH externally or here:
    # os.environ["PATH"] += r";C:\\path\\to\\ngspice\\bin"
    return

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
    # .ic I(L_Income) = {IC_Income}   ← PySpice cannot yet embed .ic directives

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
    circuit.L('Income',            'N011', 'N007',            1.5   @ u_H)
    circuit.L('Consumption',       'N007', 'N012',            1     @ u_H)
    # ─── ideal coupling: KH1 L_Consumption & L_Income, KH2 L_Income & Savings
        
    circuit.raw_spice += '\nKHK1 LConsumption LIncome -0.2\n'
    circuit.raw_spice += '\nKHK2 LIncome      LSavings  -0.8\n'


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
    circuit.R('Aggregate_Supply_Rser','N014','N013',         1e-6  @ u_Ω)  # Rser=1µ
    circuit.R('F_Interest_Rser',   circuit.gnd,'N010',        1e-6  @ u_Ω)  # Rser=1µ
    circuit.R('Revenue_Rser',      'N012', circuit.gnd,       1e-6  @ u_Ω)  # Rser=1µ
    circuit.R('Wage_Rser',         circuit.gnd,'N011',      1e-6  @ u_Ω)  # Rser=1µ



    # ─────────────── Behavioral Sources (financial equations) ───────────────
    circuit.B('Interest_Expense',        'N009', 'N008',
                current_expression='I(Savings_Account_Balance)*I(Savings_Interest_Rate)/120')
    circuit.B('Interest_Income',         'N010', 'N009',
                current_expression='I(Loan_Balance)*I(Loan_Interest_Rate)/120')
    
    # Integrator
    circuit.B('Production',              circuit.gnd, 'N014',
                current_expression='{IC_Goods} + idt(I(Investment))*1/120') #Integrate, inductor


    circuit.B('Incentive_to_Save',       'Incentive_to_Save', circuit.gnd,
                voltage_expression='(-8*(I(Savings_Interest_Rate)-I(T_rate)+0.02))') #IF(time<0.02,0,
    circuit.B('Incentive_to_Borrow',     'Incentive_to_Borrow', circuit.gnd,
                voltage_expression='(-3*(I(Loan_Interest_Rate)-I(T_rate)-0.020))') #IF(time<0.02,0,

    circuit.B('Incentive_to_Deposit',    'N003', circuit.gnd,
                voltage_expression='0')


                #----------------Dashboard--------------------


    # ------------------ Integrators -------------------



    circuit.B('Current_Account_Balance', circuit.gnd, circuit.gnd,
                current_expression='({q_C0} + idt(I(Current_Deposits)))') #IF(time<0.0001,0, en #Integrate inductor


    circuit.B('Savings_Account_Balance', circuit.gnd, circuit.gnd,
                current_expression='({q_S0} + idt(I(Savings_Deposits)))') #IF(time<0.0001,0, en #Integrate inductor


    circuit.B('Loan_Balance',            circuit.gnd, circuit.gnd,
                current_expression='({q_L0} + idt(I(Loans)))') #IF(time<0.0001,0,  en #Integrate inductor
    
    circuit.B('Retained_Earnings',       circuit.gnd, circuit.gnd,
                current_expression='idt(I(NII))') #Integrate inductor
    
    circuit.B('Spread',                  circuit.gnd, circuit.gnd,
                current_expression='0.005-(0.1*I(Spread_Err2)+{Ki}*idt(I(Spread_Err2)))') # IF(time<0.001,0, en PI Current expression, integrate


    # ------------------ If Statements -------------------
########
# rate shock
    # circuit.B('T_rate',                  circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,IF(time<120,0.02,0.03))') #Pulse !!!! Can also just a constant probs, goes from 0.02 to o.03 at 120s
    
#make equivalent pulse, goes from 0.02 to 0.03 at 120s
    circuit.PulseVoltageSource("T_rate", circuit.gnd, circuit.gnd,
        initial_value=0.02, pulsed_value=0.03,
        delay_time=120@u_s, rise_time=1@u_ns,
        fall_time=1@u_us, pulse_width=1e100@u_s, period=1@u_Ts)
#########


######
    # circuit.B('FTP_Rate1',               circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,IF(time<20,0.025,0.025))') # Always 0.025
# set equal to 0.025
    circuit.B('FTP_Rate1',               circuit.gnd, circuit.gnd,
                current_expression='0.025')
########

#####
    # circuit.B('Spread1',                 circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,0.005)') # always 0.005
    # set equal to 0.005
    circuit.B('Spread1',                 circuit.gnd, circuit.gnd,
                current_expression='0.005')
#########


####    
    # circuit.B('Spread_Err2',             circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.02,0,I(Target_Debt-to-Equity_Ratio)-I(Debt_to_Equity_Ratio1))') # should just be the second part
    # set equal to the second part of the equation
    circuit.B('Spread_Err2',             circuit.gnd, circuit.gnd,
                current_expression='I(Target_Debt-to-Equity_Ratio)-I(Debt_to_Equity_Ratio1)')
########
 
#####    
    # circuit.B('FTP_Err2',                circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.02,0,I(Target_Loan-to-Deposit_Ratio)-I(Loan-to-Deposit_Ratio1))') # should just be the second part
    # set equal to the second part of the equation
    circuit.B('FTP_Err2',                circuit.gnd, circuit.gnd,
                current_expression='I(Target_Loan-to-Deposit_Ratio)-I(Loan-to-Deposit_Ratio1)')    
#########

#####
    # circuit.B('Loan_Interest_Rate',      circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,I(FTP_Rate)+I(Spread))') # should just be the second part
    # set equal to the second part of the equation
    circuit.B('Loan_Interest_Rate',      circuit.gnd, circuit.gnd,
            current_expression='I(FTP_Rate)+I(Spread)')
#########

#####    
    # circuit.B('Savings_Interest_Rate',   circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,I(FTP_Rate)-I(Spread))') # should just be the second part
    # set equal to the second part of the equation
    circuit.B('Savings_Interest_Rate',   circuit.gnd, circuit.gnd,
                current_expression='I(FTP_Rate)-I(Spread)')
    
###########

####### MIGHT CAUSE ISSUES WITH DIVIDED BY ZERO    
    # circuit.B('Loan-to-Deposit_Ratio1',  circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.02,I(Target_Loan-to-Deposit_Ratio),I(Loan_Balance)/I(Total_Liabilities))') # keep second part of the equation
    # set equal to the second part of the equation
    circuit.B('Loan-to-Deposit_Ratio1',  circuit.gnd, circuit.gnd,
                current_expression='I(Loan_Balance)/I(Total_Liabilities)')
##########

###### INTEGRATOR
    # circuit.B('Spread3',                 circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,0.005+(0.05*I(Spread_Err3)+0.00*idt(I(Spread_Err3))))')  # Keeping second part of the equation
    # set equal to the second part of the equation
    circuit.B('Spread3',                 circuit.gnd, circuit.gnd,
                current_expression='0.005+(0.05*I(Spread_Err3)+0.00*idt(I(Spread_Err3)))')     # Integrate current expression
##########

######
    # circuit.B('Spread_Err3',             circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.02,0,I(Target_Tier_1_Capital_Ratio)-I(Tier_1_Capital_Ratio1))') # should just be the second part
    # set equal to the second part of the equation
    circuit.B('Spread_Err3',             circuit.gnd, circuit.gnd,
                current_expression='I(Target_Tier_1_Capital_Ratio)-I(Tier_1_Capital_Ratio1)')
###########

###### INTEGRATOR
    # circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
    #             current_expression='IF(time<0.001,0,0.025-(2*0.06*I(FTP_Err2)+1.5*0.003*idt(I(FTP_Err2))))') # keep second part of the equation
    # set equal to the second part of the equation
    circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
                current_expression='0.025-(2*0.06*I(FTP_Err2)+1.5*0.003*idt(I(FTP_Err2)))') # Integrate current expression
    


    # ------------------ Normal behavioral probs -------------------

    circuit.B('Total_Liabilities',       circuit.gnd, circuit.gnd,
                current_expression='I(Current_Account_Balance)+I(Savings_Account_Balance)')
    circuit.B('Initial_Equity',          circuit.gnd, circuit.gnd,
                current_expression='({q_E0})') #IF(time<0.0001,0,
    circuit.B('Total_Equity',            circuit.gnd, circuit.gnd,
                current_expression='I(Retained_Earnings)+I(Initial_Equity)')
    circuit.B('Cash_Reserves',           circuit.gnd, circuit.gnd,
                current_expression='I(Total_Liabilities)+I(Total_Equity)-I(Loan_Balance)')
    circuit.B('Total_Assets',            circuit.gnd, circuit.gnd,
                current_expression='I(Loan_Balance)+I(Cash_Reserves)')

    circuit.B('Loan-to-Deposit_Ratio',   circuit.gnd, circuit.gnd,
                current_expression='I(Loan_Balance)/I(Total_Liabilities)')
    circuit.B('Return_on_Equity',        circuit.gnd, circuit.gnd,
                current_expression='I(NII)/I(Total_Equity)')
    circuit.B('Debt_to_Equity_Ratio',    circuit.gnd, circuit.gnd,
                current_expression='I(Total_Liabilities)/I(Total_Equity)')
    
    circuit.B('Net_Stable_Funding_Ratio',circuit.gnd, circuit.gnd,
                current_expression='(I(Total_Equity)+0.9*I(Current_Account_Balance)'
                                    '+0.9*I(Savings_Account_Balance))'
                                    '/(0*I(Cash_Reserves)+0.85*I(Loan_Balance))') #Raar met '' misschien later aanpassen, indien errors.
    circuit.B('Liquidity_Coverage_Ratio',circuit.gnd, circuit.gnd,
                current_expression='I(Cash_Reserves)/(0.1*I(Current_Account_Balance)'
                                    '+0.1*I(Savings_Account_Balance))') # Same als boven
    circuit.B('Tier_1_Capital_Ratio',    circuit.gnd, circuit.gnd,
                current_expression='I(Total_Equity)/I(Loan_Balance)')
    circuit.B('Return_on_Assets',        circuit.gnd, circuit.gnd,
                current_expression='I(NII)/I(Total_Assets)')
    circuit.B('Net_Interest_Margin',     circuit.gnd, circuit.gnd,
                current_expression='I(NII)/I(Loan_Balance)')
    circuit.B('Average_Cost_of_Debt',    circuit.gnd, circuit.gnd,
                current_expression='I(Interest_Expense)/I(Total_Liabilities)')

    circuit.B('Target_Debt-to-Equity_Ratio',circuit.gnd, circuit.gnd,
                current_expression='2')
    circuit.B('Debt_to_Equity_Ratio1',   circuit.gnd, circuit.gnd,
                current_expression='I(Total_Liabilities)/I(Total_Equity)')

    circuit.B('Target_Loan-to-Deposit_Ratio',circuit.gnd, circuit.gnd,
                current_expression='1.2')
    circuit.B('Target_Tier_1_Capital_Ratio',circuit.gnd, circuit.gnd,
                current_expression='0.35')

    circuit.B('Tier_1_Capital_Ratio1',   circuit.gnd, circuit.gnd,
                current_expression='I(Total_Equity)/I(Loan_Balance)')


    return circuit 




CIRCUIT_REGISTRY = {
    'ALM': ALM
    # add new circuits here, e.g. 'rc_filter': build_rc_filter
}

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

    circuit = ALM()
    # Convert step and end to units
    step_time = 0.1
    end_time = 20

    analysis = run_transient(circuit)


    plot_node_voltage(circuit, analysis)


if __name__ == '__main__':
    main()
