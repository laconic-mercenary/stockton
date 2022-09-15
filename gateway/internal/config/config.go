package config

import (
	"errors"
	"os"
	"strconv"
	"strings"

	"github.com/rs/zerolog"
	"github.com/rs/zerolog/log"
)

const (
	envFunctionsCustomHandlerPort = "FUNCTIONS_CUSTOMHANDLER_PORT"
	envLoggingLevel               = "LOGGING_LEVEL"
	envDebugRequests              = "LOG_REQUESTS"
	envAuthorizationToken         = "AUTHORIZATION_TOKEN"
	envAllowedOrigin              = "ALLOWED_ORIGIN"
	envRequireSignalKey           = "REQUIRE_SIGNAL_KEY"
	envStorageAddress             = "STORAGE_ADDRESS"
	envStorageToken               = "STORAGE_TOKEN"
)

func ServerAddress() string {
	if val, ok := os.LookupEnv(envFunctionsCustomHandlerPort); ok {
		return ":" + val
	}
	return ":8080"
}

func LogRequests() bool {
	if val, ok := os.LookupEnv(envDebugRequests); ok {
		logRequests, err := strconv.ParseBool(val)
		if err != nil {
			log.Fatal().Err(err).Msg("invalid value configured for " + envDebugRequests)
		}
		return logRequests
	}
	return false
}

func RequireSignalKey() bool {
	if val, ok := os.LookupEnv(envRequireSignalKey); ok {
		requireSignalKey, err := strconv.ParseBool(val)
		if err != nil {
			log.Fatal().Err(err).Msg("invalid value configured for " + envRequireSignalKey)
		}
		return requireSignalKey
	}
	return false
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

func AuthenticationToken() (token string, allowAll bool) {
	token = lookupOrFail(envAuthorizationToken)
	allowAll = (token == "ALLOW")
	return
}

func AllowedOrigin() (domain string, allowAny bool) {
	domain = lookupOrFail(envAllowedOrigin)
	allowAny = (domain == "*")
	return
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
