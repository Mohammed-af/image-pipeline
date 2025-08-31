FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir kafka-python==2.0.2 requests==2.31.0 Pillow==10.1.0 pymilvus==2.3.3 marshmallow==3.20.1
COPY producer_milvus.py producer.py
CMD ["python", "-u", "producer.py"]
