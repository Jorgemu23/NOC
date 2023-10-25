# Version # 1.1

# instalar primero pandas == 1.3.4 y luego yahoo_fin
import requests
import pandas as pd
from datetime import datetime
from yahoo_fin.stock_info import tickers_sp500
import numpy as np
from pprint import pprint
import time 
from pymongo import MongoClient
import warnings
import re
import os
warnings.filterwarnings("ignore")

# Definimos las funciones para hacer las llamadas al API y obtener los datos 
def get_company_overview (token, ticker):
    '''
    '''
    url = f'https://www.alphavantage.co/query?function=OVERVIEW&symbol={ticker}&apikey={token}'
    r = requests.get(url)
    data = r.json()
    return data
def get_income_statement (token, ticker): 
    '''
    '''
    url = f'https://www.alphavantage.co/query?function=INCOME_STATEMENT&symbol={ticker}&apikey={token}'
    r = requests.get(url)
    data = r.json()
    return data
def get_balance_sheet(token, ticker):
    '''
    '''
    url = f'https://www.alphavantage.co/query?function=BALANCE_SHEET&symbol={ticker}&apikey={token}'
    r = requests.get(url)
    data = r.json()
    return data

# Expresiones regulares para identificar las claves en el diccionario de la funcio get_stats()
institutions_regex = re.compile(r'% Held by Institutions \d')
short_ratio_regex = re.compile(r'Short Ratio .*')
short_float_regex = re.compile(r'Short % of Float .*')
short_outstanding_regex = re.compile(r'Short % of Shares Outstanding .*')
forward_dividend_rate_regex = re.compile(r'Forward Annual Dividend Rate')
trailing_dividend_rate_regex = re.compile(r'Trailing Annual Dividend Rate')
avg_dividend_yield_regex = re.compile(r'5 Year Average Dividend Yield')
payout_ratio_regex = re.compile(r'Payout Ratio')
revenue_per_share_regex = re.compile(r'Revenue Per Share .*')
total_cash_per_share_regex = re.compile(r'Total Cash Per Share .*')

def get_stats(ticker, headers={'User-agent': 'Mozilla/5.0'}):
    '''Scrapes information from the statistics tab on Yahoo Finance 
       for an input ticker and returns a dictionary with the specified ratios
       using regular expressions to match the dictionary keys
    
       @param: ticker
    '''
    stats_site = "https://finance.yahoo.com/quote/" + ticker + \
                 "/key-statistics?p=" + ticker

    tables = pd.read_html(requests.get(stats_site, headers=headers).text)
    tables = [table for table in tables[1:] if table.shape[1] == 2]
    table = pd.concat(tables)
    table = table.set_index(0).T
    
    # Selección de los ratios por medio de las expresiones regulares
    selected_ratios = {'Symbol':ticker}
    
    for key, value in table.items():
        if institutions_regex.match(key):
            selected_ratios[key] = value.values[0]
        elif short_ratio_regex.match(key):
            selected_ratios[key] = value.values[0]
        elif short_float_regex.match(key):
            selected_ratios[key] = value.values[0]
        elif short_outstanding_regex.match(key):
            selected_ratios[key] = value.values[0]
        elif forward_dividend_rate_regex.match(key):
            selected_ratios[key] = value.values[0]
        elif trailing_dividend_rate_regex.match(key):
            selected_ratios[key] = value.values[0]
        elif avg_dividend_yield_regex.match(key):
            selected_ratios[key] = value.values[0]
        elif payout_ratio_regex.match(key):
            selected_ratios[key] = value.values[0]
        elif revenue_per_share_regex.match(key):
            selected_ratios[key] = value.values[0]
        elif total_cash_per_share_regex.match(key):
            selected_ratios[key] = value.values[0]
            
    return selected_ratios

# Creamos un diccionario con los patrones de las claves originales y los nombres nuevos
def ratios_names(stats_dictt):
    patterns = {
        '.*% Held by Institutions.*': 'HeldByInstitutions',
        'Short Ratio.*': 'ShortRatio',
        'Short % of Float.*': 'Short%Float',
        'Short % of Shares Outstanding.*': 'Short%SharesOutstanding',
        'Forward Annual Dividend Rate.*': 'ForwardDividendRate',
        'Trailing Annual Dividend Rate.*': 'TrailingDividendRate',
        '5 Year Average Dividend Yield.*': '5YrAverageDividendYield',
        'Payout Ratio.*': 'Payout',
        'Revenue Per Share \(ttm\).*': 'RevenuePerShareTTM',
        'Total Cash Per Share \(mrq\).*': 'TotalCashPerShareMRQ'
    }
    first_dict = {}
    for k, v in stats_dictt.items():
        for pattern, name in patterns.items():
            if re.match(pattern, k):
                first_dict[name] = v
                break
        else:
            first_dict[k] = v
            
    return first_dict

# Cambiamos los valors str a fomrato numerico 
def str_to_number(first_dict):
    final_dict = {}
    valor_num = np.nan
    for ratio, str_value in first_dict.items():
        try:
            if ratio == 'Symbol':
                pass
            elif type(str_value) == float:
                valor_num == np.nan
            elif '%' in str_value:
                valor_num = float(str_value.replace(',', '.').replace('%', '')) / 100
            else: 
                valor_num = float(str_value)
        except: 
            print(f'Error en el ticker {first_dict.Symbol} en el ratio {ratio} no se ha asignado valor')
        
        final_dict[ratio] = valor_num
        final_dict['Symbol'] = first_dict['Symbol']
    return final_dict

# Definimos las funciones para calcular algunos ratios 
def current_ratio(dict_BS):
    '''
    '''
    try:
        tk = dict_BS['symbol']
        df_BS = pd.DataFrame(dict_BS['annualReports'])
        cols_numericas = ['totalCurrentAssets','totalCurrentLiabilities']
        df_BS = pd.DataFrame(dict_BS['annualReports'])
        df_BS[cols_numericas] = df_BS.loc[:,cols_numericas].apply(pd.to_numeric, errors='coerce').fillna(0)
        current_assets = df_BS.loc[0,'totalCurrentAssets']
        current_liabilities = df_BS.loc[0,'totalCurrentLiabilities']
        current_liquidity_ratio = current_assets/ current_liabilities
        return {tk :{'CurrentLiquidityRatio':current_liquidity_ratio}}
    except:
        tk = None
        current_liquidity_ratio= np.nan
        return {tk:{'CurrentLiquidityRatio':current_liquidity_ratio}}

def acid_test_ratio(dict_BS): 
    '''
    '''

    try:
        tk = dict_BS['symbol']
        df_BS = pd.DataFrame(dict_BS['annualReports'])
    
        cols_numericas = ['cashAndCashEquivalentsAtCarryingValue', 'currentDebt']
        df_BS[cols_numericas] = df_BS.loc[0,cols_numericas].apply(pd.to_numeric, errors='coerce').fillna(0)
        cash_cash_equivalent = df_BS.loc[0,'cashAndCashEquivalentsAtCarryingValue']
        currentNetReceivables = df_BS.loc[0,'currentNetReceivables']
        current_liabilities = df_BS.loc[0,'currentDebt']
        currentAccountsPayable = df_BS.loc[0,'currentAccountsPayable']
        acid_test_ratio = (cash_cash_equivalent + currentNetReceivables) / (current_liabilities + currentAccountsPayable)
        return{tk :{'AcidTestRatio':acid_test_ratio}}
    except:
        tk = None
        acid_test_ratio= np.nan
        return {tk:{'AcidTestRatio':acid_test_ratio}}

def total_debt_ratio(dict_BS):
    '''
    '''
    try:
        tk = dict_BS['symbol']
        df_BS = pd.DataFrame(dict_BS['annualReports'])
        cols_numericas = ['totalAssets','totalLiabilities']
        df_BS[cols_numericas] = df_BS.loc[0,cols_numericas].apply(pd.to_numeric, errors='coerce').fillna(0)
        assets = df_BS.loc[0,'totalAssets']
        liabilities = df_BS.loc[0,'totalLiabilities']
        debt_ratio = liabilities/ assets
        return {tk :{'TotalDebtRatio':debt_ratio}}
    except:
        tk = None
        debt_ratio= np.nan
        return {tk:{'TotalDebtRatio':debt_ratio}}

    
