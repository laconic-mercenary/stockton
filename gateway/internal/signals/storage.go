package signals

import (
	"bytes"
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"time"

	"github.com/stockton/internal/config"
)

func Store(signal SignalEvent) error {
	signalJson, _ := json.Marshal(signal)
	signalBytes := bytes.NewReader(signalJson)
	req, err := http.NewRequest("POST", getStorageTarget(signal.Ticker), signalBytes)
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("x-functions-key", config.StorageToken())
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return errors.New("received status from storage: " + strconv.FormatInt(resp.StatusCode, 10))
	}
	return nil
}

func getStorageTarget(ticker string) string {
	baseAddr := config.StorageAddress()
	partitionKey := ticker
	rowKey := strconv.FormatInt(time.Now().UnixMilli(), 10)
	return baseAddr + "/" + partitionKey + "/" + rowKey
}
