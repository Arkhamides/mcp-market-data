FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -e .

EXPOSE 8000

ENV HTTP_HOST=0.0.0.0
ENV HTTP_PORT=8000

CMD ["ark-market-data-mcp-http"]
