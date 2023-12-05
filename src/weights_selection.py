# Version # 1.3

from ratio_filter import get_ratios_db, get_sectors_db, filtrar_datos
from pprint import pprint
import pandas as pd
import numpy as np
from sector_filter import get_number_sectors, sector_filter, modulo2
from yahoo_fin.stock_info import get_data, get_stats
import cvxpy as cv 
import matplotlib.pyplot as plt
import matplotlib.style as style
import warnings
from tabulate import tabulate
import time 
from full_fred.fred import Fred
import time
from datetime import datetime, timedelta
import os 
from pymongo import MongoClient
warnings.filterwarnings("ignore")
# librerias para probar modelo en local
from keras.models import load_model
import joblib
from sklearn.preprocessing import StandardScaler


# mu: Un array con las tasas esperadas de retorno de cada activo.
# Sigma: Una matriz de covarianzas de los activos.
# rf: La tasa libre de riesgo (por defecto es 0).
# objective: El objetivo que se desea optimizar en el portafolio (por defecto es "Utility").
# A: El parámetro de adversión al riesgo, utilizado en algunos objetivos (por defecto es 0).
# upperlng: El peso máximo que se puede asignar a cada activo (por defecto es 1).

def MV_portfolio(mu, Sigma, rf, objective, A, upperlng):
    '''
    '''
    # Definición de variables
    w = cv.Variable((1, mu.shape[1]))
    k = cv.Variable((1, 1))
    
    # Definición del parámetro rf0 como no negativo
    rf0 = cv.Parameter(nonneg=True)
    rf0.value = rf
    
    # Cálculo del retorno y el riesgo
    ret = mu * w.T
    risk = cv.quad_form(w.T, Sigma)
    
    # Casos para diferentes objetivos
    if objective == 'Sharpe':
        obj = cv.Minimize(risk * 100)  # Se minimiza el riesgo multiplicado por 100
        constraints = [cv.sum(w) == k,  # Restricción de suma de pesos igual a k
                       k >= 0,  # Restricción de k no negativo
                       mu * w.T - rf0 * k == 1]  # Restricción para Sharpe sea = a 1 
        constraints += [w <= k * upperlng,  # Restricción de pesos menores o iguales a k*upperlng
                        w >= 0.01]  # Restricción de pesos demasiados pequeños

    elif objective == 'Utility':
        obj = cv.Maximize(ret - A * risk)  # Se maximiza el retorno menos el riesgo ponderado por adversión al riesgo A
        constraints = [cv.sum(w) == 1]  # Restricción de suma de pesos igual a 1
        constraints += [w <= upperlng,  # Restricción de pesos menores o iguales a upperlng
                        w >= 0.01]  # Restricción de pesos no negativos

    elif objective == 'MinRisk':
        obj = cv.Minimize(risk)  # Se minimiza el riesgo
        constraints = [cv.sum(w) == 1]  # Restricción de suma de pesos igual a 1
        constraints += [w <= upperlng,  # Restricción de pesos menores o iguales a upperlng
                        w >= 0.01]  # Restricción de pesos no negativos

    elif objective == 'MaxRet':
        obj = cv.Maximize(ret)  # Se maximiza el retorno
        constraints = [cv.sum(w) == 1,  # Restricción de suma de pesos igual a 1
                       risk <= A**2]  # Restricción de riesgo menor o igual a a^2
        constraints += [w <= upperlng,  # Restricción de pesos menores o iguales a upperlng
                        w >= 0.01]  # Restricción de pesos no negativos
    
    # Resolución del problema de optimización
    prob = cv.Problem(obj, constraints)
    
    # Búsqueda del mejor solver para resolver el problema
    for solver in [cv.ECOS, cv.SCS, cv.OSQP]:
        try:
            prob.solve(solver=solver)
            if w.value is not None:
                break
        except:
            pass
    
    # Cálculo de los pesos finales
    if objective == 'Sharpe':
        weights = w.value/k.value  # Se divide w entre k para obtener los pesos finales y que la suma de w sea 1 
        weights = weights.reshape(mu.shape[1], 1)
    else:    
        weights = w.value.reshape(mu.shape[1], 1)

    return weights

