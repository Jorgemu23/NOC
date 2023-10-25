# Version # 1.1

import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from pathlib import Path 
from yahoo_fin.stock_info import tickers_sp500
import time
import os
# Conexión a MongoDB Atlas
uri = os.environ['mongo_uri']
client = MongoClient(uri)

db = client['Proyect']
collection = db['SECTOR_COMPONENTS']
fdir = Path('data/sector_data')

if not fdir.exists():
    raise ValueError('Directorio de datos no encontrado')

# cargamos los csv con los componentes de cada sector
comunication_service = pd.read_csv(fdir/'comunication_service.csv', header=1) 
consumer_discretionary = pd.read_csv(fdir/"consumer_discretionary.csv", header=1) 
consumer_staples = pd.read_csv(fdir/"consumer_staples.csv", header=1) 
energy = pd.read_csv(fdir/"energy.csv", header=1) 
financials = pd.read_csv(fdir/"financials.csv", header=1) 
health_care = pd.read_csv(fdir/"health_care.csv", header=1) 
industrials = pd.read_csv(fdir/"industrials.csv", header=1) 
materials = pd.read_csv(fdir/"materials.csv", header=1) 
real_state = pd.read_csv(fdir/"real_state.csv", header=1)
technology = pd.read_csv(fdir/"technology.csv", header=1)
utilities = pd.read_csv(fdir/"utilities.csv", header=1)

sp500_tkr = tickers_sp500()
#sp500_tkr = [ticker.replace('-', '.') for ticker in sp500_tkr]

sector_dicc = {}
for tk in sp500_tkr:
    if tk in comunication_service.Symbol.values:
        sector_dicc[tk]= 'Comunication Service'
    elif tk in consumer_discretionary.Symbol.values:
        sector_dicc[tk]= 'Consumer Discretionary'
    elif tk in consumer_staples.Symbol.values:
        sector_dicc[tk]= 'Consumer Staples'
    elif tk in energy.Symbol.values:
        sector_dicc[tk]= 'Energy'
    elif tk in financials.Symbol.values:
        sector_dicc[tk]= 'Financials'
    elif tk in health_care.Symbol.values:
        sector_dicc[tk]= 'Health Care'
    elif tk in industrials.Symbol.values:
        sector_dicc[tk]= 'Industrials'
    elif tk in materials.Symbol.values:
        sector_dicc[tk]= 'Materials'
    elif tk in real_state.Symbol.values:
        sector_dicc[tk]= 'Real State'
    elif tk in technology.Symbol.values:
        sector_dicc[tk]= 'Technology'
    elif tk in utilities.Symbol.values:
        sector_dicc[tk]= 'Utilities'
    else: 
      print (f' This ticker is not in the SPDR {tk} ETFs sector')  

## Guardamos los componentes de los sectores en la base de datos MONGO 'PROYECT' coleccion SECTOR_COMPONENTS  

today_date = datetime.now()
timestamp = int(time.time())
dicc = {'_id':timestamp }
sector_dicc.update(dicc)
collection.insert_one(sector_dicc)

print(dicc)