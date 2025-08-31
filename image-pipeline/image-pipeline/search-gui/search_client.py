#!/usr/bin/env python3
import requests
import json
import argparse
from PIL import Image

class SearchClient:
    def __init__(self, base_url="http://localhost:3000"):
        self.base_url = base_url
    
    def search_by_image(self, image_path, k=10):
        url = f"{self.base_url}/api/search/image"
        with open(image_path, 'rb') as f:
            files = {'image': f}
            params = {'k': k}
            response = requests.post(url, files=files, params=params)
        return response.json() if response.ok else None
    
    def search_by_text(self, text, k=10):
        url = f"{self.base_url}/api/search/text"
        response = requests.post(url, json={"text": text, "k": k})
        return response.json() if response.ok else None
    
    def get_stats(self):
        response = requests.get(f"{self.base_url}/stats")
        return response.json() if response.ok else None

def main():
    parser = argparse.ArgumentParser(description='Search Client')
    parser.add_argument('--demo', action='store_true', help='Run demo')
    args = parser.parse_args()
    
    client = SearchClient()
    
    if args.demo:
        print("Running demo...")
        stats = client.get_stats()
        print(f"Stats: {json.dumps(stats, indent=2)}")
        
        # Create test image
        img = Image.new('RGB', (256, 256), 'blue')
        img.save('demo.jpg')
        
        # Test image search
        results = client.search_by_image('demo.jpg', k=3)
        if results:
            print(f"\nImage search found {results['results_count']} results")
        
        # Test text search
        results = client.search_by_text('blue color', k=3)
        if results:
            print(f"Text search found {results['results_count']} results")

if __name__ == "__main__":
    main()
