# OVERVIEW

Request gateway before reaching other functions in stockton.

# PREREQUISITES

## Install
* golang v1.19+
* Azure Core Functions 

# HOWTO

## Build 

```bash
go build cmd/api.go
```

## Run Locally

```bash
func start
```

## Deploy

### login
```bash
az login
```

### list subscriptions
```bash
az account list -o table
```

### set active subscription
```bash
az account set --subscription <SUBSCRIPTION_ID>
```

### create an Azure Resource Group 
```bash
az group create -n stockton-jpe-resources01 -l japaneast
```

### create an Azure Storage Account (required for Azure Functions App)
```bash
az storage account create -n stockton-gateway-jpe-storage01 -g stockton-jpe-resources01 -l japaneast
```

### create an Azure Functions App
```bash
az functionapp create -n stockton-gateway-jpe01 \
  -g stockton-jpe-resources01 \
  --consumption-plan-location japaneast \
  --os-type Linux \
  --runtime custom \
  --functions-version 4 \
  --storage-account stockton-gateway-jpe-storage01
```

### build for linux
```bash
GOOS=linux GOARCH=amd64 go build cmd/api.go
```

### publish the function

```bash
func azure functionapp publish stockton-gateway-jpe01
```

# NEW PROJECT

## Creating New Function
```bash
func new -l Custom -t HttpTrigger -n function-name -a anonymous
```