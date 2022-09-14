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
	envStorageAddress             = "STORAGE_ADDRESS"
	envStorageToken               = "STORAGE_TOKEN"
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
	return lookupOrFail(envAuthorizationToken)
}

func StorageAddress() string {
	return lookupOrFail(envStorageAddress)
}

func StorageToken() string {
	return lookupOrFail(envStorageToken)
}

func lookupOrFail(env string) string {
	if val, ok := os.LookupEnv(env); ok {
		return val
	}
	log.Fatal().Err(errors.New("missing env var: " + env)).Msg("required env var missing")
	return ""
}
