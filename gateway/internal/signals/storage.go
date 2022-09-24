package signals

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/rs/zerolog/log"
	"github.com/stockton/internal/config"
)

const (
	storeRequestMethod       = "POST"
	deleteRequestMethod      = "DELETE"
	queryRequestMethod       = "GET"
	storageAuthTokenHeader   = "x-functions-key"
	storageContentTypeHeader = "Content-Type"
	storageContentTypeValue  = "application/json"
	errorResponse            = "error"
	maxDataLengthBytes       = (2 * (1 << 20))
)

func Store(signal SignalEvent) error {
	log.Trace().Msg("Store")
	sanitize(&signal)
	return enqueue(signal)
}

func DeleteOld() error {
	log.Trace().Msg("DeleteOld")
	_, err := makeRequest(deleteRequestMethod, makeStorageURLForDelete(), nil)
	return err
}

func GetByTicker(ticker string) ([]SignalEvent, error) {
	log.Trace().Msg("GetByTicker")
	var signals []SignalEvent = nil
	var err error
	var data []byte = nil
	if data, err = makeRequest(queryRequestMethod, makeStorageUrlForGet(ticker), nil); err != nil {
		return nil, err
	}
	if signals, err = ParseSignals(data); err != nil {
		return nil, err
	}
	return signals, nil
}

func makeRequest(method, url string, reader io.Reader) ([]byte, error) {
	log.Trace().Msg("makeRequest")
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(time.Second*15))
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, method, url, reader)
	if err != nil {
		return nil, err
	}
	setHeaders(req)
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("received status from storage: %d", resp.StatusCode)
	}
	if len(data) > maxDataLengthBytes {
		return nil, fmt.Errorf("response from storage was larger than %d bytes (max allowed)", maxDataLengthBytes)
	}
	return data, nil
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

func makeStorageUrlForGet(ticker string) string {
	log.Trace().Msg("makeStorageUrlForGet")
	baseAddr := config.StorageAddress()
	return fmt.Sprintf("%s/%s", baseAddr, ticker)
}

func makeStorageURLForDelete() string {
	log.Trace().Msg("makeStorageURLForDelete")
	return config.StorageAddress()
}
