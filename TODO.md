- Add HTTP transport to your codebase
- Add HTTP Docker Image

  FROM python:3.11
  COPY . /app
  WORKDIR /app
  RUN pip install -e .
  CMD ["python", "-m", "ark_market_data_mcp.http_server"]
