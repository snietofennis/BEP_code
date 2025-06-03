


import os
import argparse
import matplotlib.pyplot as plt
from PySpice.Logging.Logging import setup_logging
from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_F, u_H, u_Ω, u_V, u_A, u_s, u_ms, u_us, u_Ts, u_ns, u_mΩ
import numpy as np
from scipy.integrate import cumulative_trapezoid


dt = 0.1

show_statements = True
show_preset_Trate = True

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

def add_differentiator(circuit, name, input_capacitor):
        """Adds a differentiator block to the circuit."""
        circuit.B(f'{name}_input_dt', f'{name}_measured_dt', circuit.gnd, voltage_expression=f'I({input_capacitor})')
        circuit.raw_spice += f"""
A_{name}_dt {name}_measured_dt {name}_dt d_model
.model d_model d_dt(out_offset=0 
+ out_lower_limit=-1e100 out_upper_limit=1e100 
+ limit_range=1e-9)
R_{name}_dt {name}_dt 0 1Meg
"""
        circuit.B(f'{name}_output_dt', circuit.gnd, circuit.gnd, current_expression=f'V({name}_dt)')

def steps(circuit, name, rates, times):
    i = 0 
    incentive_nodes = []

    for interest_rate in rates:
        if times == None:
            width = 20
            delay = 20*i
        else:
            width = times[i] - times[i-1] if i > 0 else times[0]
            delay = times[i-1] if i > 0 else 0 

        circuit.PulseVoltageSource(f"variable_source_{i}_{name}", f"incentive_{i}_{name}", circuit.gnd,
            initial_value=0, pulsed_value=interest_rate,
            delay_time=delay + dt@u_s, rise_time=0@u_ns,
            fall_time=0@u_ns, pulse_width= width - dt@u_s, period=1@u_Ts)
                
        incentive_nodes.append(f"V(incentive_{i}_{name})")

        i += 1

            # Join all incentive node names into a single sum string
        sum_string = " + ".join(incentive_nodes)

            # Use the sum string in the behavioral voltage source
    circuit.B(f"sum_pulses_{name}", f'{name}_preset', circuit.gnd, voltage_expression =sum_string)

import numpy as np

def recommend_discrete(time, u_continuous, Ts, tol=1e-6):
    """
    Given a continuous control waveform u_continuous sampled at instants `time`,
    produce a list of (step_value, step_start_time) pairs for a zero-order hold
    with period Ts.
    
    Args:
      time             np.ndarray of shape (N,)      – strictly increasing time stamps [s]
      u_continuous     np.ndarray of shape (N,)      – continuous control signal values
      Ts               float                         – sampling period [s]
      tol              float                         – threshold for detecting changes
      
    Returns:
      rates   : list of floats    – the sampled u[k] values
      times   : list of floats    – the times at which each u[k] takes effect
    """
    # 1) build the uniform grid of sampling instants 
    t_samples = np.arange(0, time[-1] + Ts, Ts)
    # 2) sample / interpolate the continuous waveform
    u_samples = np.interp(t_samples, time, u_continuous)
    # 3) collapse into only the points where u actually changes (within tol)
    rates, times_out = [], []
    last = None
    for t, u in zip(t_samples, u_samples):
        if (last is None) or (abs(u - last) > tol):
            rates.append(u)
            times_out.append(t)
            last = u
    return rates, times_out