def MV_NOC(mu, Sigma, w0, obj_W0, rf, upperlng, A, bins=30):
    '''
    '''
    if obj_W0 == 'Sharpe':
        # Calculamos los pesos óptimos para minimizar el riesgo
        w1 = MV_portfolio(mu, Sigma, rf, 'MinRisk', A, upperlng)
        # Calculamos los pesos óptimos para maximizar la utilidad
        w2 = MV_portfolio(mu, Sigma, rf, 'Utility', A, upperlng)
    elif obj_W0 == 'Utility':
        # Calculamos los pesos óptimos para minimizar el riesgo
        w1 = MV_portfolio(mu, Sigma, rf, 'MinRisk', A, upperlng)
        # Calculamos los pesos óptimos para maximizar la rentabilidad
        w2 = MV_portfolio(mu, Sigma, rf, 'MaxRet', A, upperlng)
    elif obj_W0 == 'MaxRet':
        # Calculamos los pesos óptimos para minimizar el riesgo
        w1 = MV_portfolio(mu, Sigma, rf, 'MinRisk', A, upperlng)
        # Calculamos los pesos óptimos para maximizar la utilidad
        w2 = MV_portfolio(mu, Sigma, rf, 'Utility', A, upperlng)
    elif obj_W0 == 'MinRisk':
        # Calculamos los pesos óptimos para maximizar la rentabilidad
        w1 = MV_portfolio(mu, Sigma, rf, 'MaxRet', A, upperlng)
        # Calculamos los pesos óptimos para maximizar la utilidad
        w2 = MV_portfolio(mu, Sigma, rf, 'Utility', A, upperlng)
        
    # Calculamos la diferencia en el riesgo y el retorno entre los dos portafolios
    d_x = (np.sqrt(w2.T @ Sigma @ w2) - np.sqrt(w1.T @ Sigma @ w1))/bins
    d_y = (mu @ w2 - mu @ w1)/bins

    # Definimos el riesgo y el retorno del portafolio de referencia w0
    risk1 = np.square(np.sqrt(w0.T @ Sigma @ w0) + d_x)
    ret1 = mu @ w0 - d_y
    
    # Definimos los pesos w como variables de optimización
    w = cv.Variable((1, mu.shape[1]))
    
    # Calculamos el retorno y el riesgo del portafolio utilizando las variables w
    ret = mu @ w.T
    risk = cv.quad_form(w.T, Sigma)

    # Definición de la función objetivo
    obj = -cv.log((ret - ret1)*1000) - cv.log((risk1 - risk)*1000)  # combinar el rendimiento y el riesgo en la función objetivo 
    obj += -cv.sum(cv.log((upperlng - w)*1000))  # Restricción de pesos máximos
    obj += -A*cv.sum(cv.log(w*1000))  # Función de utilidad

    # Definimos las restricciones del problema
    constraints = [cv.sum(w) == 1,  w >= 0.01] 
    
    # Definimos la función objetivo a minimizar
    obj = cv.Minimize(obj*1000)

    # Resolvemos el problema de optimización utilizando diferentes solvers
    prob = cv.Problem(obj, constraints)
    for solver in [cv.ECOS, cv.SCS, cv.OSQP]:
        try:
            prob.solve(solver=solver)
            if w.value is not None:
                break
        except:
            pass
    
    # Obtenemos los pesos óptimos
    weights = w.value
    weights = weights.reshape(mu.shape[1],1)
    weights = weights/np.sum(weights)

    return weights

# A = 0: el inversor es totalmente neutral al riesgo y solo se preocupa por maximizar el rendimiento esperado.
# 0 < A < 1: el inversor es relativamente tolerante al riesgo y está dispuesto a aceptar cierta cantidad de volatilidad en sus inversiones a cambio de una rentabilidad esperada más alta.
# A = 1: el inversor tiene aversión media al riesgo y busca un equilibrio entre el rendimiento esperado y el riesgo.
# A > 1: el inversor es muy averso al riesgo y está dispuesto a aceptar una menor rentabilidad esperada a cambio de una mayor estabilidad en sus inversiones.