def long_term_debt_ratio(dict_BS): 
    '''
    '''
    try:
        tk = dict_BS['symbol']
        df_BS = pd.DataFrame(dict_BS['annualReports'])
        cols_numericas = ['longTermDebt', 'totalShareholderEquity']
        df_BS[cols_numericas] = df_BS.loc[0,cols_numericas].apply(pd.to_numeric, errors='coerce').fillna(0)
        deuda_largo_plazo = df_BS.loc[0,'longTermDebt']
        capitalizacion_total = df_BS.loc[0,'totalShareholderEquity'] + deuda_largo_plazo
        long_term_debt = deuda_largo_plazo / capitalizacion_total
        return {tk :{'LongTermDebtRatio':long_term_debt}}
    except: 
        long_term_debt= np.nan
        tk = None
        return {tk:{'LongTermDebtRatio':long_term_debt}}

    
def interest_coverage_ratio(dict_IS):
    '''
    '''
    try:
        tk = dict_IS['symbol']
        df_IS = pd.DataFrame(dict_IS['annualReports'])
        cols_numericas = ['ebit', 'interestExpense']
        df_IS[cols_numericas] = df_IS.loc[0,cols_numericas].apply(pd.to_numeric, errors='coerce').fillna(0)
        ebit = df_IS.loc[0,'ebit']
        interest = df_IS.loc[0,'interestExpense']
        coverage = ebit / interest
        return {tk :{'InterestCoverRatio':coverage}}
    except:
        tk = None
        coverage= np.nan
        return {tk:{'InterestCoverRatio':coverage}}

def gross_margin(dict_IS):
    '''
    '''

    try:
        tk = dict_IS['symbol']
        df_IS = pd.DataFrame(dict_IS['annualReports'])
        cols_numericas = ['totalRevenue', 'costOfRevenue']
        df_IS[cols_numericas] = df_IS.loc[0,cols_numericas].apply(pd.to_numeric, errors='coerce').fillna(0)
        revenue = df_IS.loc[0,'totalRevenue']
        cost_of_goods = df_IS.loc[0,'costOfRevenue']
        gross_margin = (revenue - cost_of_goods) / revenue
        return {tk :{'GrossMargin':gross_margin}}
    except:
        tk = None
        gross_margin= np.nan
        return {tk:{'GrossMargin':gross_margin}}

      
def inventory_turnover_ratio(dict_BS, dict_IS):
    '''
    '''

    try:
        tk = dict_IS['symbol']
        df_BS = pd.DataFrame(dict_BS['annualReports'])
        df_IS = pd.DataFrame(dict_IS['annualReports'])
        cols_numericas = ['inventory']
        df_BS[cols_numericas] = df_BS.loc[0,cols_numericas].apply(pd.to_numeric, errors='coerce').fillna(0)
        cols_numericas = ['costOfRevenue']
        df_IS[cols_numericas] = df_IS.loc[0,cols_numericas].apply(pd.to_numeric, errors='coerce').fillna(0)
        avg_inventory = df_BS['inventory'].sum() / len(df_BS)
        cost_of_sales = df_IS.loc[0, 'costOfRevenue']
        inventory_turnover = cost_of_sales / avg_inventory
        return {tk :{'InventoryTrunoverRatio':inventory_turnover}}
    except:
        tk = None
        inventory_turnover= np.nan
        return {tk:{'InventoryTrunoverRatio':inventory_turnover}}
        
