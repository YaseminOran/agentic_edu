# Dev container imajı (Hafta 1): Python 3.12 + requirements.txt.
# docker-compose.yml'deki app servisi bu dosyadan derlenir.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
