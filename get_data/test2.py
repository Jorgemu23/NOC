import requests
import pandas as pd
import time 

token = 'TOKEN'

def get_historical_data(token, ticker):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_MONTHLY_ADJUSTED&symbol={ticker}&apikey={token}&datatype=csv'
    r = requests.get(url)
    data = pd.read_csv(url)
    return data

etf_tickers = ['XLC', 'XLY', 'XLP', 'XLE', 'XLF', 'XLV', 'XLI', 'XLB', 'XLRE', 'XLK', 'XLU']

count=0
for ticker in etf_tickers:
    count+=1
    if count==4:
      time.sleep(120)
      data = get_historical_data(token, ticker)
      data.to_csv(f'{ticker}.csv', index=False)
    else:
      data = get_historical_data(token, ticker)
      data.to_csv(f'{ticker}.csv', index=False)