def ALM(
    tau_d=1.0,
    q_L0=48,
    q_C0=20,
    q_S0=20,
    q_E0=20,
    IC_Goods=100e-3,
    IC_Income=100e-3,

# Control parameters
    Kp=0.015,
    Ki=0.001,
    Kd=0.000,

    control_loan_desposit=False, #Controls FTP rate
    control_debt_equity=True, # Controls spread
    control_tier_1=False, # Controls spread

    use_preset_FTP = False,
    preset_FTP_rates = [0.035, 0.0275, 0.025, 0.0225, 0.02],
    preset_FTP_times = [200, 400, 600, 800, 1500],  # can be None

    use_preset_spread = False,
    preset_spread = [0.005, 0.005, 0.01, 0.01, 0.005],
    preset_spread_times = [40, 50, 70, 90, 110],  # can be None

    control_premium = True, # Controls FTP rate to be equal to T_rate
    use_time_delay = True, # If True, uses time delay for preset FTP rates
    time_delay = 10,

#Economic parameters
    Trate_shock = False,
    rate_shock_time = 120,
    rate_shock_size = 0.01,
    constant_T_rate = 0.02,  # default FTP rate if preset is used

    use_preset_Trate = True,
    preset_T_rates = [0.035, 0.0275, 0.025, 0.0225, 0.02],
    preset_T_times = [200, 400, 600, 800, 1500],  # can be None 

    production_shock = False,
    production_shock_time = 200,
    production_shock_size = 10,

    demand_shock = False, #Nothing yet
    demand_shock_time = 120,
    demand_shock_size = 0.03,

# Simulation parameters
    dt = dt,

):
    
    circuit = Circuit('ALM - Asset Liability Management')


    # ─────────────── Parameters ───────────────
    circuit.parameter('Kp',       Kp)       # PID-Kp
    circuit.parameter('Ki',       Ki)       # PID-Ki
    circuit.parameter('Kd',       Kd)         # PID-Kd
    circuit.parameter('tau_d',    tau_d)         # derivative filter time constant
    circuit.parameter('q_L0',     q_L0)          # initial Loan balance
    circuit.parameter('q_C0',     q_C0)          # initial Current Acct balance
    circuit.parameter('q_S0',     q_S0)          # initial Savings Acct balance
    circuit.parameter('q_E0',     q_E0)          # initial Equity
    circuit.parameter('IC_Goods', IC_Goods)      # initial production constant
    circuit.parameter('IC_Income',IC_Income)      # initial income current

    # ─────────────── Inductors (economic flows) ───────────────
    circuit.L('Investment',        'N005', circuit.gnd,       0.5   @ u_H) 
    circuit.L('Aggregate_Demand',  'N013', circuit.gnd,       1.5   @ u_H)
    circuit.L('Aggregate_Supply',  'N014', 'N013',            1     @ u_H)
    circuit.L('H_Interest',        'N008', 'N007',           10    @ u_H)
    circuit.L('F_Interest',        circuit.gnd, 'N010',      10    @ u_H)
    circuit.L('NII',               'N009', circuit.gnd,       1     @ u_H)
    circuit.L('Savings',           'N007', 'N001',            1     @ u_H)
    circuit.L('Revenue',           'N012', circuit.gnd,       1     @ u_H)
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


    # ─────────────── Behavioral Sources (financial equations) ───────────────

    # Income statement
    circuit.B('Interest_Expense',        'N009', 'N008',
                current_expression='I(BSavings_Account_Balance)*I(BSavings_Interest_Rate)/120')
    circuit.B('Interest_Income',         'N010', 'N009',
                current_expression='I(BLoan_Balance)*I(BLoan_Interest_Rate)/120')
    circuit.B('Net_Interest_Income',    circuit.gnd, circuit.gnd,
                current_expression='I(BInterest_Income)-I(BInterest_Expense)')
    


    circuit.B('Make_sure_netinterest_is_saved',                circuit.gnd, circuit.gnd, 
                current_expression='I(BNet_Interest_Income)') 

    # Cash flow statement

    circuit.L('Current_Deposits',  'N002', 'N003',           0.9   @ u_H)
    circuit.L('Savings_Deposits',  'N006', 'Incentive_to_Save',2    @ u_H)
    circuit.L('Loans',             'Incentive_to_Borrow','N004',1  @ u_H)
    circuit.B('Net_cash_flow',         circuit.gnd, circuit.gnd,
                current_expression='I(LCurrent_Deposits)+I(LSavings_Deposits) + I(BNet_Interest_Income) -I(LLoans)')

    circuit.B('makesure_netcashflow_is_saved', circuit.gnd, circuit.gnd,
                current_expression='I(BNet_cash_flow)') # make sure net cash flow is saved



    circuit.B('Incentive_to_Save',       'Incentive_to_Save', circuit.gnd,
                voltage_expression='(-8*(I(BSavings_Interest_Rate)-I(BT_rate)+0.02))') 
    circuit.B('Incentive_to_Borrow',     'Incentive_to_Borrow', circuit.gnd,
                voltage_expression='-3*(I(BLoan_Interest_Rate)-I(BT_rate)-0.02)') 

    circuit.B('Incentive_to_Deposit',    'N003', circuit.gnd,
                voltage_expression='0')


    # ------------------ Integrators -------------------

