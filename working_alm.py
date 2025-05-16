import os
import argparse
import matplotlib.pyplot as plt
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_F, u_H, u_Ω, u_V, u_A, u_s, u_ms, u_us, u_Ts, u_ns, u_mΩ
import numpy as np
from scipy.integrate import cumulative_trapezoid




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

    # ─────────────── Inductors (economic flows) ───────────────
    

############# INTEGRATING INVESTMENT
    
    circuit.B('Investment_input', 'Investment_measured', circuit.gnd, voltage_expression='I(LInvestment)')


    circuit.raw_spice += f"""
A_investment Investment_measured Investment_idt i_model
.model i_model int(gain=1 in_offset=0 
+ out_lower_limit=-1e100 out_upper_limit=1e100
+ limit_range=1e-9 out_ic=0)
R_investment Investment_idt 0 1Meg
"""
        
    circuit.B('Investment_output', circuit.gnd, circuit.gnd, current_expression='V(Investment_idt)')

    circuit.B('Production',              circuit.gnd, 'N014',
                current_expression='{IC_Goods} + I(BInvestment_output)*1/120') 

###############

    # circuit.B('Production',              circuit.gnd, 'N014',
    #             current_expression='{IC_Goods} + idt(I(Investment))*1/120') #Integrate, inductor, 

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
    # ─── ideal coupling: KH1 L_Consumption & L_Income, KH2 L_Income & Savings
        
    # circuit.raw_spice += '\nKHK1 LConsumption LIncome -0.2\n'
    # circuit.raw_spice += '\nKHK2 LIncome      LSavings  -0.8\n'

    circuit.K('H1', 'Consumption', 'Aggregate_Demand',  -0.2)
    circuit.K('H2', 'Income',      'Savings', -0.8)

    circuit.K('F1', 'Aggregate_Supply', 'Wage', -0.6)
    circuit.K('F2', 'Revenue',      'Investment', -0.4)


    # KH1 L_Consumption Aggregate_demand -0.2
    # KH2 L_Income Savings -0.8
    # KF1 Aggregate_Supply Wage -0.6
    # KF2 Revenue Investment -0.4

    
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
    
    # Integrator



    circuit.B('Incentive_to_Save',       'Incentive_to_Save', circuit.gnd,
                voltage_expression='(-8*(I(BSavings_Interest_Rate)-I(BT_rate)+0.02))') #IF(time<0.02,0,
    circuit.B('Incentive_to_Borrow',     'Incentive_to_Borrow', circuit.gnd,
                voltage_expression='-3*(I(BLoan_Interest_Rate)-I(BT_rate)-0.020)') #IF(time<0.02,0,

    circuit.B('Incentive_to_Deposit',    'N003', circuit.gnd,
                voltage_expression='0')


                #----------------Dashboard--------------------


    # ------------------ Integrators -------------------

############# INTEGRATING Current Deposits

    
    circuit.B('Current_Deposits_input', 'Current_Deposits_measured', circuit.gnd, voltage_expression='I(LCurrent_Deposits)')


    circuit.raw_spice += f"""
A_currentdeposit Current_Deposits_measured Current_Deposits_idt i_model
.model i_model int(gain=1 in_offset=0 
+ out_lower_limit=-1e100 out_upper_limit=1e100
+ limit_range=1e-9 out_ic=0)
R_Current_Deposits_idt Current_Deposits_idt 0 1Meg
"""
        
    circuit.B('Current_Deposits_output', circuit.gnd, circuit.gnd, current_expression='V(Current_Deposits_idt)')

    circuit.B('Current_Account_Balance', circuit.gnd, circuit.gnd,
                current_expression='{q_C0} + I(BCurrent_Deposits_output)') #IF(time<0.0001,0, en #Integrate inductor

###############

    # circuit.B('Current_Account_Balance', circuit.gnd, circuit.gnd,
    #             current_expression='({q_C0} + idt(I(Current_Deposits)))') #IF(time<0.0001,0, en #Integrate inductor

############# INTEGRATING Savings Deposits

    
    circuit.B('Savings_Deposits_input', 'Savings_Deposits_measured', circuit.gnd, voltage_expression='I(LSavings_Deposits)')


    circuit.raw_spice += f"""
A_SavingsDeposits Savings_Deposits_measured Savings_Deposits_idt i_model
.model i_model int(gain=1 in_offset=0 
+ out_lower_limit=-1e100 out_upper_limit=1e100
+ limit_range=1e-9 out_ic=0)
R_SavingsDeposits Savings_Deposits_idt 0 1Meg
"""
        
    circuit.B('Saving_Deposits_output', circuit.gnd, circuit.gnd, current_expression='V(Savings_Deposits_idt)')

    circuit.B('Savings_Account_Balance', circuit.gnd, circuit.gnd,
                current_expression='{q_S0} + I(BSaving_Deposits_output)') 


