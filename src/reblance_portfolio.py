# version 1.0 
from pymongo import MongoClient
from bson import ObjectId
from alpaca_trade_api.rest import REST, TimeFrame
from alpaca_trade_api.stream import Stream
import random 
import os 
from weights_selection import modulo3
from time import sleep
from send_orders_paper import get_portfolio_db
import time

def _alpaca_symbols_to_close(alpaca_positions, portfolio_symbols):
    '''
    Return the sybmols to close positions
    '''
    alpaca_symbols_to_close = [x for x in alpaca_positions if x not in portfolio_symbols]
    return alpaca_symbols_to_close

def _all_symbols_eligible_for_fractionals(portfolio_symbols, alpaca):
    
    all_symbols_eligible_for_fractionals = all([[alpaca.get_asset(symbol).fractionable for symbol in portfolio_symbols]])
    return all_symbols_eligible_for_fractionals

def alpaca_close_positions(symbols_to_close, alpaca):
    '''
    Close the positions for the symbols given
    '''

    for symbol in symbols_to_close:
        order_pending = True
        alpaca_order_info = alpaca.close_position(symbol)
        alpaca_client_order_id = alpaca_order_info.client_order_id
        
        while order_pending:
            alpaca_latest_order_info = alpaca.get_order_by_client_order_id(alpaca_client_order_id)
            alpaca_latest_status = alpaca_latest_order_info.status
            if alpaca_latest_status == "filled":
                order_pending = False

def _rebalance_equity(cash_weight, alpaca):
    '''
    Get the amount to rebalance the portfolio
    '''
    alpaca_account_equity = float(alpaca.get_account().equity)
    rebalance_equity = alpaca_account_equity - (alpaca_account_equity * cash_weight)
    
    return rebalance_equity

def _portfolio_symbols_equity_allocations(target_allocations, rebalance_equity):
    '''
    Get the dollar allocation for the target portfolio and the amount that we wnat to invest
    '''
    portfolio_symbols_equity_allocations = {}
    for ticker, weight in target_allocations.items():
        portfolio_symbols_equity_allocations[ticker] = round((weight * rebalance_equity))
    
    return portfolio_symbols_equity_allocations
    
def _alpaca_latest_positions_allocations(alpaca):
    '''
    Get the latest positions allocations symbol:alloc
    '''
    
    latest_alpaca_positions_allocations = {position.symbol: float(position.market_value) for position in alpaca.list_positions()}
    return latest_alpaca_positions_allocations

def _alpaca_latest_positions(alpaca):
    '''
    Get the latest positions [symbol]
    '''
    alpaca_positions = alpaca.list_positions()
    alpaca_latest_positions = [position.symbol for position in alpaca_positions]

    return alpaca_latest_positions

def _alpaca_symbols_to_sell_and_buy(portfolio_symbols_equity_allocations, latest_alpaca_positions_allocations):
    '''
    Get the symbols to buy and to sell from the traget portfolio
    '''
    positions_to_sell, positions_to_buy = {}, {}

    # Loop Through Latest Desired Allocation
    for ticker, desired_allocation in portfolio_symbols_equity_allocations.items():

        current_allocation = latest_alpaca_positions_allocations.get(ticker, 0)
        allocation_to_adjust = desired_allocation - current_allocation

        if allocation_to_adjust > 0:
            positions_to_buy[ticker] = allocation_to_adjust
        else:
            positions_to_sell[ticker] = allocation_to_adjust * -1
    
    return positions_to_sell, positions_to_buy

def alpaca_order(symbol, amount, side, alpaca):
    '''
    Send orders to alpaca
    '''
    if amount > 1:
        amount = round(amount)
        alpaca_order_info = alpaca.submit_order(symbol=symbol, notional=amount, side=side, type="market", time_in_force="day")
        alpaca_client_order_id = alpaca_order_info.client_order_id
        
        order_pending = True
        while order_pending:
            latest_alpaca_order_info = alpaca.get_order_by_client_order_id(alpaca_client_order_id)
            alpaca_latest_status = latest_alpaca_order_info.status
            sleep(2.5)
            if alpaca_latest_status == "filled":
                order_pending = False