def expenses_ratio_id(dict_IS):
    """
    Función que calcula el ratio de Gastos de Investigación y Desarrollo (I+D)
    
    Parameters:
    df (pandas.DataFrame): DataFrame con los datos financieros de la compañía (Income Statement)
    
    Returns:
    float: Valor del ratio de Gastos de Investigación y Desarrollo (I+D)
    """

    try:
        tk = dict_IS['symbol']
        df_IS = pd.DataFrame(dict_IS['annualReports'])
        cols_numericas = ['researchAndDevelopment', 'totalRevenue']
        df_IS[cols_numericas] = df_IS.loc[0,cols_numericas].apply(pd.to_numeric, errors='coerce').fillna(0)
        rd_expenses = df_IS.loc[0,'researchAndDevelopment']
        sales = df_IS.loc[0,'totalRevenue']
        ratio_id = rd_expenses / sales
        return {tk :{'I+DRatio':ratio_id}}
    except: 
        tk = None
        ratio_id= np.nan
        return {tk:{'I+DRatio':ratio_id}}

# Obtenemos datos de los proveedores de datos y los guardamos en lista
sp500_tkr = tickers_sp500()
token = os.environ['alpha_key']
yahoo_list = []
overview_list = []
BS_list = []
IS_list= []
tk_error_list = []
count = 0

for tk in sp500_tkr:    
    time.sleep(5) 
    try:
        stats_dict = get_stats(tk)
        first_dict = ratios_names(stats_dict)
        yahoo_dict = str_to_number(first_dict)
        yahoo_list.append(yahoo_dict)
        print(f'Getting stats data from Yahoo for {tk}') 
    except:
        try:
            time.sleep(120) 
            stats_dict = get_stats(tk)
            first_dict = ratios_names(stats_dict)
            yahoo_dict = str_to_number(first_dict)
            yahoo_list.append(yahoo_dict)
            print(f'Getting stats data from Yahoo for {tk}')  
        except Exception as e :
            print(f' Error {e} in Yahoo Stats for ticker {tk}')
    try:
        data = get_company_overview(token, tk)
        
        if 'Symbol' in data.keys():
            overview_list.append(data)
            count += 1 
            print(f'Getting company overview data from alphavantage for {tk}')
            if count == 29:
                time.sleep(65)
                count = 0 
        else:
            tk_error_list.append(tk)
    except Exception as e:
        print(f' error {e }in alphavantage company overview for ticker {tk}')
    try:
        IS = get_income_statement(token, tk)
        if 'symbol' in IS.keys():
            IS_list.append(IS)
            count += 1 
            print(f'Getting company income statement data from alphavantage for {tk}')
            if count == 29:
                time.sleep(65)
                count = 0
        else:
            tk_error_list.append(tk)
    except Exception as e: 
        print(f' error {e} in alphavantage income statement for ticker {tk}')
    try:
        BS = get_balance_sheet(token, tk)
        if 'symbol' in BS.keys():
            BS_list.append(BS)
            count += 1 
            print(f'Getting company balance sheet data from alphavantage for {tk}')
            if count == 29:
                time.sleep(65)
                count = 0
        else:
            tk_error_list.append(tk)
    except Exception as e:
        print(f' error {e} in alphavantage balance sheet for ticker {tk}')

#print(yahoo_list)
tk_error_list_def = []
if len(tk_error_list) > 0:
    
    time.sleep(60*5)
    count = 0
    tk_error_list = list(set(tk_error_list))
    print(tk_error_list)
    for tk_faltante in tk_error_list:
        try:
            data = get_company_overview(token, tk_faltante)
            if 'Symbol' in data.keys():
                overview_list.append(data)
                count += 1 
                print(f'Getting company overview data from alphavantage for {tk_faltante}')
                if count == 29:
                    time.sleep(65)
                    count = 0 
            else:
                tk_error_list_def.append(tk_faltante)
        except Exception as e:
            print(f' error {e }in alphavantage company overview for ticker {tk_faltante}')
        try:
            IS = get_income_statement(token, tk_faltante)
            if 'symbol' in IS.keys():
                IS_list.append(IS)
                count += 1 
                print(f'Getting company income statement data from alphavantage for {tk_faltante}')
                if count == 29:
                    time.sleep(65)
                    count = 0
            else:
                tk_error_list_def.append(tk_faltante)
        except Exception as e: 
            print(f' error {e} in alphavantage income statement for ticker {tk_faltante}')
        try:
            BS = get_balance_sheet(token, tk_faltante)
            if 'symbol' in IS.keys():
                BS_list.append(BS)
                count += 1 
                print(f'\nGetting company balance sheet data from alphavantage for {tk_faltante}')
                print(f'Ticker obtenido: {BS["symbol"]}')
                if count == 29:
                    time.sleep(65)
                    count = 0
            else:
                tk_error_list_def.append(tk_faltante)
        except Exception as e:
            print(f' error {e} in alphavantage balance sheet for ticker {tk_faltante}')

