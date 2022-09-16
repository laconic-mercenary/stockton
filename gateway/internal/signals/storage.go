package signals

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/rs/zerolog/log"
	"github.com/stockton/internal/config"
)

const (
	storageRequestMethod     = "POST"
	storageAuthTokenHeader   = "x-functions-key"
	storageContentTypeHeader = "Content-Type"
	storageContentTypeValue  = "application/json"
)

func Store(signal SignalEvent) error {
	log.Trace().Msg("Store")
	sanitize(&signal)
	signalJson, _ := json.Marshal(signal)
	signalBytes := bytes.NewReader(signalJson)
	req, err := http.NewRequest(storageRequestMethod, makeStorageURL(signal.Ticker), signalBytes)
	if err != nil {
		return err
	}
	setHeaders(req)
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return errors.New("received status from storage: " + strconv.FormatInt(int64(resp.StatusCode), 10))
	}
	return nil
}

func setHeaders(request *http.Request) {
	log.Trace().Msg("setHeaders")
	request.Header.Set(storageContentTypeHeader, storageContentTypeValue)
	request.Header.Set(storageAuthTokenHeader, config.StorageToken())
}

func sanitize(signal *SignalEvent) {
	log.Trace().Msg("sanitize")
	signal.Key = ""
}

func makeStorageURL(ticker string) string {
	log.Trace().Msg("getStorageTarget")
	baseAddr := config.StorageAddress()
	partitionKey := ticker
	rowKey := strconv.FormatInt(currentMillis(), 10)
	return fmt.Sprintf("%s/%s/%s", baseAddr, partitionKey, rowKey)
}

func currentMillis() int64 {
	log.Trace().Msg("currentMillis")
	return time.Now().UnixMilli()
}
