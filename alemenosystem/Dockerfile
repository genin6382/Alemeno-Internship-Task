FROM python:3.12-slim 
  
WORKDIR /app
  
COPY requirements.txt /app/

# Install postgres client for health checks
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*
 
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

RUN chmod +x /app/entrypoint.sh
 
EXPOSE 8000 
 
ENTRYPOINT ["/app/entrypoint.sh"]



