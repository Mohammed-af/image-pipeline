#!/usr/bin/env python3
"""
Fixed Producer with correct FastAPI format
"""

import os
import json
import base64
import time
import hashlib
from datetime import datetime
from pathlib import Path
from kafka import KafkaProducer
import requests
from PIL import Image
import io

class ImageProducer:
    def __init__(self):
        self.kafka_broker = os.getenv("KAFKA_BROKER", "kafka:29092")
        self.fastapi_url = os.getenv("FASTAPI_URL", "http://host.docker.internal:8003")
        self.source_dir = os.getenv("SOURCE_DIR", "/app/images")
        
        print("\n=== IMAGE PRODUCER CONFIGURATION ===")
        print(f"Kafka Broker: {self.kafka_broker}")
        print(f"FastAPI URL: {self.fastapi_url}")
        print(f"Image Source: {self.source_dir}")
        print("="*40 + "\n")
        
        self.producer = self.connect_kafka()
        self.verify_fastapi()
    
    def connect_kafka(self):
        print("Connecting to Kafka...")
        for attempt in range(30):
            try:
                producer = KafkaProducer(
                    bootstrap_servers=self.kafka_broker,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    max_request_size=104857600  # 100MB
                )
                print("✓ Connected to Kafka broker")
                return producer
            except Exception as e:
                print(f"  Waiting for Kafka... attempt {attempt + 1}/30")
                time.sleep(2)
        raise Exception("Failed to connect to Kafka")
    
    def verify_fastapi(self):
        """Verify FastAPI is accessible and working"""
        print("Verifying FastAPI connection...")
        try:
            # Test health endpoint
            resp = requests.get(f"{self.fastapi_url}/health", timeout=5)
            if resp.status_code == 200:
                print(f"✓ FastAPI is running at {self.fastapi_url}")
                return True
        except Exception as e:
            print(f"⚠ FastAPI may not be accessible: {e}")
            print("  Will use mock embeddings if unavailable")
        return False
    
    def get_image_embedding(self, image_path):
        """Get image embedding from FastAPI with correct format"""
        try:
            # Read and resize image if needed
            with Image.open(image_path) as img:
                # Resize large images to avoid issues
                max_dim = 1920
                if img.width > max_dim or img.height > max_dim:
                    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save to bytes
                buf = io.BytesIO()
                img.save(buf, format='JPEG', quality=90)
                image_bytes = buf.getvalue()
            
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Call FastAPI with correct format
            response = requests.post(
                f"{self.fastapi_url}/retrieval/SigLIP/embed-image",
                json={"data": [image_base64]},  # Correct format!
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    # Response is [{"embedding": [...]}]
                    if isinstance(result[0], dict) and 'embedding' in result[0]:
                        embedding = result[0]['embedding']
                    else:
                        embedding = result[0]
                elif isinstance(result, dict) and 'embeddings' in result:
                    # Response is {"embeddings": [[...]]}
                    embedding = result['embeddings'][0]
                else:
                    # Fallback to mock
                    print("  ⚠ Unexpected response format, using mock")
                    embedding = [0.1] * 1152
                
                return embedding, image_bytes
            else:
                print(f"  ⚠ FastAPI returned {response.status_code}, using mock embeddings")
                return [0.1] * 1152, image_bytes
                
        except Exception as e:
            print(f"  ⚠ Error getting embedding: {e}, using mock")
            return [0.1] * 1152, image_bytes
    
    def get_text_embedding(self, text):
        """Get text embedding from FastAPI"""
        try:
            response = requests.post(
                f"{self.fastapi_url}/retrieval/SigLIP/embed-text",
                json={"data": [text]},  # Correct format!
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict) and 'embedding' in result[0]:
                        return result[0]['embedding']
                    else:
                        return result[0]
                elif isinstance(result, dict) and 'embeddings' in result:
                    return result['embeddings'][0]
            
            # Fallback to mock
            return [0.2] * 1152
            
        except Exception:
            return [0.2] * 1152
    
    def process_image(self, image_path):
        """Process single image"""
        filename = os.path.basename(image_path)
        print(f"\nProcessing: {filename}")
        
        # Get image embedding
        image_embedding, image_bytes = self.get_image_embedding(image_path)
        print(f"  Image embedding: {len(image_embedding)} dimensions")
        
        # Create metadata
        metadata = {
            "filename": filename,
            "file_size": len(image_bytes),
            "file_hash": hashlib.md5(image_bytes).hexdigest(),
            "timestamp": datetime.now().isoformat(),
            "processed_at": int(time.time())
        }
        
        # Get image properties
        try:
            with Image.open(image_path) as img:
                metadata["width"] = img.width
                metadata["height"] = img.height
                metadata["format"] = img.format
        except:
            pass
        
        # Generate caption and get text embedding
        caption = f"Image of {filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ')}"
        metadata["caption"] = caption
        text_embedding = self.get_text_embedding(caption)
        print(f"  Text embedding: {len(text_embedding)} dimensions")
        
        # Create Kafka message
        message = {
            "image_binary": base64.b64encode(image_bytes).decode('utf-8'),
            "image_embedding": image_embedding,
            "text_embedding": text_embedding,
            "metadata": metadata,
            "embedding_dim": len(image_embedding),
            "has_dual_embeddings": True
        }
        
        # Send to Kafka
        future = self.producer.send("image-topic", value=message)
        result = future.get(timeout=10)
        print(f"  ✓ Sent to Kafka (partition: {result.partition}, offset: {result.offset})")
        
        return True
    
    def run(self):
        """Process all images"""
        print(f"\nScanning directory: {self.source_dir}")
        
        # Find images
        if not os.path.exists(self.source_dir):
            print(f"Creating test images in {self.source_dir}...")
            os.makedirs(self.source_dir, exist_ok=True)
            # Create test images
            colors = ['red', 'green', 'blue', 'yellow', 'purple']
            for color in colors:
                img = Image.new('RGB', (256, 256), color=color)
                img.save(f"{self.source_dir}/test_{color}.jpg")
        
        images = []
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            images.extend(Path(self.source_dir).glob(f"*{ext}"))
            images.extend(Path(self.source_dir).glob(f"*{ext.upper()}"))
        
        if not images:
            print("No images found!")
            return
        
        print(f"Found {len(images)} images to process")
        print("="*40)
        
        processed = 0
        failed = 0
        
        for image_path in images:
            try:
                if self.process_image(str(image_path)):
                    processed += 1
                time.sleep(0.5)  # Don't overwhelm the system
            except Exception as e:
                print(f"ERROR processing {image_path}: {e}")
                failed += 1
        
        self.producer.flush()
        
        print("\n" + "="*40)
        print(f"COMPLETE: Processed {processed}, Failed {failed}")
        print("="*40)

if __name__ == "__main__":
    try:
        producer = ImageProducer()
        producer.run()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        exit(1)
# Add this import at the top (after existing imports)
from pymilvus import connections, Collection

# Add this method to ImageProducer class
def connect_milvus(self):
    """Connect to Milvus"""
    try:
        connections.connect(host="milvus", port=19530)
        collection = Collection("image_embeddings")
        collection.load()
        print(f"✓ Connected to Milvus ({collection.num_entities} vectors)")
        return collection
    except Exception as e:
        print(f"⚠ Milvus not available: {e}")
        return None

# Add to __init__ method (after self.producer line):
self.milvus = self.connect_milvus()

# Add to process_image method (after getting embeddings, before Kafka send):
# Insert to Milvus
if self.milvus and image_embedding:
    try:
        milvus_id = f"img_{metadata['file_hash']}"
        data = [[milvus_id], [image_embedding], [filename], [int(time.time())]]
        self.milvus.insert(data)
        self.milvus.flush()
        print(f"  ✓ Inserted to Milvus: {milvus_id}")
        metadata["milvus_id"] = milvus_id
    except Exception as e:
        print(f"  ⚠ Milvus insert failed: {e}")
