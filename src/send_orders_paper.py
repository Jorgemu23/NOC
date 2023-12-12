# version 1.0
from pymongo import MongoClient
from bson import ObjectId
from alpaca_trade_api.rest import REST, TimeFrame
from alpaca_trade_api.stream import Stream
import random 
import os 
from weights_selection import modulo3
# Funcion para esblecer Conexión a MongoDB Atlas
def get_portfolio_db(uri, DB_name, collection_name, portfolio_id):
    '''
    Hace una llamada a la DB para traer el protfolio almacenado. 
    '''
    uri = uri
    client = MongoClient(uri)
    db = client[DB_name]
    collection_portfolios = db[collection_name]
    object_id = ObjectId(portfolio_id)
    result = collection_portfolios.find_one({'_id': object_id})
    portfolio = result

    return portfolio

# iniciamos el proceso para enviar ordenes en PAPER a traves de Alpaca
# Cuando este listo hay que añadir el condicional para dar la opción de enviar ordenes en live y paper
def send_alloc_paper():
    existing_id_portfolio = input('\n¿Cuenta con un ID de Portfolio? (Escriba si o no) | ')
    if existing_id_portfolio.lower() == 'si':
        user_portfolio_id = input('\nIngrese el ID de su portfolio')

        user_api_key = input('\nPor favor ingresa el API_KEY de Alpaca | ')
        user__secret_api_key = input('\nPor favor ingresa la SECRET_KEY de Alpaca | ')

        API_KEY = user_api_key
        SECRET_KEY = user__secret_api_key

        rest_api = REST(API_KEY, SECRET_KEY, 'https://paper-api.alpaca.markets')
        mongo_uri = os.environ['mongo_uri']
        uri = mongo_uri
        DB_name= 'Proyect'
        collection_name='Portfolios'

        portfolio_db = get_portfolio_db(uri, DB_name, collection_name, user_portfolio_id)

        print('\nEl portfolio obtenido de la DB es el siguiente\n')
        print(portfolio_db)

        cash_capital = input('\nIngrese el valor del capital que desea invertir |')
        # añadir excepcion para que solo se pueda ingresar un valor númerico
        cash_capital = int(cash_capital)

        # how many dollars we want to allocate to each symbol
        dollar_value_allocations = {symbol: percent * cash_capital for symbol, percent in portfolio_db.items()}

        print('\nEl dinero en dolares que será invertido en cada ticker es el siguiente')
        print(dollar_value_allocations)

        # liquidate all existing positions before rebalanc
        user_input = input('¿Dese cerrar las posiciones para los tickers anteriores? (Escriba si o no) | ')
        if user_input.lower() == 'si':
            print('\nCerrando posciones anteriores ---------------------->\n')
            rest_api.close_all_positions()
        else:
            pass

        # Rebalance portfolio
        for symbol, dollars_alloc in dollar_value_allocations.items():
            
            # market price of current ETF
            market_price = rest_api.get_latest_bar(symbol).close
            
            # how many shares we want
            target_holdings = dollars_alloc // market_price

            # how many shares we have to buy to match target
            order_quantity = target_holdings
            if order_quantity > 0:
                # submit market order for this ETF
                print(f"Submitting market order for {order_quantity} shares of {symbol}")
                rest_api.submit_order(symbol, order_quantity, 'buy', 'market', client_order_id=f'colab_{random.randrange(10000000)}')
            else:
                print(f" It is not posible to Submit market order for {order_quantity} shares of {symbol}\n")
                no_order_sent_stock = []
                no_order_sent_stock.append(symbol)

        if len(no_order_sent_stock)>0:

            print('\nNo se han abierto posiciones para los siguientes tickers')

            for tk in no_order_sent_stock:
                print(tk)

            user_input1 = input('¿Dese abrir posiciones para los tickers anteriores? (Escriba si o no) | ')

            if user_input1.lower() == 'si':
                for tk in no_order_sent_stock:
                    print(f'¿Desea enviar orden para el ticker {tk}')
                    user_input2 = input('(Escriba si o no) | ')
                    if user_input.lower() == 'si':
                        while True:
                            user_order_quantity = input(f'Ingrese la cantidad de acciones que quiere comprar para el ticker {tk}')
                            try:
                                int(user_order_quantity)
                                break
                            except:
                                print('Ingrese un valor númerico')        
                        print(f"Submitting market order for {user_order_quantity} shares of {tk}")
                        rest_api.submit_order(tk, user_order_quantity, 'buy', 'market', client_order_id=f'colab_{random.randrange(10000000)}')            
        else:
            pass

        print('\n\033[1m----------Se han enviado las ordenes correctamente----------\033[0m')

        return  print('Puede consultar el desempeño de su portfolio en el Dasboard de ALPACA')
    else:
        print('\nNo es posible enviar ordenes sin un ID de portfolio existente')
        pass

if __name__ == "__main__":
    crear_cartera_user = input('¿Desea crear una cartera? (Escriba si o no) | ')
    if crear_cartera_user.lower():
        modulo3()
        send_alloc_paper()
    else:
        send_alloc_paper()