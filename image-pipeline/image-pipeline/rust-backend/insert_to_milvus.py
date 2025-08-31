#!/usr/bin/env python3
import sys
import json
from pymilvus import connections, Collection

try:
    collection_name = sys.argv[1]
    id_val = sys.argv[2]
    embedding = json.loads(sys.argv[3])
    filename = sys.argv[4]
    timestamp = sys.argv[5]
    
    connections.connect(host="milvus", port=19530)
    collection = Collection(collection_name)
    
    data = [[id_val], [embedding], [filename], [int(timestamp)]]
    collection.insert(data)
    collection.flush()
    
    print(f"SUCCESS")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