############# INTEGRATING INVESTMENT
    
    add_integrator(circuit, 'Investment', 'LInvestment')

############# INTEGRATING Current Deposits

    add_integrator(circuit, 'Current_Deposits', 'LCurrent_Deposits')

    circuit.B('Current_Account_Balance', circuit.gnd, circuit.gnd,
                current_expression='{q_C0} + I(BCurrent_Deposits_output)') 


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
                current_expression='I(BNII_output)') 





    circuit.B('Loan_Interest_Rate',      circuit.gnd, circuit.gnd,
            current_expression='I(BFTP_Rate)+I(BSpread)')

    circuit.B('Savings_Interest_Rate',   circuit.gnd, circuit.gnd,
                current_expression='I(BFTP_Rate)-I(BSpread)')
    
    circuit.B('Loan-to-Deposit_Ratio1',  circuit.gnd, circuit.gnd,
                current_expression='I(BLoan_Balance)/I(BTotal_Liabilities)') # same as BLoan-to-Deposit_Ratio



    circuit.B('Total_Liabilities',       circuit.gnd, circuit.gnd,
                current_expression='I(BCurrent_Account_Balance)+I(BSavings_Account_Balance)')
    circuit.B('Initial_Equity',          circuit.gnd, circuit.gnd,
                current_expression='({q_E0})') 
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
                current_expression='I(BTotal_Equity)/I(BLoan_Balance)') # same as BTier_1_Capital_Ratio

    
    # ----------------------- Shocks ---------------------------

    if Trate_shock:
        circuit.PulseVoltageSource("T_rate_input", "t_rate_shock", circuit.gnd,
            initial_value=1e-3, pulsed_value=rate_shock_size,
            delay_time=rate_shock_time@u_s, rise_time=1@u_ns,
            fall_time=1@u_us, pulse_width=1e100@u_s, period=1@u_Ts)
    else:
        circuit.V('T_rate_input', 't_rate_shock', circuit.gnd, 0) # keep constant without shock

    if use_preset_Trate:
        steps(circuit, 'Trate', preset_T_rates, preset_T_times)
        circuit.B('T_rate',                 circuit.gnd, circuit.gnd,
                current_expression='V(Trate_preset)+V(t_rate_shock)')
    else:
        circuit.B('T_rate',                 circuit.gnd, 'NodeT_prime',
                current_expression=f'V(t_rate_shock)+{constant_T_rate}')



    if production_shock:
        #make equivalent pulse, goes from 100e-3 to 130e-3 at 120s
        circuit.PulseVoltageSource("Production_input", "node_production", circuit.gnd,
            initial_value=0, pulsed_value=production_shock_size,
            delay_time=production_shock_time@u_s, rise_time=1@u_ns,
            fall_time=1@u_us, pulse_width=1e100@u_s, period=1@u_Ts)
        circuit.B('Production',              circuit.gnd, 'N014',
                current_expression='{IC_Goods} + I(BInvestment_output)*1/120 - V(node_production)') 
    else:    
        circuit.B('Production',              circuit.gnd, 'N014',
                current_expression='{IC_Goods} + I(BInvestment_output)*1/120')     
    

    # if demand_shock:

    # ----------------------- Control --------------------------
    
    #Errors

        #Loan to deposit ratio error
    circuit.B('FTP_Err2',                circuit.gnd, circuit.gnd,
                current_expression='I(BTarget_Loan-to-Deposit_Ratio)-I(BLoan-to-Deposit_Ratio1)')
        #Debt to equity ratio error
    circuit.B('Spread_Err2',             circuit.gnd, circuit.gnd,
                current_expression='I(BTarget_Debt-to-Equity_Ratio)-I(BDebt_to_Equity_Ratio1)')
        #Tier 1 capital ratio error
    circuit.B('Spread_Err3',             circuit.gnd, circuit.gnd,
                current_expression='I(BTarget_Tier_1_Capital_Ratio)-I(BTier_1_Capital_Ratio1)')
    

    # Add required circuit elements when there is no control

    if control_loan_desposit == False and use_preset_FTP == False and control_premium == False:
        circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
                current_expression='0.025') # keep constant without control
 


    if control_debt_equity == False and control_tier_1 == False and use_preset_spread == False:
        circuit.B('Spread',                  circuit.gnd, circuit.gnd,
                current_expression='0.005')

    # Controllers

    if control_loan_desposit:
        add_integrator(circuit, 'FTP_Err2', 'BFTP_Err2')
        add_differentiator(circuit, 'FTP_Err2', 'BFTP_Err2')
        circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
                current_expression='0.025 - ({Kp}*I(BFTP_Err2) + {Ki}*I(BFTP_Err2_output) + {Kd}*I(BFTP_Err2_output_dt))') 



    if control_debt_equity:
        add_integrator(circuit, 'Spread_Err2', 'BSpread_Err2')
        add_differentiator(circuit, 'Spread_Err2', 'BSpread_Err2')
        circuit.B('Spread',                  circuit.gnd, circuit.gnd,
                current_expression='0.010 - ({Kp}*I(BSpread_Err2) + {Ki}*I(BSpread_Err2_output) + {Kd}*I(BSpread_Err2_output_dt))')

    if control_tier_1:
        add_integrator(circuit, 'Spread_Err3', 'BSpread_Err3')
        add_differentiator(circuit, 'Spread_Err3', 'BSpread_Err3')
        circuit.B('Spread',                 circuit.gnd, circuit.gnd,
                current_expression='0.005 + ({Kp}*I(BSpread_Err3) + {Ki}*I(BSpread_Err3_output) + {Kd}*I(BSpread_Err3_output_dt))')
    
    if use_preset_FTP:
        steps(circuit, 'FTP', preset_FTP_rates, preset_FTP_times)
        circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
                current_expression='V(FTP_preset)')

    if use_preset_spread:
        steps(circuit, 'Spread', preset_spread, preset_spread_times)
        circuit.B('Spread',                 circuit.gnd, circuit.gnd,
                current_expression='V(Spread_preset)')

    

    if control_premium and use_time_delay == True:
        new_times = [t + time_delay for t in preset_T_times]
        steps(circuit, 'FTP', preset_T_rates, new_times)  # add time delay to preset times
        circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
                current_expression='V(FTP_preset)')
    elif control_premium:
        circuit.B('FTP_Rate',                circuit.gnd, circuit.gnd, 
                current_expression='I(BT_rate)') 
        # circuit.B('Spread',                  circuit.gnd, circuit.gnd,
        #           current_expression='')


        
    print(circuit)
    return circuit 


