package config

import (
	"errors"
	"os"
	"strings"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

const (
	envFunctionsCustomHandlerPort = "FUNCTIONS_CUSTOMHANDLER_PORT"
	envLoggingLevel               = "LOGGING_LEVEL"
	envAuthorizationToken         = "AUTHORIZATION_TOKEN"
)

func ServerAddress() string {
	if val, ok := os.LookupEnv(envFunctionsCustomHandlerPort); ok {
		return ":" + val
	}
	return ":8080"
}

func LoggingLevel() zerolog.Level {
	if val, ok := os.LookupEnv(envLoggingLevel); ok {
		level := strings.ToUpper(val)
		switch {
		case level == "ERROR":
			return zerolog.ErrorLevel
		case level == "WARN":
			return zerolog.WarnLevel
		case level == "DEBUG":
			return zerolog.DebugLevel
		case level == "TRACE":
			return zerolog.TraceLevel
		case level == "OFF":
			return zerolog.Disabled
		}
	}
	return zerolog.InfoLevel
}

func AuthorizationToken() string {
	if val, ok := os.LookupEnv(envAuthorizationToken); ok {
		return val
	}
	log.Fatal().Err(errors.New("authorization token is required - even if empty")).Msg("required env var missing")
	return ""
}