def handle_buy_orders(positions_to_buy, alpaca):
    '''
    Send buy orders
    '''
    
    for symbol, amount in positions_to_buy.items():
        print(f'Submitting market order "buy" for {amount} dollars of {symbol}')
        alpaca_order(symbol, amount, "buy", alpaca)

def handle_sell_orders(positions_to_sell, alpaca):
    '''
    Send sell orders
    '''
    for symbol, amount in positions_to_sell.items():
        print(f'Submitting market order "sell" for {amount} dollars of {symbol}')
        alpaca_order(symbol, amount, "sell", alpaca)

def alpaca_rebalance():
    
    user_portfolio_id = input('\nIngrese el ID de su portfolio objetivo a rebalancear | ')

    user_api_key = input('\nPor favor, ingresa el API_KEY de Alpaca | ')
    user__secret_api_key = input('\nPor favor, ingresa la SECRET_KEY de Alpaca | ')

    API_KEY = user_api_key
    SECRET_KEY = user__secret_api_key

    alpaca = REST(API_KEY, SECRET_KEY, 'https://paper-api.alpaca.markets')
    mongo_uri = os.environ['mongo_uri']
    uri = mongo_uri
    DB_name= 'Proyect'
    collection_name='Portfolios'

    portfolio_db  = get_portfolio_db(uri, DB_name, collection_name, user_portfolio_id)
    target_allocations = portfolio_db['Portfolio']
    print('\nEl portfolio objetivo para el rebalanceo es el siguiente\n')
    print(portfolio_db)
    portfolio_symbols = list(target_allocations.keys())

    # Check to Make Sure All Symbols are Eligible for Fractional Trading on Alpaca and Market is Open
    all_symbols_eligible_for_fractionals = _all_symbols_eligible_for_fractionals(portfolio_symbols, alpaca)

    # Setting available cash
    cash_weight = input('\nPor favor, ingrese el porcentaje de efectivo disponible que desea mantener en la cartera (valor entre 0 y 1) | ')
    try: 
        cash_weight = float(cash_weight)
    except:
        cash_weight = input('\nPor favor, ingrese un valor entre 0 y 1 | ')
        cash_weight = float(cash_weight)

    # Ensures All Symbols are Fractionable and the Market is Open
    if all_symbols_eligible_for_fractionals and alpaca.get_clock().is_open:

        # Grab Current Alpaca Holdings
        alpaca_latest_positions = _alpaca_latest_positions(alpaca)

        # Construct a List of Equities to Close Based on Current Alpaca Holdings and Current Desired Holdings
        print("\nClosing Positions...")
        print(20*"~~")
        alpaca_symbols_to_close = _alpaca_symbols_to_close(alpaca_latest_positions, portfolio_symbols)
        
        # Close Any Alpaca Positions if Neccessary
        if alpaca_symbols_to_close:
            alpaca_close_positions(alpaca_symbols_to_close, alpaca)

        # Calculate Rebalance Weight Taking Cash Weight % into Account
        print("Preparing Rebalance Equity...")
        print(20*"~~")
        rebalance_equity = _rebalance_equity(cash_weight, alpaca)
        
        # Allocate the Equity to Each Holding Based on Weight and Available Portfolio Equity
        print("Preparing Positions to Sell and Buy...")
        print(20*"~~")
        portfolio_symbols_equity_allocations = _portfolio_symbols_equity_allocations(target_allocations, rebalance_equity)
        latest_alpaca_positions_allocations = _alpaca_latest_positions_allocations(alpaca)
        positions_to_sell, positions_to_buy = _alpaca_symbols_to_sell_and_buy(portfolio_symbols_equity_allocations, latest_alpaca_positions_allocations)

        # Finally Adjust Allocations 
        print("Rebalancing...")
        print(20*"~~")
        handle_sell_orders(positions_to_sell, alpaca)
        handle_buy_orders(positions_to_buy, alpaca)

        print("Completed Rebalance!")
        print(20*"~~")

if __name__ == "__main__":
    print('\n')
    print(10*'*','REBALANCEO DE CARTERA',10*'*')
    print(' ')
    alpaca_rebalance()