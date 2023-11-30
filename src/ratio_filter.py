# Version # 1.1

from pymongo import MongoClient, DESCENDING
from pprint import pprint
import pandas as pd
import numpy as np 
import warnings
from tabulate import tabulate
import time 
import os
warnings.filterwarnings('ignore', '.*Boolean Series key will be reindexed.*')

# Funciones para esblecer Conexión a MongoDB Atlas
def get_ratios_db (uri, DB_name, collection_name):
    '''
    '''
    uri = uri
    client = MongoClient(uri)
    db = client[DB_name]
    collection_ratios = db[collection_name]
    result = collection_ratios.find_one(sort=[('_id', DESCENDING)])
    ratios = result
    return ratios

# Seleccionamos la base de datos y la colección 'SECTOR_COMPONENTS' para guardar los componentes de los sectores en un diccionario
def get_sectors_db (uri, DB_name, collection_name):
    uri = uri
    client = MongoClient(uri)
    db = client[DB_name]
    collection_sector = db[collection_name]
    result = collection_sector.find_one(sort=[('_id', DESCENDING)])
    sector_dict = result
    del sector_dict['_id']
    return sector_dict

def filtrar_datos(df, dicc):
    """
    Función que filtra un DataFrame con ratios financieros en función de los filtros especificados por el usuario.

    Args:
    df: pandas DataFrame con ratios y tickers de empresas
    dicc: diccionario con las empresas como key y los sectores como valor

    Returns:
    diccionario con las empresas y sectores que cumplen los filtros
    """
    lista_ratios = df.index.values
    max_ratio = ['ShortRatio', 'Short%Float', 'Short%SharesOutstanding', 'TotalDebToEquityMRQ', 'PERatio', 'PEGRatio',
              'PriceToSalesRatioTTM', 'PriceToBookRatio', 'EVToRevenue', 'EVToEBITDA', 'TotalDebtRatio', 'LongTermDebtRatio','I+DRatio']
    filtros_dict_list = [] # cambiar nombre por filtros_dict_list
    ratio_1 = 0
    valor_1= 0 
    ratio_2 = 0
    valor_2 = 0

    print(f'\n\033[1mLos ratios disponibles son:\033[0m')
    print("----------------------------------------------------------------------")

    for i, (a, b) in enumerate(zip(lista_ratios[::2], lista_ratios[1::2]), start=1):
        print(f"\033[1m{i*2-1}.\033[0m {a:<35}", end="")
        if b:
            print(f"\033[1m{i*2}.\033[0m {b:<20}")
        else:
            print()
    print("----------------------------------------------------------------------")
    # Preguntar al usuario si quiere la descripción de algún ratio
    ratios={'Beta':['Sensibilidad de un activo financiero en relación con el mercado en general.','\n- Un activo con un beta de 1 significa que se mueve en línea con el mercado.\n- Un beta superior a 1 indica que el activo es más volátil que el mercado. \n- Un beta inferior a 1 indica que es menos volátil que el mercado.','El valor del ratio beta se calcula comparando la variación porcentual en el precio de un activo con la variación porcentual en el precio del mercado de referencia.'],
        '%HeldByInstitutions':['Porcentaje de acciones de una empresa que son propiedad de inversores institucionales.','Indica el nivel de confianza que los inversores institucionales tienen en la empresa. Un alto porcentaje de propiedad institucional es visto como una señal positiva ya que sugiere que los inversores profesionales confían en la empresa.','% de instituciones = (acciones de instituciones / número total de acciones en circulación).'],
        'ShortRatio':['Relación entre el número de acciones vendidas en corto y el volumen promedio diario de negociación de esas acciones en los últimos 30 días. Puede utilizarse para evaluar la cantidad de interés de los inversores en corto en una determinada acción y cuánto tiempo podría tardar en cubrir sus posiciones cortas.','\n- Un ratio alto indica que hay muchos inversores que han tomado posiciones en corto. \n- Un ratio bajo indica que hay pocos inversores que han tomado posiciones cortas. \n- Por encima de 5 se puede consider alto. \n- Por debajo de 2 se puede consider bajo.','Se calcula dividiendo el número total de acciones vendidas en corto por el volumen promedio diario de negociación de esas acciones en los últimos 30 días. El resultado se expresa en días.'],
        'Short%Float':['Porcentaje de acciones de una empresa que están siendo vendidas en corto en relación con el número total de acciones disponibles para el comercio público.','Se utiliza para evaluar la opinión del mercado sobre las perspectivas futuras de una empresa: \n- Un ratio alto indica que los inversores tienen una opinión negativa sobre la empresa. \n- Un ratio bajo indica una opinión positiva del mercado sobre las perspectivas futuras de una empresa.','Se calcula dividiendo el número de acciones vendidas en corto por el número de acciones en circulación o "float" de la empresa.'],
        'Short%SharesOutstanding':['Porcentaje de acciones en circulación de una empresa que han sido vendidas en corto en relación con el número total de acciones en circulación.','Se utiliza para evaluar la opinión del mercado sobre las perspectivas futuras de una empresa: \n- Un ratio alto indica que los inversores tienen una opinión negativa sobre la empresa.\n- Un ratio bajo indica una opinión positiva del mercado sobre las perspectivas futuras de una empresa.','Se calcula dividiendo el número de acciones vendidas en corto por el número total de acciones.'],
        'ForwardDividendRate':['Tasa de dividendos anuales esperados para una empresa en el futuro.','Un ratio alto indica que una empresa tiene una política de dividendos sólida y estable, y que los inversores pueden esperar recibir una cantidad significativa de ingresos por dividendos en el futuro.','Se calcula multiplicando el dividendo por acción actual por el número de acciones en circulación y luego anualizando el resultado.'],
        'TrailingDividendRate':['Monto total de los dividendos pagados por una empresa durante los últimos 12 meses.','Medida útil para los inversores que buscan ingresos regulares de dividendos en sus inversiones y quieren saber cuánto ha pagado la empresa en dividendos en el último año.','Se calcula sumando todos los dividendos pagados por la empresa durante los últimos cuatro trimestres.'],
        '5YrAverageDividendYield':['Promedio del rendimiento de dividendos de una empresa durante los últimos cinco años fiscales.','Un ratio alto es una señal positiva para los inversores que buscan una empresa estable que haya sido capaz de mantener y/o aumentar sus dividendos a lo largo del tiempo.','Se calcula sumando los rendimientos de dividendos de los últimos cinco años y se divide el resultado por cinco. Luego, se divide por el precio actual de la acción.'],
        'Payout':['Es la proporción de las ganancias de una empresa que se distribuyen a los accionistas en forma de dividendos.','\n- Un ratio alto indica que la empresa está distribuyendo una gran proporción de sus ganancias como dividendos. \n- Un ratio bajo indica que la empresa está reteniendo una gran parte de sus ganancias.','Se calcula dividiendo el dividendo anual por acción de la empresa entre las ganancias anuales por acción.'],
        'ProfitMargin':['Porcentaje de ganancias que una empresa obtiene por cada dólar de ingresos generados. Mide la eficiencia de una empresa en la gestión de sus costos y la generación de beneficios.','\n- Un ratio alto indica que la empresa está gestionando sus costos de manera efectiva y generando un beneficio saludable en relación con sus ingresos. \n- Un ratio bajo indica que la empresa está teniendo dificultades para gestionar sus costos y/o que está enfrentando presiones competitivas en su industria.','Se calcula dividiendo la utilidad neta de la empresa por sus ingresos totales.'],
        'OperatingMarginTTM':['Porcentaje de ingresos de una empresa que se convierten en ganancias antes de los impuestos, los intereses y otros gastos no relacionados con la operación de la empresa. Mide la eficiencia de una empresa en la gestión de sus costos y la generación de ganancias a través de sus operaciones principales.','\n- Un ratio alto indica que la empresa está gestionando sus costos de manera efectiva y generando ganancias saludables a través de sus operaciones principales. \n- Un ratio bajo indica que la empresa está teniendo dificultades para gestionar sus costos y/o que está enfrentando presiones competitivas en su industria.','Se calcula dividiendo el EBIT de la empresa por sus ingresos totales .'],
        'ROATTM':['Capacidad de una empresa para generar ganancias a partir de sus activos totales.','\n- Un ratio alto indica que la empresa está utilizando de manera eficiente sus activos para generar ganancias y es una señal de una gestión efectiva de los recursos empresariales. \n- Un ratio bajo indica que la empresa está luchando para generar ganancias a partir de sus activos.','Se calcula dividiendo el beneficio neto de la empresa por sus activos totales.'],
        'ROETTM':['Rentabilidad de una empresa en términos de la cantidad de beneficio que genera en relación con el capital invertido por sus accionistas.','\n- Un ratio alto alto indica que la empresa está utilizando de manera efectiva el capital de sus accionistas para generar ganancias. \n- Un ratio bajo indica que la empresa está luchando para generar ganancias a partir del capital de sus accionistas.','Se calcula dividiendo el beneficio neto de la empresa por su capital contable.'],
        'RevenuePerShareTTM':['Es la cantidad de ingresos generados por una empresa por cada acción en circulación.','\n- Un ratio alto indica que la empresa está generando una gran cantidad de ingresos por cada acción en circulación. \n- Un ratio bajo indica indicar que la empresa está luchando para generar ingresos.','Se calcula dividiendo los ingresos totales de la empresa por el número de acciones en circulación.'],
        'QuarterlyRevenueGrowthYOY':['Crecimiento de los ingresos de una empresa durante un trimestre específico en comparación con el mismo trimestre del año anterior.','\n- Un ratio positivo indica que la empresa ha experimentado un crecimiento en sus ingresos en comparación con el año anterior. \n- Un ratio negativo indica que los ingresos de la empresa han disminuido en comparación con el mismo trimestre del año anterior','Quarterly Revenue Growth (yoy) = ((Ingresos del trimestre actual - Ingresos del mismo trimestre del año anterior) / Ingresos del mismo trimestre del año anterior)'],
        'DilutedEpsTTM':['Ganancia que la empresa ha obtenido en doce meses dividido por el número total de acciones en circulación, incluyendo las acciones que podrían ser emitidas en el futuro en caso de que los instrumentos convertibles, como las opciones sobre acciones, sean ejercidas.','\n- Un ratio positivo indica que la empresa ha obtenido nouna ganancia en los últimos doce meses. \n- Un ratio negativo significa que la empresa ha perdido dinero en los últimos doce meses.','Diluted EPS (ttm) = (Ganancias Netas - Dividendos sobre Acciones Preferentes) / Acciones Diluidas en Circulación'],
        'TotalCashPerShareMRQ':['Muestra cuánto efectivo tiene disponible la empresa por cada acción en circulación.','Un ratio alto significa que la empresa tiene una mayor capacidad financiera para financiar su crecimiento, invertir en nuevos proyectos o pagar dividendos a los accionistas.','La cantidad total de efectivo y equivalentes de efectivo que una empresa tiene en su balance dividido por el número total de acciones en circulación en el mercado.'],
        'PERatio':['Mide la relación entre el precio de mercado de una acción y sus ganancias por acción (EPS).','\n- Un ratio alto indica que los inversores están dispuestos a pagar más por cada dólar de ganancias que la empresa genera. \n- Un ratio bajo puede indicar que la empresa está subvalorada en el mercado.','PER = Precio actual de las acciones / Ganancias por acción (EPS)'],
        'PEGRatio':['Relaciona el precio de la acción de una empresa con sus ganancias y su tasa de crecimiento esperada.','\n- Un Ratio de 1 indica que suel precio de la acción está alineado con la tasa de crecimiento esperada. \n- Un Ratio mayor que 1, puede indicar que la acción está sobrevalorada en relación a su tasa de crecimiento \n- Un Ratio menor que 1 podría indicar que la acción está subvalorada en relación a su tasa de crecimiento.','Se calcula dividiendo el P/E Ratio (Price/Earnings Ratio) de una empresa por su tasa de crecimiento anual estimada en ganancias.'],
        'DividendPerShare':['Mide la cantidad de dinero que una empresa paga a sus accionistas en dividendos por cada acción en circulació.','\n- Un ratio alto indica que la empresa está pagando un mayor porcentaje de sus ganancias a los accionistas en forma de dividendos. \n- Un ratio bajo puede indicar que la empresa está reteniendo más ganancias para reinvertir en el negocio o pagar deudas.','Dividend Per Share = Total de dividendos pagados / Número de acciones en circulación'],
        'EPS':['Muestra las ganancias netas que una empresa ha generado durante un periodo determinado, dividido por el número de acciones en circulación de la empresa.','\n- Un ratio alto indica que la empresa está generando beneficios importantes, puede ser un indicativo de un crecimiento saludable y sostenible. \n- Un ratio bajo puede indicar que la empresa está luchando por generar beneficios.','EPS = Ganancias netas / Número de acciones en circulación'],
        'QuarterlyEarningsGrowthYOY':['Mide el crecimiento de las ganancias de una empresa en un trimestre específico en comparación con el mismo trimestre del año anterior.','\n- Un ratio positivo indica que la empresa está creciendo en términos de ganancias en comparación con el mismo trimestre del año anterior. \n- Un ratio negativo indica que las ganancias han disminuido en comparación con el mismo trimestre del año anterior.','Quarterly Earnings Growth YOY = (Ganancias del trimestre actual - Ganancias del mismo trimestre del año anterior) / Ganancias del mismo trimestre del año anterior'],
        'PriceToSalesRatioTTM':['Se utiliza para evaluar el valor de mercado de una empresa en relación con sus ventas.','\n- Un ratio alto indica que los inversores están dispuestos a pagar un precio elevado por cada dólar de ventas que obtiene la empresa, lo que puede indicar que está sobrevalorada. \n- Un ratio bajo indica que los inversores no están dispuestos a pagar un precio elevado por cada dólar de ventas de la empresa, lo que puede indicar que  está infravalorada.','P/S Ratio = Precio de la acción / Ventas por acción'],
        'PriceToBookRatio':['Se utiliza para evaluar el valor de mercado de una empresa en relación con su valor contable o patrimonio neto.','\n- Un ratio alto indica que los inversores están dispuestos a pagar un precio elevado por cada dólar de valor contable de la empresa, puede indicar que la empresa está sobrevalorada. \n- Un ratio bajo indica que los inversores no están dispuestos a pagar un precio elevado por cada dólar de valor contable de la empresa, puede indicar que la empresa está infravalorada.','P/B ratio = Precio de mercado por acción / Valor contable por acción'],
        'EVToRevenue':['El ratio es un indicador financiero que se utiliza para evaluar el valor de mercado de una empresa en relación con sus ingresos. El EV es una medida que representa el valor total de mercado de una empresa, que incluye tanto el valor de mercado de las acciones como el valor de mercado de la deuda.','\n- Un ratio alto indica que los inversores están dispuestos a pagar un precio elevado por cada dólar de ingresos que obtiene la empresa, lo que puede indicar que está sobrevalorada. \n- Un ratio bajo indica indicar que los inversores no están dispuestos a pagar un precio elevado por cada dólar de ingresos de la empresa, lo que puede indicar que  está infravalorada.','EVToRevenue = Enterprise Value / Revenue'],
        'EVToEBITDA':['Se utiliza para evaluar el valor de mercado de una empresa en relación con su flujo de efectivo operativo.','\n- Un ratio alto indica que los inversores están dispuestos a pagar un precio elevado por cada dólar de flujo de efectivo operativo que obtiene la empresa, lo que puede indicar que la empresa está sobrevalorada. \n- Un ratio bajo indica que los inversores no están dispuestos a pagar un precio elevado por cada dólar de flujo de efectivo operativo de la empresa, lo que puede indicar que la empresa está infravalorada.','EV/EBITDA = (Valor de la empresa + Deuda neta - Efectivo y equivalentes de efectivo) / EBITDA'],
        'CurrentLiquidityRatio':['Mide la capacidad de una empresa para pagar sus obligaciones a corto plazo. Compara los activos circulantes de una empresa con sus pasivos circulantes.','\n- Un ratio alto indica que la empresa tiene suficientes activos circulantes para cubrir sus pasivos circulantes y que tiene una buena posición de liquidez. \n- Un ratio bajo puede indicar que la empresa puede tener dificultades para pagar sus deudas a corto plazo.','Curren liquidity ratio = current assets/ current liabilities'],
        'AcidTestRatio':['Es una medida de la liquidez de una empresa que mide su capacidad para pagar sus obligaciones a corto plazo utilizando solo sus activos líquidos más inmediatos, como el efectivo, los equivalentes de efectivo y las cuentas por cobrar.','\n- Un ratio alto indica que la empresa tiene una buena capacidad para pagar sus obligaciones a corto plazo utilizando sólo sus activos líquidos más inmediato. \n- Un ratio bajo indica que la empresa podría tener dificultades para hacer frente a sus obligaciones a corto plazo si se produce una caída en sus ingresos o aumentos en sus gastos.','AcidTestRatio= (cash and cash equivalents + currentNetReceivables) / (currentDebt + currentAccountsPayable)'],
        'TotalDebtRatio':['Medida de la cantidad de deuda que una empresa tiene en relación con sus activos totales.','\n- Un ratio alto la empresa tiene una gran cantidad de deuda en relación con sus activos, lo que puede significar que la empresa tiene un mayor riesgo de incumplimiento en el pago de la deuda. \n- Un ratio bajo indica que la empresa depende menos de la deuda para financiar sus operaciones','TotalDebtRatio = Total liabilities/ Total assets'],
        'LongTermDebtRatio':['Compara la deuda a largo plazo de una empresa con su capitalización total.','\n- Un ratio alto indica que está financiando gran parte de sus operaciones a través de la deuda a largo plazo. \n- Un ratio bajo puede indicar que la empresa está financiando sus operaciones con fondos propios.','LongTermDebtRatio = longTermDebt/totalShareholderEquity'],
        'InterestCoverRatio':['Es un indicador de la capacidad de una empresa para pagar los intereses sobre su deuda. Mide la cantidad de ganancias operativas que tiene una empresa en relación con los intereses que debe pagar.','\n- Un ratio alto indica que la empresa tiene una capacidad sólida para pagar sus intereses sobre la deuda. \n- Un ratio bajo indica que la empresa puede tener dificultades para pagar sus intereses y podría estar en riesgo de incumplimiento.','InterestCoverRatio = EBIT/InterestExpense'],
        'GrossMargin':['Mide la eficiencia en la gestión de la producción de la empresa.  Indica la cantidad de ingresos que quedan después de pagar los costes directos relacionados con la producción de bienes o servicios.','Un ratio alto indica que la empresa está operando de manera eficiente y puede tener más margen para reducir los costos de producción o aumentar los precios de venta.','GrossMargin = totalRevenue/costOfRevenue'],
        'I+DRatio':['Mide la cantidad de inversión que una empresa está realizando en investigación y desarrollo en relación con sus ingresos totales. Se utiliza para evaluar la capacidad de la empresa para innovar y mantener una ventaja competitiva a largo plazo.','\n- Un ratio alto indica que la empresa está invirtiendo una gran cantidad de sus ingresos en I+D. \n- Un ratio bajo puede indicar que la empresa no está invirtiendo suficientes recursos en I+D.','I+Dratio = researchAndDevelopment/totalRevenue'],
        'InventoryTrunoverRatio':['Medida que indica la frecuencia con la que una empresa convierte su inventario en ventas durante un período de tiempo determinado.','\n- Un ratio alto indica que la empresa está vendiendo su inventario rápidamente. \n- Un ratio bajo indica que la empresa tiene dificultades para vender sus productos.','Inventory Turnover Ratio = Costo de ventas / Promedio del inventario']
        }
    while True:
        ayuda = input("\n¿Desea ayuda con la definición/interpretación/cálculo de algún ratio? (Escriba 'si' o 'no') | ")
        ratios_seleccionados = []
        if ayuda.lower() == "si":
            ratio = input("\nCopie el nombre del ratio de interés: ")
            if ratio in ratios:
                ratios_seleccionados.append(ratio)
            else:
                print("\n\033[1mRatio no encontrado\033[0m")
                ratio = input("Copie el nombre del ratio de interés: ")
            print("\n")
            # print("*************")
            print("\033[1mEscoja una de las siguientes opciones:\033[0m")
            print("1. Definición")
            print("2. Interpretación")
            print("3. Cálculo")
            print("4. Todas las anteriores")
            #print("*************")
            try:
                opc = int(input("\nIngrese el número de la opción deseada: "))
            except: 
                opc = int(input("\nIngrese el número de la opción deseada: "))
            while(opc<1 or opc>4):
                print("\n\033[1mOpción no válidad\033[0m")
                opc = int(input("\nIngrese el número de la opción deseada: "))
            for ratio in ratios_seleccionados:
                if opc == 1:
                    print("\n---------------------------------")
                    print("\033[1m{}\033[0m".format(ratio))
                    print("---------------------------------")
                    print("\033[1mDefinición:\033[0m {}".format(ratios[ratio][0]))
                elif opc == 2:
                    print("\n---------------------------------")
                    print("\033[1m{}\033[0m".format(ratio))
                    print("---------------------------------")
                    print("\033[1mInterpretación:\033[0m {}".format(ratios[ratio][1]))
                elif opc == 3:
                    print("\n---------------------------------")
                    print("\033[1m{}\033[0m".format(ratio))
                    print("---------------------------------")
                    print("\033[1mCálculo:\033[0m {}".format(ratios[ratio][2]))
                elif opc == 4:
                    print("\n---------------------------------")
                    print("\033[1m{}\033[0m".format(ratio))
                    print("---------------------------------")
                    print("\033[1mDefinición:\033[0m {}".format(ratios[ratio][0]))
                    print("\033[1mInterpretación:\033[0m {}".format(ratios[ratio][1]))
                    print("\033[1mCálculo:\033[0m {}".format(ratios[ratio][2]))
        else:
            break

    # Solicitar al usuario que ingrese los filtros  
    print(f'\n\033[1mLos ratios disponibles son:\033[0m')
    print("----------------------------------------------------------------------")

    for i, (a, b) in enumerate(zip(df.index.values[::2], df.index.values[1::2]), start=1):
        print(f"\033[1m{i*2-1}.\033[0m {a:<35}", end="")
        if b:
            print(f"\033[1m{i*2}.\033[0m {b:<20}")
        else:
            print()
    print("----------------------------------------------------------------------")
    while True:
        ratio = input("\nCopie el nombre del ratio por el que desea filtrar o 'salir' para terminar: ")
        if ratio.lower() == 'salir':
            break
        while ratio not in lista_ratios:
            print (f"\nError: El ratio ingresado '{ratio}' no es válido.")
            ratio = input("\nIngrese nuevamente el nombre del ratio por el que desea filtrar o 'salir' para terminar: ")
            if ratio.lower() == 'salir':
                break
        if ratio in lista_ratios:         
            value = input("\nIngrese 'max' si desea filtrar por el valor máximo o 'min' si desea filtrar por el valor mínimo: ")
            while True:
                if value.lower() == 'max':
                    ratio_1 = ratio
                    valor_input_1 = input("\nIngrese el valor máximo para el ratio {}: ".format(ratio))
                    try:
                        valor_1 = float(valor_input_1)
                        filtros_dict_list.append({'ratio_1': ratio_1, 'valor_1': valor_1})
                        break
                    except ValueError:
                        print("\nEl valor ingresado no es válido. Por favor, ingrese un número.")  
                        
                elif value.lower() == 'min':
                    ratio_2 = ratio
                    valor_input_2 = input("\nIngrese el valor mínimo para el ratio {}: ".format(ratio))
                    try:
                        valor_2 = float(valor_input_2)
                        filtros_dict_list.append({'ratio_2':ratio_2, 'valor_2':valor_2})
                        break
                    except ValueError:
                        print("\nEl valor ingresado no es válido. Por favor, ingrese un número.")
                else: 
                    print("\nEl valor ingresado no es válido.")
                    break
        if len(filtros_dict_list)>0:
            resumen = (input("\n¿Desea un resumen de los ratios filtrados? (Escriba 'si' o 'no') | "))
            if resumen.lower() == 'si':
                print("")
                for dictt in filtros_dict_list:
                    if 'ratio_1' in dictt.keys() and 'ratio_2' not in dictt.keys():
                        print(f"{dictt['ratio_1']} < {dictt['valor_1']}")
                    elif 'ratio_2' in dictt.keys() and 'ratio_1' not in dictt.keys(): 
                        print(f"{dictt['ratio_2']} > {dictt['valor_2']}")
                    else:
                        print(f"{dictt['ratio_1']} < {dictt['valor_1']}")
                        print(f"{dictt['ratio_2']} > {dictt['valor2']}")
            else: 
                pass
    # Aplicar los filtros al DataFrame_ratios
    ratios_list= []
    df_filtrado = df.copy()
    summary_list = []
    for filtro in filtros_dict_list:
        try:
            if 'ratio_1' in filtro.keys():
                ratio_1 = filtro['ratio_1']
                valor_1 = filtro['valor_1']
                mask = df_filtrado.loc[ratio_1] <= valor_1
                mask_nans = df_filtrado.loc[ratio_1].isna()
                mask = mask | mask_nans  # Combinar la máscara original con la máscara de NaN para que traiga las empresas con NAN pereo que cumplen con los demas filtros
                df_filtrado = df_filtrado.loc[:, mask]
                summary_list.append({ratio_1:{'<':valor_1}})
                ratios_list.append(ratio_1)
            elif 'ratio_2' in filtro.keys():
                ratio_2 = filtro['ratio_2']
                valor_2 = filtro['valor_2']
                mask = df_filtrado.loc[ratio_2] >= valor_2 
                mask_nans = df_filtrado.loc[ratio_2].isna()
                mask = mask | mask_nans  
                df_filtrado = df_filtrado.loc[:, mask]  
                summary_list.append({ratio_2:{'>':valor_2}})
                ratios_list.append(ratio_2)
        except:
            pass

    # imprimimos aquellas empresas que cumplen con los filtros pero en alguno de los ratios tiene NA 
    empresas_df = df_filtrado.transpose()
    # encuentra las filas del DataFrame que tienen valores faltantes en alguna de las columnas seleccionadas
    empresas_faltantes = empresas_df.loc[:, ratios_list].loc[empresas_df[ratios_list].isna().any(axis=1)]
    # itera sobre cada fila del DataFrame que tiene valores faltantes
    empresas_na = []
    ratios_na = []
    for empresa, valores_faltantes in empresas_faltantes.iterrows():
        # itera sobre cada columna del DataFrame
        for ratio, valor in valores_faltantes.iteritems():
            # si hay valores faltantes, imprime el nombre de la empresa y el nombre del ratio
            if pd.isna(valor):
                empresas_na.append(empresa)
                ratios_na.append(ratio)

    # Damos la opción al usuario de eliminar las empresas con valores faltantes del df filtrado
    if len(empresas_na)>=1:
        lista3 = []
        for elemento1, elemento2 in zip(empresas_na, ratios_na):
            lista3.append(elemento1)
            lista3.append(elemento2)
        print('\n\033[1mLas empresas que se muestran a continuación tienen valores faltantes\033[0m')
        print("---------------------------------------------------------------------------------------------------------------------")
        print('\033[1mTicker \t Filtro\033[0m')
        print("------------------------------------")
        for a, b in zip(lista3[::2], lista3[1::2]):
            
            print(f"{a:<10}", end="")
            if b:
                print(f"{b:<10}")
            else:
                print()
        print("----------------------------------------------------------------------")

        while True:
            try:
                user_chooice = (input("\n¿Desea eliminar las empresas con valores faltantes? (Escriba 'si' o 'no') | "))
                if user_chooice.lower() == 'si':
                    df_filtrado.drop(columns = empresas_na, inplace=True)
                else:
                    pass
                break
            except:
                print("\nPor favor, ingrese si o no.\n")
    else:       
        pass
    
    # Guardamos las empresas filtradas y su respectivo sector en un diccionario
    dicc_filtrado = {} 
    for company in df_filtrado.columns.values:
        # Excepcion en caso de que el ticker este en el df pero no en el diccionario de sectores
        try:
            dicc_filtrado[company]= dicc[company]
            dicc_filtrado
            
        except  KeyError as error:
            clave = error.args[0]
            print(f"\nEl ticker '{clave}' no se encuentra disponible \n")
    print (f'\n-----------------------------\033[1mFILTRANDO EMPRESAS\033[0m-----------------------------\n')
    
    # Creamos el diccionario con los ratios y sus respectivos valores filtrados
    first_summ_dict = {}
    for diccionario in summary_list:
        first_summ_dict.update(diccionario)
    summary_dict = {'Ratios filtrados':first_summ_dict}
    summary_filter_list = [dicc_filtrado, summary_dict]
    
    return summary_filter_list

