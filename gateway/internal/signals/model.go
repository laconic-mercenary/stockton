package signals

import (
	"encoding/json"

	"github.com/go-playground/validator"
)

type SignalEvent struct {
	Ticker         string  `json:"ticker" validate:"required"`
	Action         string  `json:"action" validate:"oneof=buy sell"`
	Close          float64 `json:"close" validate:"gt=0.0,lte=9999999.99"`
	ContractsCount int     `json:"contracts" validate:"gte=1,lte=9999"`
	Notes          string  `json:"notes,omitempty" validate:"lt=256"`
	Key            string  `json:"key,omitempty" validate:"lt=256"`
}

func ParseSignal(data []byte) (SignalEvent, error) {
	var err error
	var event SignalEvent = SignalEvent{}
	if err = json.Unmarshal(data, &event); err != nil {
		return event, err
	}
	return event, validator.New().Struct(event)
}

func ParseSignals(data []byte) ([]SignalEvent, error) {
	var err error
	var events []SignalEvent = make([]SignalEvent, 0)
	if err = json.Unmarshal(data, &events); err != nil {
		return nil, err
	}
	signalValidator := validator.New()
	for i := 0; i < len(events); i++ {
		if err = signalValidator.Struct(events[i]); err != nil {
			return nil, err
		}
	}
	return events, nil
}

func SignalToData(signal SignalEvent) ([]byte, error) {
	return json.Marshal(signal)
}

func SignalsToData(signals []SignalEvent) ([]byte, error) {
	return json.Marshal(signals)
}