def get_final_companies(interes_companies):
    '''
    '''
    list_interes_tk = []
    for tk in interes_companies:
        list_interes_tk.append(tk)
    #print('\nLos activos disponibles son:')
    # for c in list_interes_tk:
    #     print(c)
    #pprint(interes_companies)

    while True:
        try:
            print('\n\033[1mEscoga una opción:\033[0m \n1. Añadir ticker\n2. Eliminar ticker\n3. Salir')
            user_option = int(input("\nIngrese el número de la opción: "))
            if user_option == 3:
                break
            elif user_option == 1:
                new_asset = input("\nIntroduzca el ticker que desea añadir: ")
                try: 
                    get_stats(new_asset)
                    list_interes_tk.append(new_asset)
                    #print(f"\nEl ticker {new_asset} se ha agregado a la lista de activos de interés.\n")
                    print('\033[1;32m' + f"\nEl ticker {new_asset} se ha agregado a la lista de activos de interés.\n" + '\033[0m')

                except:
                    print(f'\nEl ticker {new_asset} no está disponible.\n')
            elif user_option == 2:
                del_asset = input("\nIntroduzca el ticker que desea eliminar: ")
                if del_asset in list_interes_tk:
                    list_interes_tk.remove(del_asset)
                    #print(f"\nEl ticker {del_asset} se ha eliminado de la lista de activos de interés.\n")
                    print('\033[1;32m' + f"\nEl ticker {del_asset} se ha eliminado de la lista de activos de interés.\n" + '\033[0m')

                else: 
                    print(f'\nNo es posible eliminar el ticker {del_asset} porque no se encuentra en la lista.')
            else:
                print("\nOpción inválida. Por favor seleccione una opción válida (1, 2 o 3).")
        except ValueError: 
                print("\nOpción inválida. Por favor seleccione una opción válida (1, 2 o 3).")
    return list_interes_tk

def get_close(list_interes_tk):
    '''
    '''
    #start = '2010-01-01'
    price_dicct = {}
    for tk in list_interes_tk:
        df = get_data(tk)
                      #, start_date= start)
        price_dicct[tk] = df.adjclose
    df_close = pd.DataFrame(price_dicct)
    return df_close
# ontemeos los indices macro economicos mas recientes y los preprocesamos

def get_macro_features():
    '''
    Call API FRED and get the features for the economic model
    '''
    fred = Fred('fredkey.txt')
    fred.set_api_key_file('fredkey.txt')
    df = pd.DataFrame()
    current_date = datetime.now()
    time_ago = current_date - timedelta(days=300)
    start_date = time_ago.strftime('%Y-%m-%d')
    end_date = current_date.strftime('%Y-%m-%d')
    icc = fred.get_series_df('UMCSENT', vintage_dates=end_date, observation_start=start_date)
    icc['value'] = icc.value.apply(pd.to_numeric)
    icc['variacion'] = np.log(icc['value'].iloc[-2]) - np.log(icc['value'].iloc[-1])
    df.loc[0, 'UMCSENT'] = icc['variacion'].iloc[-1]
    interest_rate = fred.get_series_df('FEDFUNDS', vintage_dates=end_date, observation_start=start_date)
    interest_rate['value'] = interest_rate.value.apply(pd.to_numeric)
    interest_rate['value'] = interest_rate['value']/100 
    df.loc[0, 'FEDFUNDS'] = interest_rate.value.iloc[-1]
    current_date = datetime.now()
    time_ago = current_date - timedelta(days=350)
    start_date = time_ago.strftime('%Y-%m-%d')
    end_date = current_date.strftime('%Y-%m-%d')
    public_debt = fred.get_series_df('GFDEGDQ188S', vintage_dates=end_date, observation_start=start_date)
    public_debt['value'] = public_debt.value.apply(pd.to_numeric)
    public_debt['value'] = public_debt['value']/100 #
    df.loc[0, 'GFDEGDQ188S'] = public_debt.value.iloc[-1]
    time_ago = current_date - timedelta(days=350)
    start_date = time_ago.strftime('%Y-%m-%d')
    end_date = current_date.strftime('%Y-%m-%d')
    salaries = fred.get_series_df('LES1252881600Q', vintage_dates=end_date, observation_start=start_date)
    salaries['value'] = salaries.value.apply(pd.to_numeric)
    salaries['variacion'] = np.log(salaries['value'].iloc[-2]) - np.log(salaries['value'].iloc[-1])
    df.loc[0, 'LES1252881600Q'] = salaries['variacion'].iloc[-1]
    time_ago = current_date - timedelta(days=300)
    start_date = time_ago.strftime('%Y-%m-%d')
    end_date = current_date.strftime('%Y-%m-%d')
    monetary_supply = fred.get_series_df('AMDMUO', vintage_dates=end_date, observation_start=start_date)
    monetary_supply['value'] = monetary_supply.value.apply(pd.to_numeric)
    monetary_supply['variacion'] = np.log(monetary_supply['value'].iloc[-2]) - np.log(monetary_supply['value'].iloc[-1])
    df.loc[0, 'AMDMUO'] = monetary_supply['variacion'].iloc[-1]
    time_ago = current_date - timedelta(days=300)
    start_date = time_ago.strftime('%Y-%m-%d')
    end_date = current_date.strftime('%Y-%m-%d')
    exportation_idx = fred.get_series_df('XTEXVA01CNQ667S', vintage_dates=end_date, observation_start=start_date)
    exportation_idx['value'] = exportation_idx.value.apply(pd.to_numeric)
    exportation_idx['variacion'] = np.log(exportation_idx['value'].iloc[-2]) - np.log(exportation_idx['value'].iloc[-1])
    df.loc[0, 'XTEXVA01CNQ667S'] = exportation_idx['variacion'].iloc[-1]
    exportation_idx = fred.get_series_df('XTIMVA01CNQ657S', vintage_dates=end_date, observation_start=start_date)
    exportation_idx['value'] = exportation_idx.value.apply(pd.to_numeric)
    exportation_idx['value'] = exportation_idx['value']/100 
    df.loc[0, 'XTIMVA01CNQ657S'] = exportation_idx.value.iloc[-1]
    public_expenditure = fred.get_series_df('FGEXPND', vintage_dates=end_date, observation_start=start_date)
    public_expenditure['value'] = public_expenditure.value.apply(pd.to_numeric)
    public_expenditure['variacion'] = np.log(public_expenditure['value'].iloc[-2]) - np.log(public_expenditure['value'].iloc[-1])
    df.loc[0, 'FGEXPND'] = public_expenditure['variacion'].iloc[-1]
    time_ago = current_date - timedelta(days=365)
    start_date = time_ago.strftime('%Y-%m-%d')
    end_date = current_date.strftime('%Y-%m-%d')
    gov_defct_surpls = fred.get_series_df('FYFSGDA188S', vintage_dates=end_date, observation_start=start_date)
    gov_defct_surpls['value'] = gov_defct_surpls.value.apply(pd.to_numeric)
    gov_defct_surpls['value'] = gov_defct_surpls['value']/100 
    df.loc[0, 'FYFSGDA188S'] = gov_defct_surpls.value.iloc[-1]
    
    return df.values

