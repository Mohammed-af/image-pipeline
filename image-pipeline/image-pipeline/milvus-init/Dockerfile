FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir pymilvus==2.3.3 requests==2.31.0 Pillow==10.1.0 marshmallow==3.20.1
COPY init_milvus_dual.py init_milvus_dual.py
CMD ["python", "-u", "init_milvus_dual.py"]
