import azure.functions as func
import json
import logging
import uuid
import os

from azure.data.tables import TableServiceClient

from merchant import Merchant, MerchantSignal

app = func.FunctionApp()

##
# Merchant API
##

@app.route(route="merchant_api", 
            auth_level=func.AuthLevel.FUNCTION)
def merchant_api(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    if req.method != "GET":
        return func.HttpResponse(f"Only GET requests are supported", status_code=405)
    return func.HttpResponse("OK", mimetype="application/json")
    # with TableServiceClient.from_connection_string(os.environ['storageAccountConnectionString']) as table_service:
    #     table_client = table_service.get_table_client(table_name="flowmerchant")
    #     entities = table_client.list_entities()
    #     rows = [dict(entity) for entity in entities]
    #     return func.HttpResponse(json.dumps(rows), mimetype="application/json")

##
# Merchant Consumer
##

# @app.function_name(name="merchant_consumer")
# @app.queue_trigger(arg_name="msg", 
#                     queue_name="merchantsignals",
#                     connection="storageAccountConnectionString")
# def merchant_consumer(msg: func.QueueMessage) -> None:
#     message_body = json.loads(msg.get_body().decode('utf-8'))
#     signal = MerchantSignal(message_body)
    
#     logging.info(f"received merchant signal, id is {signal.id()}")

#     with TableServiceClient.from_connection_string(os.environ['storageAccountConnectionString']) as table_service:
#         try:
#             merchant = Merchant(table_service)
#             merchant.handle_market_signal(signal)
#         except Exception as e:
#             logging.error(f"error handling market signal {signal.id()}, {e}")
#             return
        
# def new_signal_id() -> str:
#     return str(uuid.uuid4())