def economic_model(features):
    scaler = StandardScaler()
    features = scaler.fit_transform(features)
    # importamos el modelo de NN para predecir el ciclo economico
    ciclo_eco_model = load_model('../Machine Learning/modelos_entrenados/modelo_NN_OPT.h5')
    estimaciones_ciclo_eco = ciclo_eco_model.predict(features)
    estimaciones_ciclo_eco = np.argmax(estimaciones_ciclo_eco, axis=1)
    return estimaciones_ciclo_eco

def strategy_pred_model(feature):
    model_filename = '../Machine Learning/modelos_entrenados/RF2.joblib'
    RF2 = joblib.load(model_filename)
    feature = feature.reshape(-1, 1)
    prediccion_estrategia_RF2 = RF2.predict(feature)
    prediccion_estrategia_RF2 = int(prediccion_estrategia_RF2[0])
    return prediccion_estrategia_RF2

################################################################################################################################
def portfolio_allocation (companies, summary):
    '''
    Versión gratitua.

    companies: una lista o diccionario con los tickers de las empresas a inviertir.
    Summary: un resumen de los modulos anteriores

    El usuario decide si queire eliminar o añadir mas empresas al input, se pregunta al usuario que modelo desea utilizar: 'Sharpe','Utility','MinRisk','MaxRet'
    un valor para medir la adversión al reisgo, y el peso máximo que puede tener cada activo en la cartera. 

    Devuelve un portfolio en función de los tickers ingresados y la configuración establecida.                           
    '''
    n = len(companies)
    if n >0:
        if n >= 20:
            print("\n")
            print('\033[1;97;41mWARNING: CON UN NUMERO ELEVADO DE ACTIVOS ES POSIBLE QUE NO SE PUEDA CONSTRUIR LA CARTERA OPTIMA\033[0m')
            final_tk_list  = get_final_companies(companies)
            df_close = get_close(final_tk_list)
            n = len(final_tk_list)
            returns = np.log(df_close).diff().dropna()
            mu = np.mean(returns.to_numpy(),axis=0).reshape(1, n)
            Sigma = np.cov(returns.to_numpy().T)
        else:
            final_tk_list  = get_final_companies(companies)
            df_close = get_close(final_tk_list)
            n = len(final_tk_list)
            returns = np.log(df_close).diff().dropna()
            mu = np.mean(returns.to_numpy(),axis=0).reshape(1, n)
            Sigma = np.cov(returns.to_numpy().T)
        print('\n\033[1m----------Configuración para la asiganción de recursos----------\033[0m')
        
        print(f'\nEl rango temporal para hacer los calculos es: \n\n{returns.index[0].date()} - {returns.index[-1].date()}')
        
        while True:
            print('\n\033[1m¿Desea que la estrategia del portfolio la seleccione los modelos de Machine Learning?\033[0m\n')
            user_decision=  input('Escriba si o no | ')
            user_decision = user_decision.lower()
            if user_decision == 'si':
                eco_feutrues = get_macro_features()
                eco_predict = economic_model(eco_feutrues)
                stratey = strategy_pred_model(eco_predict)
                stretgy_dict = {0:'Sharpe',
                                1:'Utility',
                                2:'MinRisk',
                                3:'MaxRet'}
                objective = stretgy_dict[stratey]
                if objective == 'Sharpe':
                    print('\n\033[1mLa estrategia seleccionada por los modelos de ML ha sido: Máximizar el coeficiente Sharpe\033[0m\n')
                elif objective == 'Utility':
                    print('\n\033[1mLa estrategia seleccionada por los modelos de ML ha sido: Utility (Equilibrio entre el retorno esperado y el riesgo asumido)\033[0m\n')
                elif objective == 'MinRisk':
                    print('\n\033[1mLa estrategia seleccionada por los modelos de ML ha sido: Minimizar el Riesgo\033[0m\n')
                elif objective == 'MaxRet':
                    print('\n\033[1mLa estrategia seleccionada por los modelos de ML ha sido:  Máximizar la rentabilidad\033[0m\n')
                break
            else:
                print('\n\033[1mEscoga una opción para determinar el objetivo del portfolio:\033[0m\n1. Máximizar el coeficiente Sharpe\n2. Utility (Equilibrio entre el retorno esperado y el riesgo asumido)\n3. Minimizar el Riesgo\n4. Máximizar la rentabilidad en función del riesgo asumido')
                user_objective = int(input("\nIngrese el número de la opción: "))
                if user_objective == 1:
                    objective = 'Sharpe'
                    break
                elif user_objective == 2:
                    objective = 'Utility'
                    break
                elif user_objective == 3:
                    objective = 'MinRisk'
                    break
                elif user_objective == 4:
                    objective = 'MaxRet'
                    break
                else: 
                    print("\nEl valor ingresado no es válido.")

        print('\n\033[1mTeniendo en cuenta las siguientes consideraciones para medir la adversión al riesgo (A):\033[0m')
        print("---------------------------------------------------------------------------------------------------------------------")
        tabla = [['A = 0.1' , 'Neutral', 'Maximizar el rendimiento esperado'],
            ['0.1 < A < 1', 'Tolerante', 'Aceptar cierta volatilidad por una rentabilidad esperada más alta'],
            ['A = 1' , 'Media adversión al riesgo', 'Equilibrio entre el rendimiento esperado y el riesgo'],
            ['A > 1' , 'Muy adverso al riesgo', 'Aceptar menor rentabilidad esperada por mayor estabilidad en las inversiones']
        ]
        headers = ['Valor de A', 'Actitud hacia el riesgo', 'Prioridad']
        print(tabulate(tabla, headers=headers))

        while True:
            try:
                user_A = float(input("\nIngrese un valor para determinar su adversión al riesgo: "))
                if user_A == 0:
                    print('\nLa adversion al riesgo no puede ser 0')
                    user_A = float(input("\nIngrese un valor para determinar su adversión al riesgo: "))
                break
            except: 
                print("\n El valor ingresado no es válido. Por favor, ingrese un número. \n")

        while True:
            try: 
                user_ulong = float(input("\nIngrese el peso máximo que se pueda asignar a cada activo (0-1): "))
                A = user_A
                upperlong = user_ulong 
                bins = 20
                obj_W0 = objective
                w0 = MV_portfolio(mu, Sigma, 0, objective, A, upperlong)
                w_noc = MV_NOC(mu, Sigma, w0, obj_W0, 0, upperlong, bins)
                break
            except AttributeError:
                print(f'\nCon un peso máximo de {upperlong}, no es posible construir una cartera')
            except: 
                print("\nEl valor ingresado no es válido.")
            
        port_ret = (mu @ w_noc).item() * 12
        port_risk = np.sqrt(w0.T @ Sigma @ w_noc * 12).item()

        SR_NOC = []
        SR_NOC.append([port_ret])
        SR_NOC.append([port_risk])
        Portafolio_NOC = pd.DataFrame(data = w_noc.T, columns = df_close.columns)
        Portfolio_MV = pd.DataFrame(data = w0.T, columns = df_close.columns)
        final_portfolio = Portafolio_NOC.to_dict('records')[0] 

        #print("El retorno esperado del portafolio es: ", '{:,.2%}'.format(port_ret)) 
        print("\nLa desviación estándar del portafolio es: ", '{:,.2%}'.format(port_risk))
        print("\nEl ratio de Sharpe del portafolio es: ", '{:,.6}'.format(port_ret/port_risk))
        print("")
        print("\n\033[1mEl portafolio NOC:\033[0m ")
        #pprint(final_portfolio) # Esto devuelve el API

        graficar = input(f'¿Desea observar un gráfico con la distribución de los pesos? (Escriba si o no) |')
        try:
            if graficar.lower() == 'si': 

                # Establecer el estilo del gráfico
                style.use('ggplot')

                # Definir el tamaño de la figura
                fig = plt.figure(figsize=(8, 8))

                # Definir las leyendas con los nombres de las empresas
                leyendas = Portafolio_NOC.columns.tolist()

                # Trazar el gráfico de pastel
                patches, texts, autotexts = plt.pie(Portafolio_NOC.iloc[0].values,   
                                                    labels=leyendas, autopct='%1.1f%%', pctdistance=0.8)

                # Personalizar el texto de los valores
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_fontsize(12)

                # Añadir leyenda
                plt.legend(title='Empresas', loc='center left', bbox_to_anchor=(1, 0.5))

                # Añadir título
                plt.title('Distribución de los pesos por empresa NOC', fontsize=18)

                # Mostrar el gráfico
                plt.show()
            else:
                pass
        except:
            print ('Por favor, escriba si o no.')

        summary_mod2 = summary['Resumen']    
        summary_portfolio_feautres = {'Caracteristicas cartera': {#'IA':user_decision,
                                                                  "Objetivo":objective,
                                                                  'Adversión al riesgo': A,
                                                                  "Peso max":upperlong}
                            }
        summary_mod2.update(summary_portfolio_feautres)
        summary['Resumen'] = summary_mod2

        portfolio_summary = [final_portfolio, summary]

        return portfolio_summary
    else:

        return(print('No hay empresas para calcular el protfolio'))

