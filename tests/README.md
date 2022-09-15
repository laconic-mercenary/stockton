## Execution

### Run the Services
```bash
docker-compose up --build
```

### Using Header for AUTH
```bash
curl -v -H "X-Gateway-Allow-Token: test-0QEmRXHwkp4sRXLTKpJLE3RQFTS01xk8" -X POST -d '{ "ticker":"TSLA", "action":"buy", "close":256.34, "contracts":1 }' http://localhost:8080/api/gateway
```

### Using Signal Key for AUTH
```bash
curl -v -X POST -d '{ "ticker":"TSLA", "action":"buy", "close":256.34, "contracts":1, "key":"test-0QEmRXHwkp4sRXLTKpJLE3RQFTS01xk8" }' http://localhost:8080/api/gateway
```

### HTTP/2
```bash
curl -v  -X POST -d '{ "ticker":"TSLA", "action":"buy", "close":256.34, "contracts":1, "key":"test-0QEmRXHwkp4sRXLTKpJLE3RQFTS01xk8", "notes":"N/A" }' --http2 http://localhost:8080/api/gateway
```