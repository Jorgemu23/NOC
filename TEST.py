from pymongo.mongo_client import MongoClient
from pymongo import MongoClient, DESCENDING

uri =  '...'


# Create a new client and connect to the server
client = MongoClient(uri)

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)


db = client['Proyect']
collection_ratios = db['SP500_RATIOS']
result = collection_ratios.find_one(sort=[('_id', DESCENDING)])
#ratios = result
print(result)

   # ratios = get_ratios_db(uri = mongo_uri, DB_name= 'Proyect', collection_name='SP500_RATIOS')