def modulo3(portfolio, summary):
    '''
    portfolio: el porfolio obtenido de la funcion portfolio_allocation.
    summary: el resumen obtenido de la funcion portfolio_allocation.

    Se le pregunta al usuario si desea guardar el portfolio en la base de datos, en caso de afirmativo se devuelve el ID del documento (el porfolio y el resumen),
    en caso contrario, devuelve una lista con el porfolio y el resumen. 
    '''
    print('\nEl portfolio es:')
    pprint(portfolio)
    print('\nEl resumen para obtener el portfolio es:')
    pprint(summary['Resumen'])

    print('\n¿Desea guardar el portfolio en la base de datos?')
    save_portfolio = input('Escriba si o no | ')

    if save_portfolio == 'si':
        timestamp = int(time.time())
        final_dict = {'Fecha':timestamp,
                      'Portfolio': portfolio,}
        final_dict.update(summary)
        uri = os.environ['mongo_uri']
        client = MongoClient(uri)
        db = client['Proyect']
        collection = db['Portfolios']
        result = collection.insert_one(final_dict)
        inserted_id = result.inserted_id
        print(f"\nEl ID de su portfolio es: {inserted_id}")
        
        return inserted_id
    
    else:
        print('\nEl portfolio no se ha guardado en la base de datos')

        return [portfolio, summary]


# ##############A PARTIR DE AQUI ESTE MODULO#####################################################  
if __name__ == "__main__":
    output_m2 = modulo2()
    companies = output_m2[0]
    summary = output_m2[1]
    porfolio_summary = portfolio_allocation(companies, summary)
    # print('\nEl portfolio es el siguiente:')
    # pprint(porfolio_summary[0])
    # print('\nEl resumen para obtener el portfolio es el siguiente:')
    # pprint(porfolio_summary[1]['Resumen'])

    resultado = modulo3(porfolio_summary[0], porfolio_summary[1])

    print(f'\n{resultado}')