def run_transient(circuit, step_time=dt @ u_s, end_time=5000 @ u_s):
    simulator = circuit.simulator()
    return simulator.transient(step_time=dt, end_time=end_time, use_initial_condition=True)


def plotting(circuit, analysis, plot_1 = 'v_btarget_debt-to-equity_ratio', plot_2 ='v_bdebt_to_equity_ratio1', plot_3 ='v_bspread'):
    time = analysis.time
    #plot_1 = 'v_btarget_loan-to-deposit_ratio', plot_2 ='v_bloan-to-deposit_ratio1', plot_3 ='BIncentive_to_Borrow'
    plot_1_output = analysis[plot_1]
    plot_2_output = analysis[plot_2]
    plot_3_output = analysis[plot_3]


    # x = time
    # y = voltage_control

    # cum_int = cumulative_trapezoid(y, x, initial=0.0)
    print(analysis.branches.keys())

    # plt.figure()
    plt.plot(time, plot_1_output, label = f"{plot_1}")
    plt.plot(time, plot_2_output, label = f"{plot_2}")
    # # plt.plot(time, plot_3_output, label = f"{plot_3}")

    plt.xlabel('Time [s]')
    plt.ylabel('V or A')
    plt.legend()
  
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    if show_preset_Trate:
        plot_incentive =  analysis['v_bt_rate']
        plot_delayed = analysis['v_bftp_rate']
        print(plot_incentive)
 
        plt.figure()
        plt.plot(time, plot_incentive, label='t_rate', color='orange')
        plt.plot(time, plot_delayed, label='FTP Rate', color='purple')
        plt.xlabel('Time [s]')
        plt.ylabel('V')
        plt.legend()
    
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    if show_statements:
        fig, axs = plt.subplots(3, 1, figsize=(8, 10), sharex=True)

        # Balance Sheet
        axs[0].plot(time, analysis['v_btotal_assets'], label='Total Assets', color = 'blue')
        axs[0].plot(time, analysis['v_btotal_liabilities'], label='Total Liabilities', color = 'red')
        axs[0].plot(time, analysis['v_btotal_equity'], label='Total Equity', color = 'green')
        axs[0].set_title('Balance Sheet')
        axs[0].set_ylabel('Value')
        axs[0].legend()
        axs[0].grid(True)

        # Cashflow Statement

        axs[1].plot(time, analysis['v_bnet_cash_flow'], label='Net Cash Flow', zorder= 10, linewidth=2)
        axs[1].plot(time, analysis['Lcurrent_deposits'], label='Current Deposits', linestyle=':')
        axs[1].plot(time, analysis['Lsavings_deposits'], label='Savings Deposits', linestyle=':')
        axs[1].plot(time, analysis['Lloans'], label='Loans', linestyle=':')
        axs[1].plot(time, analysis['v_bnet_interest_income'], label='Net Interest Income', color = 'greenyellow')
        axs[1].set_title('Cashflow Statement')
        axs[1].set_ylabel('Value')
        axs[1].legend()
        axs[1].grid(True)

        # Income Statement

        axs[2].plot(time, analysis['v_bnet_interest_income'], label='Net Interest Income', color = 'darkgreen')
        axs[2].plot(time, analysis['v_binterest_income'], label='Interest Income', color = 'deepskyblue')
        axs[2].plot(time, analysis['v_binterest_expense'], label='Interest Expense', color = 'firebrick')
        axs[2].set_title('Income Statement')
        axs[2].set_xlabel('Time [s]')
        axs[2].set_ylabel('Value')
        axs[2].legend()
        axs[2].grid(True)

        plt.tight_layout()
        plt.show()

