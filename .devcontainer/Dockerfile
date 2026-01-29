FROM mcr.microsoft.com/devcontainers/python:3.14-trixie

# System dependencies for psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace