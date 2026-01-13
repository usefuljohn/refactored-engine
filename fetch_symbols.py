from pool_data_handler import rpc_call
import json

ids = ["1.3.4157", "1.3.6268"]
res = rpc_call("get_objects", [ids])

if res:
    print(f"1.3.4157 Symbol: {res[0]['symbol']}")
    print(f"1.3.6268 Symbol: {res[1]['symbol']}")
else:
    print("Failed to fetch objects")
