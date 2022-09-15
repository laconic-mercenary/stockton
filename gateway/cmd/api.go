package main

import (
	"net/http"

	"github.com/stockton/internal"
	"github.com/stockton/internal/config"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

func main() {
	zerolog.SetGlobalLevel(config.LoggingLevel())
	http.HandleFunc("/api/gateway", internal.Gateway)
	log.Fatal().Err(http.ListenAndServe(config.ServerAddress(), nil)).Msg("finished")
}