def modulo1():
        mongo_uri= os.environ['mongo_uri']
        ratios = get_ratios_db(uri = mongo_uri, DB_name= 'Proyect', collection_name='SP500_RATIOS')
        data_date = ratios['_id']
        data_date = time.strftime('%d/%m/%Y', time.localtime(data_date))
        print(f'\nFecha de la obtención de datos: {data_date}\n') # mostramos la fecha en la que se han obtenido los datos
        del ratios['_id'] 

        # guardamos los ratios en un df 
        df_ratios = pd.DataFrame(ratios)
        df_ratios.replace([np.inf, -np.inf], np.nan, inplace=True) # Reemplazamos los valores infinitos por NaN

        # # Obtenemos los componentes de los sectores del DB 
        sector_dict = get_sectors_db(uri = mongo_uri, DB_name= 'Proyect', collection_name='SECTOR_COMPONENTS')

        # # Guardamos los ticker que no estan guardados en el DB ratios y avisamos al usuario que tickers no están disponibles
        # tickers_faltantes = set(sector_dict.keys()).difference(set(df_ratios.columns))

        # print(f"Los siguientes tickers no se encuentran disponibles para realizar el filtrado:")
        # for t in sorted(tickers_faltantes):
        #     print(t)
            
        return filtrar_datos(df_ratios, sector_dict)
########################################################################################################################################################################
if __name__ == "__main__":
    
    # Invocamos la función para realizar el filtrado
    pprint(modulo1())
