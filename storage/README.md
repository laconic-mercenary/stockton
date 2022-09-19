# OVERVIEW

CRUD Service for signal storage.

# PREREQUISITES

## Installation Requirements
* Maven
* JDK 11
* Azure Core Functions 

# HOWTO

## Build 

* Build jar with maven
```bash
mvn clean package
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
docker build . -t=storage:local
docker run storage:local
```

### Docker E2E Test

1. CD to ```tests``` directory

2. Run docker-compose
```bash
docker-compose up --build
```

3a. Check the [README](./../tests/README.md) and execute some test requests

3b. Check the OpenAPI UI to send test requests at http://localhost:8095

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

## TODO: add the storage account creation here
## seems it may actually be valid

5. create an Azure Functions App
```bash
az functionapp create -n stockton-jpe01-storage \
  -g stockton-jpe01 \
  --consumption-plan-location japaneast \
  --os-type Linux \
  --runtime java \
  --functions-version 4 \
  --storage-account stocktonjpe01storage
```

6. build and publish the function

```bash
mvn clean package azure-functions:deploy
```

# NEW PROJECT

## Creating New Function
```bash
func new -l Custom -t HttpTrigger -n function-name -a anonymous
```