# OVERVIEW

A complete automated trading system using price action trends on high and low time frames to place market orders at key times.

Supports any ticker or currency on TradingView - as long as your broker has an API and also supports the ticker (ex: IBKR).

## Key Components

### Trading View
Trading View is a robust trading toolset found on the web that allows you to view and trade stocks, currencies, and more. It supports many exchanges and has a robust API that allows you to automate trading via alerts + webhooks.

For more information, visit [Trading View](https://www.tradingview.com/)

### Azure Functions
Azure Functions is a serverless compute service that allows you to run code in response to events. The primary motiviation on using functions is to save costs. 

#### Microservices
- Gateway

Golang application that provides authentication and validation of the signals coming from Trading View. After valiation it will post the messages to the Azure Queue.

- Storage

Java application that stores the signals coming from Trading View for later analysis - and further offers an HTTP API for retrieving the signals.

- Reports

HTNL-based email reports on how your strategy is doing.

- Flow Merchant

Implments trend following strategy by tracking when signals come from high and low time frames. Interacts with your broker API to place market orders. Stores the orders in Azure Table Storage.

### Your Broker API

Your broker should support an API - for example, the IBKR API. 

## Requirements
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Azure Functions Core Tools](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=linux%2Ccsharp%2Cbash#install-the-azure-functions-core-tools)
- [Azure Subscription](https://azure.microsoft.com/en-us/free/)
- [Azure Storage Account](https://docs.microsoft.com/en-us/azure/storage/common/storage-account-create?tabs=azure-portal)
- [Azure Functions](https://docs.microsoft.com/en-us/azure/azure-functions/functions-overview)
- [Azure Queue Storage](https://docs.microsoft.com/en-us/azure/storage/queues/storage-queues-introduction)
- [Azure Table Storage](https://docs.microsoft.com/en-us/azure/cosmos-db/table-storage-overview)
- [TradingView Account](https://www.tradingview.com/)

# LOCAL TESTING

See [TEST README](./tests/README.md).

# DEPLOYMENT

* For Gateway, see [Gateway](./gateway/README.md).
* For Storage, see [Storage](./storage/README.md).
* For Reports, see [Reports](./reports/README.md).
- For Flow Merchant, see [Flow Merchant](./flow-merchant/README.md).