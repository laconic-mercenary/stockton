#!/bin/bash

set -euf -o pipefail

az login

STORAGE_ACCOUNT_NAME='stocktonjpe01storage'
STORAGE_ACCOUNT_KEY=`cat ./.account-key`
STORAGE_ACCOUNT_TABLE_ENDPOINT=`az storage account show --name stocktonjpe01storage | jq '.primaryEndpoints.table'`
DATE_START=`date '+%Y-%m-%d'T'%H:%M'Z''`
DATE_END=`date -v +10y '+%Y-%m-%d'T'%H:%M'Z''`

function create-table() {
    az storage table create --name signals \
                            --account-key ${STORAGE_ACCOUNT_KEY} \
                            --account-name ${STORAGE_ACCOUNT_NAME} \
                            --auth-mode login \
                            --fail-on-exist \
                            --table-endpoint ${STORAGE_ACCOUNT_TABLE_ENDPOINT}
}

function generate-access-policy() {
    az storage table policy create --debug --name signalscrud \
                                    --table-name signals \
                                    --account-key ${STORAGE_ACCOUNT_KEY} \
                                    --account-name ${STORAGE_ACCOUNT_NAME} \
                                    --expiry ${DATE_END} \
                                    --permissions rad \
                                    --start ${DATE_START} \
                                    --table-endpoint ${STORAGE_ACCOUNT_TABLE_ENDPOINT}
}

function generate-sas() {
    az storage table generate-sas --name signals \
                                    --account-key ${STORAGE_ACCOUNT_KEY} \
                                    --account-name ${STORAGE_ACCOUNT_NAME} \
                                    --expiry ${DATE_END} \
                                    --https-only \
                                    --permissions rad \
                                    --start ${DATE_START} \
                                    --table-endpoint ${STORAGE_ACCOUNT_TABLE_ENDPOINT}
}

function generate-connection-string() {
    local table_endpoint=${1}
    local shared_access_signature=${2}
    echo "TableEndpoint=${table_endpoint}; SharedAccessSignature=${shared_access_signature}"
}

##
##create-table

##
generate-access-policy
