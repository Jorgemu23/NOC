# Version # 1.1

from ratio_filter import get_ratios_db, get_sectors_db, filtrar_datos, modulo1
from pprint import pprint
from pymongo import MongoClient, DESCENDING
import pandas as pd
import numpy as np
import time 
import os 

def get_number_sectors(sector_dict):
    '''
    Gives a dictionary with sectors number:sector
    '''
    num_sector = {}
    for i, sector in enumerate(set(sector_dict.values())):
        num_sector[i] = sector
    return num_sector

def get_sectors_number(sector_dict):
    '''
    Gives a dictionary with sectors sector:number
    '''
    sector_num = {}
    for i, sector in enumerate(set(sector_dict.values())):
        sector_num[sector ] = i
    return sector_num

def sector_filter(interest_companies, sector_num_dict, summary): 
    '''
    '''
    companies_filtered_by_sector ={}
    if len(interest_companies) > 0:
        interes_sectors = []
        while True:
            num_positions = input("\nIngrese la clave del sector de las empresas filtradas que desea incluir o 'salir' para continuar: ")
            if num_positions.lower() == 'salir':
                print("")
                break
            else:
                try:
                    num_positions = int(num_positions)
                    sectors = sector_num_dict[num_positions]
                    print("")
                    print(sectors)
                    interes_sectors.append(sectors)
                except :
                    print("\nEl valor ingresado no es válido. Por favor, ingrese un número")

            if len(interes_sectors)>0:
                resumen = (input("\n¿Deseaun resumen de los ratios filtrados? (Escriba 'si' o 'no') | "))
                if resumen.lower() == 'si':
                    print("")
                    for sector in interes_sectors:
                        print(sector)
                else:
                    pass
            
            companies_filtered_by_sector = {k: v for k, v in interest_companies.items() if v in interes_sectors}

        if len(companies_filtered_by_sector)>0:
            summary_dict = {}
            sector_summary = {'Sectores seleccionados':interes_sectors}
            summary.update(sector_summary)
            summary_dict = {'Resumen': summary}
            summary_sector_list = [companies_filtered_by_sector, summary_dict]
            print('Los activos disponibles son:')
            print('')
            for tk, sector in summary_sector_list[0].items():
                print(f'{tk} - {sector}')
            print('')
            return summary_sector_list
        else:
            print("\n\033[1mNo hay compañias disponibles para los filtros seleccionados\033[0m\n")
            summary_dict = {}
            sector_summary = {'Sectores seleccionados':interes_sectors}
            summary.update(sector_summary)
            summary_dict = {'Resumen': summary}
            return (summary_dict)
    else:
        print("\n\033[1mNo hay compañias disponibles para los filtros seleccionados\033[0m\n")
        return (summary)
    
def modulo2():
    mongo_uri= os.environ['mongo_uri']

    ratios = get_ratios_db(uri = mongo_uri, DB_name= 'Proyect', collection_name='SP500_RATIOS')
    data_date = ratios['_id']
    data_date = time.strftime('%d/%m/%Y', time.localtime(data_date))
    print(f'\nFecha de la obtención de datos: {data_date}\n') # mostramos la fecha en la que se han obtenido los datos
    del ratios['_id'] 

    # guardamos los ratios en un df 
    df_ratios = pd.DataFrame(ratios)
    df_ratios.replace([np.inf, -np.inf], np.nan, inplace=True) # Reemplazamos los valores infinitos por NaN

    # Obtenemos los componentes de los sectores del DB 
    company_sector_dict = get_sectors_db(uri = mongo_uri, DB_name= 'Proyect', collection_name='SECTOR_COMPONENTS')

    # Guardamos los ticker que no estan guardados en el DB ratios y avisamos al usuario que tickers no están disponibles
    tickers_faltantes = set(company_sector_dict.keys()).difference(set(df_ratios.columns))

    print(f"Los siguientes tickers no se encuentran disponibles para realizar el filtrado: \n")
    print(f'{sorted(tickers_faltantes)}')

    # Invocamos la función para realizar el filtrado
    
    filter_summary_list = modulo1()
    filtered_tckr = filter_summary_list[0]
    ratios_summary = filter_summary_list[1]

    number_of_sector = get_number_sectors(sector_dict = company_sector_dict)

    #simulated_output = sample(range(0,len(number_of_sector)),len(number_of_sector))

    print(f'\n\033[1mSectores\033[0m')
    print("----------------------------------------------------------------------")
    for r, P in enumerate(number_of_sector):
        pos = (r+1)
        print(f'\033[1m{r+1})\033[0m {number_of_sector[P]} (clave:{P})')
    print("----------------------------------------------------------------------")

    final_companies = sector_filter(filtered_tckr, number_of_sector, ratios_summary)

    return final_companies
#######################################################################################################################################################
if __name__ == "__main__":

    # mongo_uri= os.environ['mongo_uri']

    # ratios = get_ratios_db(uri = mongo_uri, DB_name= 'Proyect', collection_name='SP500_RATIOS')
    # data_date = ratios['_id']
    # data_date = time.strftime('%d/%m/%Y', time.localtime(data_date))
    # print(f'\nFecha de la obtención de datos: {data_date}\n') # mostramos la fecha en la que se han obtenido los datos
    # del ratios['_id'] 

    # # guardamos los ratios en un df 
    # df_ratios = pd.DataFrame(ratios)
    # df_ratios.replace([np.inf, -np.inf], np.nan, inplace=True) # Reemplazamos los valores infinitos por NaN

    # # Obtenemos los componentes de los sectores del DB 
    # company_sector_dict = get_sectors_db(uri = mongo_uri, DB_name= 'Proyect', collection_name='SECTOR_COMPONENTS')

    # # Guardamos los ticker que no estan guardados en el DB ratios y avisamos al usuario que tickers no están disponibles
    # tickers_faltantes = set(company_sector_dict.keys()).difference(set(df_ratios.columns))

    # print(f"Los siguientes tickers no se encuentran disponibles para realizar el filtrado: \n")
    # print(f'{sorted(tickers_faltantes)}')

    # # Invocamos la función para realizar el filtrado
    
    # filtered_tckr = modulo1()[0]
    # ratios_summary = modulo1()[1]

    # number_of_sector = get_number_sectors(sector_dict = company_sector_dict)

    # simulated_output = sample(range(0,len(number_of_sector)),len(number_of_sector))

    # print(f'\n\033[1mRanking simulado\033[0m')
    # print("----------------------------------------------------------------------")
    # for r, P in enumerate(simulated_output):
    #     pos = (r+1)
    #     print(f'\033[1m{r+1})\033[0m {number_of_sector[P]} (clave:{P})')
    # print("----------------------------------------------------------------------")

    # final_companies = sector_filter(filtered_tckr, number_of_sector, ratios_summary)

    # pprint (final_companies)

    print(modulo2())