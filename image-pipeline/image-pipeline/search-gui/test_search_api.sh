#!/bin/bash
echo "Testing Cross-Modal Search API..."
echo ""

# Test health
echo "1. Health check:"
curl -s http://localhost:3000/health && echo " - OK"

# Test stats
echo -e "\n2. Stats:"
curl -s http://localhost:3000/stats | python3 -m json.tool

# Create test image
echo -e "\n3. Creating test image..."
python3 -c "
from PIL import Image
img = Image.new('RGB', (256, 256), color='red')
img.save('test.jpg')
print('Test image created')
"

# Test image search
echo -e "\n4. Testing image search..."
curl -X POST http://localhost:3000/api/search/image?k=3 \
  -F "image=@test.jpg" \
  -s | python3 -m json.tool | head -30

# Test text search
echo -e "\n5. Testing text search..."
curl -X POST http://localhost:3000/api/search/text \
  -H "Content-Type: application/json" \
  -d '{"text": "red color", "k": 3}' \
  -s | python3 -m json.tool | head -30

rm test.jpg
echo -e "\n✅ Tests complete!"
