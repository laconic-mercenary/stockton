package signals

import (
	"context"

	"github.com/rs/zerolog/log"
)

func Store(signal SignalEvent, ctx context.Context) error {
	log.Trace().Msg("Store")
	sanitize(&signal)
	return enqueue(signal, ctx)
}

func sanitize(signal *SignalEvent) {
	log.Trace().Msg("sanitize")
	signal.Key = ""
}
