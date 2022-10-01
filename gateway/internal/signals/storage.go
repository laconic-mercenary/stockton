package signals

import (
	"context"

	"github.com/rs/zerolog/log"
)

const (
	queryRequestMethod       = "GET"
	storageAuthTokenHeader   = "x-storage-auth-key"
	storageContentTypeHeader = "Content-Type"
	storageContentTypeValue  = "application/json"
	errorResponse            = "error"
	maxDataLengthBytes       = (2 * (1 << 20))
)

func Store(signal SignalEvent, ctx context.Context) error {
	log.Trace().Msg("Store")
	sanitize(&signal)
	return enqueue(signal, ctx)
}

// func GetByTicker(ticker string, ctx context.Context) ([]SignalEvent, error) {
// 	log.Trace().Msg("GetByTicker")
// 	var signals []SignalEvent = nil
// 	var err error
// 	var data []byte = nil
// 	var notFound bool
// 	data, notFound, err = makeRequest(queryRequestMethod, makeStorageUrlForGet(ticker), nil, ctx)
// 	if notFound {
// 		return make([]SignalEvent, 0), nil
// 	}
// 	if err != nil {
// 		return nil, err
// 	}
// 	if signals, err = ParseSignals(data); err != nil {
// 		return nil, err
// 	}
// 	return signals, nil
// }

// func makeRequest(method, url string, reader io.Reader, ctx context.Context) ([]byte, bool, error) {
// 	log.Trace().Msg("makeRequest")
// 	ctx, cancel := context.WithTimeout(ctx, time.Duration(time.Second*15))
// 	requestId := fmt.Sprintf("%s", ctx.Value(config.RequestIdKey()))
// 	defer cancel()
// 	log.Debug().Str("requestId", requestId).Str("url", url).Str("method", method).Msg("will make the following request")
// 	req, err := http.NewRequestWithContext(ctx, method, url, reader)
// 	if err != nil {
// 		return nil, false, err
// 	}
// 	setHeaders(req)
// 	if config.LogRequests() {
// 		if _data, _err := httputil.DumpRequest(req, false); _err == nil {
// 			log.Info().Str("requestId", requestId).Bytes("storageRequest", _data).Msg("request logged")
// 		}
// 	}
// 	client := &http.Client{}
// 	resp, err := client.Do(req)
// 	if err != nil {
// 		return nil, false, err
// 	}
// 	defer resp.Body.Close()
// 	data, err := io.ReadAll(resp.Body)
// 	if err != nil {
// 		return nil, false, err
// 	}
// 	if resp.StatusCode == http.StatusNotFound {
// 		return nil, true, nil
// 	}
// 	if resp.StatusCode != http.StatusOK {
// 		return nil, false, fmt.Errorf("received status from storage: %d", resp.StatusCode)
// 	}
// 	if len(data) > maxDataLengthBytes {
// 		return nil, false, fmt.Errorf("response from storage was larger than %d bytes (max allowed)", maxDataLengthBytes)
// 	}
// 	return data, false, nil
// }

// func setHeaders(request *http.Request) {
// 	log.Trace().Msg("setHeaders")
// 	request.Header.Set(storageContentTypeHeader, storageContentTypeValue)
// 	request.Header.Set(storageAuthTokenHeader, config.StorageToken())
// }

func sanitize(signal *SignalEvent) {
	log.Trace().Msg("sanitize")
	signal.Key = ""
}

// func makeStorageUrlForGet(ticker string) string {
// 	log.Trace().Msg("makeStorageUrlForGet")
// 	baseAddr := config.StorageAddress()
// 	return fmt.Sprintf("%s/%s", baseAddr, ticker)
// }
