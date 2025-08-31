FROM rust:1.82-bookworm AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    pkg-config \
    libssl-dev \
    libsasl2-dev \
    libzstd-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy Cargo files
COPY Cargo.toml ./
COPY src ./src

# Build the application
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    libsasl2-2 \
    libzstd1 \
    postgresql-client \
    wget \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages pymilvus==2.3.3

RUN wget -q https://dl.min.io/client/mc/release/linux-amd64/mc \
    && chmod +x mc && mv mc /usr/local/bin/

WORKDIR /app
COPY --from=builder /app/target/release/rust-backend /app/rust-backend

EXPOSE 3000
CMD ["./rust-backend"]
