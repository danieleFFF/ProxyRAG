FROM python:3.12-slim

WORKDIR /app

# install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy project code
COPY . .

# default command — overridden per service in docker-compose.yml
CMD ["python", "proxy/proxy/agent.py", "--port", "8001"]
