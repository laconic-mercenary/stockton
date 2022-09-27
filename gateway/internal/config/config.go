package config

import (
	"encoding/base64"
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
	envRequireAuthHeader          = "REQUIRE_AUTH_HEADER"
	envStorageAddress             = "STORAGE_ADDRESS"
	envStorageToken               = "STORAGE_TOKEN"
	envSignalQueueUrl             = "SIGNAL_QUEUE_URL"
	envSignalQueueAccountName     = "SIGNAL_QUEUE_ACCOUNT_NAME"
	envSignalQueueAccountKey      = "SIGNAL_QUEUE_ACCOUNT_KEY"
	envSignalQueueMessageTTL      = "SIGNAL_QUEUE_MESSAGE_TTL"
	envSignalQueueClientTimeout   = "SIGNAL_QUEUE_CLIENT_TIMEOUT"
	envSignalQueueClientRetry     = "SIGNAL_QUEUE_CLIENT_RETRIES"
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
			log.Fatal().Err(err).Str("key", envRequireSignalKey).Msg("invalid value specified")
		}
		return requireSignalKey
	}
	return false
}

func RequireAuthHeader() bool {
	if val, ok := os.LookupEnv(envRequireAuthHeader); ok {
		requireAuthHeader, err := strconv.ParseBool(val)
		if err != nil {
			log.Fatal().Err(err).Str("key", envRequireAuthHeader).Msg("invalid value specified")
		}
		return requireAuthHeader
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
	token := lookupOrFail(envStorageToken)
	data, err := base64.StdEncoding.DecodeString(token)
	if err != nil {
		log.Fatal().Err(err).Str("token", token).Msg("failed to decode base64 token")
	}
	log.Debug().Bytes("data", data).Str("b64token", token).Msg("storage token information")
	return strings.TrimSpace(string(data))
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

func SignalQueueClientTimeout() time.Duration {
	clientTimeout := lookupOrFail(envSignalQueueClientTimeout)
	result, err := time.ParseDuration(clientTimeout)
	if err != nil {
		log.Fatal().Err(err).Str("clientTimeout", clientTimeout).Msg("invalid client timeout")
	}
	return result
}

func SignalQueueClientRetry() int32 {
	clientRetries := lookupOrFail(envSignalQueueClientRetry)
	result, err := strconv.ParseInt(clientRetries, 10, 32)
	if err != nil {
		log.Fatal().Err(err).Str("clientRetries", clientRetries).Msg("invalid client retry (invalid format)")
	}
	if result < 1 || result > 10 {
		log.Fatal().Err(err).Str("clientRetries", clientRetries).Msg("invalid client retry (out of range)")
	}
	return int32(result)
}

func lookupOrFail(env string) string {
	val, ok := os.LookupEnv(env)
	if !ok {
		log.Fatal().Str("env_var", env).Msg("required env var missing")
	}
	return val
}
