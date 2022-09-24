package config

import (
	"net/url"
	"os"
	"strconv"
	"strings"
	"time"

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
	envSignalQueueUrl             = "SIGNAL_QUEUE_URL"
	envSignalQueueAccountName     = "SIGNAL_QUEUE_ACCOUNT_NAME"
	envSignalQueueAccountKey      = "SIGNAL_QUEUE_ACCOUNT_KEY"
	envSignalQueueMessageTTL      = "SIGNAL_QUEUE_MESSAGE_TTL"
	allowAllToken                 = "ALLOW"
	allowAnyOrigin                = "*"
)

func ServerAddress() string {
	if val, ok := os.LookupEnv(envFunctionsCustomHandlerPort); ok {
		if _, err := strconv.ParseUint(val, 10, 32); err != nil {
			log.Fatal().Err(err).Msg("port number must be an unsigned integer")
		}
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
	defaultLevel := zerolog.InfoLevel
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
		default:
			log.Warn().Str("level", val).Str("default", defaultLevel.String()).Msg("unknown log level, will use default")
		}
	}
	return zerolog.InfoLevel
}

func AuthenticationToken() (token string, allowAll bool) {
	token = lookupOrFail(envAuthorizationToken)
	allowAll = (token == allowAllToken)
	return
}

func AllowedOrigin() (domain string, allowAny bool) {
	domain = lookupOrFail(envAllowedOrigin)
	allowAny = (domain == allowAnyOrigin)
	return
}

func StorageAddress() string {
	return lookupOrFail(envStorageAddress)
}

func StorageToken() string {
	return lookupOrFail(envStorageToken)
}

func SignalQueueUrl() url.URL {
	queueUrl := lookupOrFail(envSignalQueueUrl)
	result, err := url.Parse(queueUrl)
	if err != nil {
		log.Fatal().Err(err).Str("url", queueUrl).Msg("failed to parse as url")
	}
	return *result
}

func SignalQueueAccountKey() string {
	return lookupOrFail(envSignalQueueAccountKey)
}

func SignalQueueAccountName() string {
	return lookupOrFail(envSignalQueueAccountName)
}

func SignalQueueMessageTTL() time.Duration {
	ttl := lookupOrFail(envSignalQueueMessageTTL)
	result, err := time.ParseDuration(ttl)
	if err != nil {
		log.Fatal().Err(err).Str("messageTTL", ttl).Msg("invalid message TTL")
	}
	return result
}

func lookupOrFail(env string) string {
	val, ok := os.LookupEnv(env)
	if !ok {
		log.Fatal().Str("env_var", env).Msg("required env var missing")
	}
	return val
}
