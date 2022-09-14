# Execution

```bash
docker-compose up --build
```

```
curl -v -H "XX-allow-token: allow" -X POST -d '{ "ticker":"TSLA", "action":"buy", "close":256.34, "contracts":1 }' http://localhost:8080/api/gateway
```