# Creamos una lista con los ratios obtenidos 
overview_ratios = ['PERatio', 'PEGRatio', 
               'DividendPerShare', 'EPS', 
               'QuarterlyEarningsGrowthYOY', 'PriceToSalesRatioTTM',
               'PriceToBookRatio', 'EVToRevenue', 
               'EVToEBITDA', 'Beta', 'DividendYield', 'ProfitMargin', 'OperatingMarginTTM', 
               'ReturnOnAssetsTTM', 'ReturnOnEquityTTM', 'DilutedEPSTTM', 'QuarterlyRevenueGrowthYOY']

# # Guardamos en una lista de diccionarios los ratios obtenidos del IS y BS 
IS_BS_list_dicct=[]
for IS, BS in zip(IS_list, BS_list):
    #IS_BS_dict = {}
    cr =  current_ratio(BS)
    atr = acid_test_ratio(BS)
    tdr = total_debt_ratio(BS)
    ltdr= long_term_debt_ratio(BS)
    ict =interest_coverage_ratio(IS)
    gm  =gross_margin(IS)
    er =expenses_ratio_id(IS)
    itr =inventory_turnover_ratio(BS, IS)  
    IS_BS_list_dicct.append(cr)
    IS_BS_list_dicct.append(atr)
    IS_BS_list_dicct.append(tdr)
    IS_BS_list_dicct.append(ltdr)
    IS_BS_list_dicct.append(ict)
    IS_BS_list_dicct.append(gm)
    IS_BS_list_dicct.append(er)
    IS_BS_list_dicct.append(itr)


# cambiar orden para que yahoo fin sea el primero y luego alphabentage
# En caso de camnbio quitar las lineas que eliminan de la lista el ticker faltante 

if len(tk_error_list_def) > 0:
    print ('Los ticker faltantes son:')
    for tkr in tk_error_list_def:
        print(tkr)
    sp500_tkr = [x for x in sp500_tkr if x not in tk_error_list_def]
ratios_dict = {}

for tk in sp500_tkr:
    for dictt in overview_list:
        if dictt['Symbol'] == tk:
            o_dictt = {clave: (np.nan if valor in ('-', 'None') else float(valor)) for clave, valor in dictt.items() if clave in overview_ratios}
            ratios_dict[tk] = o_dictt

    for d in yahoo_list:
        if d['Symbol'] == tk:
            y_dict = d.copy()
            y_dict.pop('Symbol', None)
            ratios_dict[tk].update(y_dict)

    for d in IS_BS_list_dicct:
        if tk in d.keys():
            ratios_dict[tk].update(d[tk])

# Guardamos los ratios en DB mongo 'SP500_RATIOS'
today_date = datetime.now()
timestamp = int(time.time())
id_dicc = {'_id':timestamp }
ratios_dict.update(id_dicc)
uri = os.environ['mongo_uri']
client = MongoClient(uri)
db = client['Proyect']
collection = db['SP500_RATIOS']
collection.insert_one(ratios_dict)

pprint(ratios_dict)


    

# Guardar en otra collection toda la info overview de las empresas

# for overview_dict in overview_list:
    # timestamp = int(time.time())
    # id_dicc = {'_id':timestamp }
    # overview_dict.update(id_dicc)
    # uri = os.environ['mongo_uri']
    # client = MongoClient(uri)
    # db = client['Proyect']
    # collection = db['SP500_RATIOS']
    # collection.insert_one(ratios_dict)