###############


    # circuit.B('Savings_Account_Balance', circuit.gnd, circuit.gnd,
    #             current_expression='({q_S0} + idt(I(Savings_Deposits)))') #IF(time<0.0001,0, en #Integrate inductor


############# INTEGRATING Loans

    
    circuit.B('Loans_input', 'Loans_measured', circuit.gnd, voltage_expression='I(LLoans)')


    circuit.raw_spice += f"""
A_Loans Loans_measured Loans_idt i_model
.model i_model int(gain=1 in_offset=0 
+ out_lower_limit=-1e100 out_upper_limit=1e100
+ limit_range=1e-9 out_ic=0)
R_Loans Loans_idt 0 1Meg
"""
        
    circuit.B('Loans_output', circuit.gnd, circuit.gnd, current_expression='V(Loans_idt)')

    circuit.B('Loan_Balance',            circuit.gnd, circuit.gnd,
                current_expression='{q_L0} + I(BLoans_output)')


###############


    # circuit.B('Loan_Balance',            circuit.gnd, circuit.gnd,
    #             current_expression='({q_L0} + idt(I(Loans)))') #IF(time<0.0001,0,  en #Integrate inductor
    
############# INTEGRATING NII

    
    circuit.B('NII_input', 'NII_measured', circuit.gnd, voltage_expression='I(LNII)')


    circuit.raw_spice += f"""
A_NII NII_measured NII_idt i_model
.model i_model int(gain=1 in_offset=0 
+ out_lower_limit=-1e100 out_upper_limit=1e100
+ limit_range=1e-9 out_ic=0)
R_NII NII_idt 0 1Meg
"""
        
    circuit.B('NII_output', circuit.gnd, circuit.gnd, current_expression='V(NII_idt)')


    circuit.B('Retained_Earnings',       circuit.gnd, circuit.gnd,
                current_expression='I(BNII_output)') #Integrate inductor

###############

    # circuit.B('Retained_Earnings',       circuit.gnd, circuit.gnd,
    #             current_expression='idt(I(NII))') #Integrate inductor

############# INTEGRATING Spread_Err2

    
    circuit.B('Spread_Err2_input', 'Spread_Err2_measured', circuit.gnd, voltage_expression='I(BSpread_Err2)')


    circuit.raw_spice += f"""
A_Spread_Err2 Spread_Err2_measured Spread_Err2_idt i_model
.model i_model int(gain=1 in_offset=0 
+ out_lower_limit=-1e100 out_upper_limit=1e100
+ limit_range=1e-9 out_ic=0)
R_Spread_Err2 Spread_Err2_idt 0 1Meg
"""
        
    circuit.B('Spread_Err2_output', circuit.gnd, circuit.gnd, current_expression='V(Spread_Err2_idt)')


    circuit.B('Spread',                  circuit.gnd, circuit.gnd,
                current_expression='0.005')

###############

    # circuit.B('Spread',                  circuit.gnd, circuit.gnd,
    #             current_expression='0.005-(0.1*I(Spread_Err2)+{Ki}*idt(I(Spread_Err2)))') # IF(time<0.001,0, en PI Current expression, integrate


    # ------------------ If Statements -------------------
########
# rate shock
    # circuit.B('T_rate',                  circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,IF(time<120,0.02,0.03))') #Pulse !!!! Can also just a constant probs, goes from 0.02 to o.03 at 120s
    
#make equivalent pulse, goes from 0.02 to 0.03 at 120s
    circuit.PulseVoltageSource("T_rate_input", "node_t_rate", circuit.gnd,
        initial_value=0.02, pulsed_value=0.03,
        delay_time=120@u_s, rise_time=1@u_ns,
        fall_time=1@u_us, pulse_width=1e100@u_s, period=1@u_Ts)
    circuit.B('T_rate',                  circuit.gnd, circuit.gnd,
                current_expression='V(node_t_rate)') 
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
                current_expression='I(BTarget_Debt-to-Equity_Ratio)-I(BDebt_to_Equity_Ratio1)')
########
 
#####    
    # circuit.B('FTP_Err2',                circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.02,0,I(Target_Loan-to-Deposit_Ratio)-I(Loan-to-Deposit_Ratio1))') # should just be the second part
    # set equal to the second part of the equation
    circuit.B('FTP_Err2',                circuit.gnd, circuit.gnd,
                current_expression='I(BTarget_Loan-to-Deposit_Ratio)-I(BLoan-to-Deposit_Ratio1)')    
#########

#####
    # circuit.B('Loan_Interest_Rate',      circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,I(FTP_Rate)+I(Spread))') # should just be the second part
    # set equal to the second part of the equation
    circuit.B('Loan_Interest_Rate',      circuit.gnd, circuit.gnd,
            current_expression='I(BFTP_Rate)+I(BSpread)')
#########

#####    
    # circuit.B('Savings_Interest_Rate',   circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,I(FTP_Rate)-I(Spread))') # should just be the second part
    # set equal to the second part of the equation
    circuit.B('Savings_Interest_Rate',   circuit.gnd, circuit.gnd,
                current_expression='I(BFTP_Rate)-I(BSpread)')
    
