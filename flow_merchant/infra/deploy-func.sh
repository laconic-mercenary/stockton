#!/bin/bash

set -euf -o pipefail

echo "Logging in to Azure..."
az login

func azure functionapp publish stockton-flow-merchant-function
