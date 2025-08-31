#!/usr/bin/env python3
import os, json, base64, time, hashlib
from datetime import datetime
from pathlib import Path
from kafka import KafkaProducer
import requests
from PIL import Image
import io

try:
    from pymilvus import connections, Collection
    MILVUS_AVAILABLE = True
except:
    MILVUS_AVAILABLE = False

class ImageProducer:
    def __init__(self):
        self.kafka_broker = os.getenv("KAFKA_BROKER", "kafka:29092")
        self.fastapi_url = os.getenv("FASTAPI_URL", "http://host.docker.internal:8003")
        self.source_dir = os.getenv("SOURCE_DIR", "/app/images")
        
        print("\n=== IMAGE PRODUCER WITH MILVUS ===")
        self.producer = self.connect_kafka()
        self.milvus = self.connect_milvus() if MILVUS_AVAILABLE else None
    
    def connect_kafka(self):
        for attempt in range(30):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=self.kafka_broker,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    max_request_size=104857600
                )
                print("✓ Connected to Kafka")
                return producer
            except:
                time.sleep(2)
        raise Exception("Failed to connect to Kafka")
    
    def connect_milvus(self):
        try:
            connections.connect(host="milvus", port=19530)
            collection = Collection("image_embeddings")
            collection.load()
            print(f"✓ Connected to Milvus ({collection.num_entities} vectors)")
            return collection
        except Exception as e:
            print(f"⚠ Milvus error: {e}")
            return None
    
    def get_embedding(self, image_path):
        # Read image
        with Image.open(image_path) as img:
            if img.width > 1920 or img.height > 1920:
                img.thumbnail((1920, 1920), Image.Resampling.LANCZOS)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=90)
            image_bytes = buf.getvalue()
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        try:
            response = requests.post(
                f"{self.fastapi_url}/retrieval/SigLIP/embed-image",
                json={"data": [image_base64]},
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict) and 'embedding' in result[0]:
                        embedding = result[0]['embedding']
                    else:
                        embedding = result[0]
                else:
                    embedding = [0.1] * 1152
                return embedding, image_bytes
            else:
                return [0.1] * 1152, image_bytes
        except Exception as e:
            print(f"  Embedding error: {e}")
            return [0.1] * 1152, image_bytes
    
    def process_image(self, image_path):
        filename = os.path.basename(image_path)
        print(f"\nProcessing: {filename}")
        
        embedding, image_bytes = self.get_embedding(image_path)
        file_hash = hashlib.md5(image_bytes).hexdigest()
        milvus_id = f"img_{file_hash}"
        
        # Insert to Milvus
        if self.milvus and len(embedding) == 1152:
            try:
                data = [[milvus_id], [embedding], [filename], [""], [int(time.time())]]
                self.milvus.insert(data)
                self.milvus.flush()
                print(f"  ✓ Milvus: {milvus_id}")
            except Exception as e:
                print(f"  ✗ Milvus failed: {e}")
        
        # Send to Kafka
        metadata = {
            "filename": filename,
            "file_size": len(image_bytes),
            "file_hash": file_hash,
            "milvus_id": milvus_id,
            "timestamp": datetime.now().isoformat(),
            "processed_at": int(time.time())
        }
        
        message = {
            "image_binary": base64.b64encode(image_bytes).decode('utf-8'),
            "image_embedding": embedding,
            "metadata": metadata,
            "embedding_dim": len(embedding)
        }
        
        future = self.producer.send("image-topic", value=message)
        result = future.get(timeout=10)
        print(f"  ✓ Kafka: offset {result.offset}")
        return True
    
    def run(self):
        if not os.path.exists(self.source_dir):
            os.makedirs(self.source_dir, exist_ok=True)
            for color in ['red', 'green', 'blue']:
                img = Image.new('RGB', (256, 256), color=color)
                img.save(f"{self.source_dir}/test_{color}.jpg")
        
        images = list(Path(self.source_dir).glob("*.jpg"))
        print(f"Found {len(images)} images")
        
        for image_path in images:
            try:
                self.process_image(str(image_path))
                time.sleep(0.5)
            except Exception as e:
                print(f"Error: {e}")
        
        self.producer.flush()
        
        if self.milvus:
            print(f"\n✓ Milvus total: {self.milvus.num_entities} vectors")

if __name__ == "__main__":
    producer = ImageProducer()
    producer.run()