###########

####### MIGHT CAUSE ISSUES WITH DIVIDED BY ZERO    
    # circuit.B('Loan-to-Deposit_Ratio1',  circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.02,I(Target_Loan-to-Deposit_Ratio),I(Loan_Balance)/I(Total_Liabilities))') # keep second part of the equation
    # set equal to the second part of the equation
    circuit.B('Loan-to-Deposit_Ratio1',  circuit.gnd, circuit.gnd,
                current_expression='I(BLoan_Balance)/I(BTotal_Liabilities)')
##########

###### INTEGRATOR
    # circuit.B('Spread3',                 circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.001,0,0.005+(0.05*I(Spread_Err3)+0.00*idt(I(Spread_Err3))))')  # Keeping second part of the equation
    # set equal to the second part of the equation

######################## INCLUDES 0.00   
    # circuit.B('Spread3',                 circuit.gnd, circuit.gnd,
    #             current_expression='0.005+(0.05*I(Spread_Err3)+0.00*idt(I(Spread_Err3)))')     # Integrate current expression
#########################   
    circuit.B('Spread3',                 circuit.gnd, circuit.gnd,
                current_expression='0.005+(0.05*I(BSpread_Err3))')
##########

######
    # circuit.B('Spread_Err3',             circuit.gnd, circuit.gnd,
    #             current_expression='IF(time<0.02,0,I(Target_Tier_1_Capital_Ratio)-I(Tier_1_Capital_Ratio1))') # should just be the second part
    # set equal to the second part of the equation
    circuit.B('Spread_Err3',             circuit.gnd, circuit.gnd,
                current_expression='I(BTarget_Tier_1_Capital_Ratio)-I(BTier_1_Capital_Ratio1)')
###########

###### INTEGRATOR
    # circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
    #             current_expression='IF(time<0.001,0,0.025-(2*0.06*I(FTP_Err2)+1.5*0.003*idt(I(FTP_Err2))))') # keep second part of the equation
    # set equal to the second part of the equation

############# INTEGRATING FTP_Err2

    
    circuit.B('FTP_Err2_input', 'FTP_Err2_measured', circuit.gnd, voltage_expression='I(BFTP_Err2)')


    circuit.raw_spice += f"""
A_FTP_Err2 FTP_Err2_measured FTP_Err2_idt i_model
.model i_model int(gain=1 in_offset=0 
+ out_lower_limit=-1e100 out_upper_limit=1e100
+ limit_range=1e-9 out_ic=0)
R_FTP_Err2 FTP_Err2_idt 0 1Meg
"""
        
    circuit.B('FTP_Err2_output', circuit.gnd, circuit.gnd, current_expression='V(FTP_Err2_idt)')


    circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
                current_expression='0.025') #0.025-(2*0.06*I(BFTP_Err2)+1.5*0.003*I(BFTP_Err2_output))

###############
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
                                    '/(0*I(BCash_Reserves)+0.85*I(BLoan_Balance))') #Raar met '' misschien later aanpassen, indien errors.
    circuit.B('Liquidity_Coverage_Ratio',circuit.gnd, circuit.gnd,
                current_expression='I(BCash_Reserves)/(0.1*I(BCurrent_Account_Balance)'
                                    '+0.1*I(BSavings_Account_Balance))') # Same als boven
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

    print(circuit)
    return circuit 




CIRCUIT_REGISTRY = {
    'ALM': ALM
    # add new circuits here, e.g. 'rc_filter': build_rc_filter
}

def run_transient(circuit, step_time=0.05 @ u_s, end_time=600 @ u_s):
    simulator = circuit.simulator()
    return simulator.transient(step_time=step_time, end_time=end_time, use_initial_condition=True)


def plot_node_voltage(circuit, analysis, node_control='LNII',node_controlled='LSavings', node_error='BIncentive_to_Borrow'):
    time = analysis.time
    voltage_control = analysis[node_control]
    voltage_controlled = analysis[node_controlled]



    x = time
    y = voltage_control

    # pre‐allocate cumulative integral array
    # cum_int = np.empty_like(x)
    # cum_int[0] = 0.0

    # # integrate from x[0] up to x[i] at each step
    # for i in range(1, len(x)):
    #     cum_int[i] = np.trapezoid(y[:i+1], x[:i+1])
    cum_int = cumulative_trapezoid(y, x, initial=0.0)

    voltage_error = analysis[node_error]
    plt.figure()
    plt.plot(time, voltage_control, label = "Controller Output")
    # plt.plot(time, voltage_controlled, label = "System Output (Capacitor)")
    # plt.plot(time, cum_int, label = "Integral of Controller Output")

    # plt.plot(time, voltage_error, label = "Error")
    plt.xlabel('Time [s]')
    plt.ylabel('Voltage [V]')
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