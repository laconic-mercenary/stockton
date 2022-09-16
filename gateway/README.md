# OVERVIEW

Request gateway before reaching other functions in stockton.

# PREREQUISITES

## Installation Requirements
* golang v1.19+
* Azure Core Functions 

# HOWTO

## Build 

* Build the executeable with go 
```bash
go build cmd/api.go
```

* Build with Docker
```bash
docker build .
```

## Run Locally

### Azure Functions Core Runtime
```bash
func start
```

### Docker
```bash
docker build . -t=gateway:local
docker run gateway:local
```

### Docker E2E Test

1. CD to ```tests``` directory

2. Run docker-compose
```bash
docker-compose up --build
```

3. Check the [README](./../tests/README.md) and execute some test requests

## Install

1. login
```bash
az login
```

2. list subscriptions
```bash
az account list -o table
```

3. set active subscription
```bash
az account set --subscription <SUBSCRIPTION_ID>
```

4. create an Azure Resource Group 
```bash
az group create -n stockton-jpe01 -l japaneast
```

5. create an Azure Storage Account (required for Azure Functions App)
```bash
az storage account create -n stockton-jpe01-gateway -g stockton-jpe01 -l japaneast
```

6. create an Azure Functions App
```bash
az functionapp create -n stockton-jpe01-gateway \
  -g stockton-jpe01 \
  --consumption-plan-location japaneast \
  --os-type Linux \
  --runtime custom \
  --functions-version 4 \
  --storage-account stockton-jpe01-gateway
```

7. build for linux
```bash
GOOS=linux GOARCH=amd64 go build cmd/api.go
```

8. publish the function

```bash
func azure functionapp publish stockton-jpe01-gateway
```

# NEW PROJECT

## Creating New Function
```bash
func new -l Custom -t HttpTrigger -n function-name -a anonymous
```