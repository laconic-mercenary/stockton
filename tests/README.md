## Overview

Provides the ability to test the services locally - even with Microsoft Azure Function dependencies. 

## Requirements

* docker

## Execution

### Run the Services
```bash
docker-compose up --build
```

### Swagger UI 

The swagger UI is available for testing various requests. 

Open it at http://localhost:8095.

### Direct API Calls

#### Using Header for AUTH
```bash
curl -v -H "X-Gateway-Allow-Token: string" -X POST -d '{ "ticker":"TSLA", "action":"buy", "close":256.34, "contracts":1 }' http://localhost:8098/api/gateway
```

#### Using Signal Key for AUTH
```bash
curl -v -X POST -d '{ "ticker":"TSLA", "action":"buy", "close":256.34, "contracts":1, "key":"string" }' http://localhost:8098/api/gateway
```

#### HTTP/2
```bash
curl -v  -X POST -d '{ "ticker":"TSLA", "action":"buy", "close":256.34, "contracts":1, "key":"string", "notes":"N/A" }' --http2 http://localhost:8098/api/gateway
```

## Shutdown

```bash
docker-compose down
```

curl -v -H "X-Gateway-Allow-Token: string" -X POST -d '{ "ticker":"TSLA", "action":"buy", "close":256.34, "contracts":1,"key":"yR4WnGvoC5po4IYNjipMzdHZ7jzw5eF" }' https://stockton-jpe01-gateway.azurewebsites.net/api/gateway
q