def plot_control_with_zoh(time, u_continuous, Ts):
    """
    Plot continuous control signal and its ZOH discrete approximation.
    
    Args:
        time (np.ndarray): time stamps of continuous signal [s]
        u_continuous (np.ndarray): continuous control signal values
        Ts (float): sampling period [s]
    """
    # Get discrete ZOH approximation
    rates, times_zoh = recommend_discrete(time, u_continuous, Ts)

    
    # Build step plot arrays
    step_times = np.append(times_zoh, time[-1])
    step_values = np.append(rates, rates[-1])
    
    # Plot
    plt.figure()
    plt.plot(time, u_continuous, label='Continuous PID')
    plt.step(step_times, step_values, where='post', label='ZOH Approximation')
    plt.xlabel('Time (s)')
    plt.ylabel('Control Signal')
    plt.legend()
    plt.title('Continuous PID vs. Discrete ZOH-Control')
    plt.grid(True)
    plt.show()

def run_recommend_discrete(time, u_continuous, Ts):
    rates, times_zoh = recommend_discrete(time, u_continuous, Ts)
    print(f"ZOH rates: {rates}")
    print(f"ZOH times: {times_zoh}")
    circuit = ALM(use_preset_FTP=True, preset_FTP_rates = rates, preset_FTP_times= times_zoh, control_loan_desposit=False)
    analysis = run_transient(circuit)
    plotting(circuit, analysis)


def main():
    configure_environment()
    setup_logging()

    circuit = ALM()

    analysis = run_transient(circuit)

    plotting(circuit, analysis)

    time = analysis.time
    u_continuous = analysis['v_bftp_rate']
    Ts = 20

    # run_recommend_discrete(time, u_continuous, Ts)
    # plot_control_with_zoh(time, u_continuous, Ts)


if __name__ == '__main__':
    main()