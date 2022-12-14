package internal

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/stockton/internal/config"
	"github.com/stockton/internal/signals"

	"github.com/rs/zerolog/log"
)

const (
	headerContentType = "Content-Type"
	headerOrigin      = "Origin"
	headerAuthToken   = "X-Gateway-Allow-Token"
	contentTypeJson   = "application/json"
	contentTypeText   = "text/plain"
	keyRequestId      = "requestId"
)

func Gateway(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("Gateway")
	timestampStart := time.Now().UnixMilli()
	logRequest(request)
	if config.HoneyPotMode() {
		log.Warn().Msg("HONEY POT MODE - will not handle requests")
		handleHoneyPot(writer, request)
		return
	}
	if !isOriginAllowed(request) {
		log.Warn().Msg("request not authorized")
		http.Error(writer, http.StatusText(http.StatusUnauthorized), http.StatusUnauthorized)
		return
	}
	op, ok := allowedOperations()[request.Method]
	if !ok {
		log.Warn().Str("method", request.Method).Msg("method not allowed")
		http.Error(writer, http.StatusText(http.StatusMethodNotAllowed), http.StatusMethodNotAllowed)
		return
	}
	requestId := uuid.New().String()
	ctx := createContext(requestId)
	op(writer, request, ctx)
	logRequestDuration(timestampStart, requestId)
}

func logRequestDuration(start int64, requestId string) {
	log.Trace().Msg("logRequestDuration")
	end := time.Now().UnixMilli()
	log.Info().Int64("elapsedMillis", end-start).Str(keyRequestId, requestId).Msg("request finished")
}

func logRequest(request *http.Request) {
	if config.LogRequests() {
		data, err := httputil.DumpRequest(request, true)
		if err != nil {
			log.Error().Err(err).Msg("error in dumping request")
		} else {
			log.Info().Bytes("request", data).Msg("logged-request")
		}
	}
}

func isOriginAllowed(request *http.Request) bool {
	log.Trace().Msg("isOriginAllowed")
	log.Debug().Msg("checking origin...")
	allowedDomain, allowAny := config.AllowedOrigin()
	if !allowAny {
		hosts, ok := request.Header[headerOrigin]
		if !ok {
			log.Warn().Msg(fmt.Sprintf("%s header not found in request", headerOrigin))
			return false
		}
		allowedOrigin := strings.Replace(allowedDomain, "*", "", 1)
		for i := 0; i < len(hosts); i++ {
			log.Debug().Str("host", hosts[i]).Msg("checking allowed host...")
			if !strings.HasSuffix(hosts[i], allowedOrigin) {
				log.Warn().Str("host", hosts[i]).Msg("host failed origin allow check")
				return false
			}
		}
	} else {
		log.Warn().Msg("all origins are allowed - please confirm configuration")
	}
	return true
}

func isAuthHeaderAllowed(request *http.Request, requestId string) bool {
	log.Trace().Msg("isAuthHeaderAllowed")
	log.Debug().Msg("checking auth token in header...")
	secureToken, allowAll := config.AuthenticationToken()
	if !allowAll {
		auth, ok := request.Header[headerAuthToken]
		if !ok {
			log.Warn().Str("header", headerAuthToken).Msg("header not found in request - access denied")
			return false
		}
		if len(auth) != 1 {
			log.Warn().Strs("authValues", auth).Msg("multiple auth headers specified - access denied")
			return false
		}
		userProvidedToken := auth[0]
		log.Debug().Str("token", userProvidedToken).Msg("user token info")
		return (secureToken == userProvidedToken)
	} else {
		log.Warn().Msg("all origins are allowed - this should not be used in PRODUCTION")
	}
	return true
}

func isObjectAuthorized(signal signals.SignalEvent) bool {
	log.Trace().Msg("isObjectAuthorized")
	if secureToken, allowAll := config.AuthenticationToken(); !allowAll {
		return (secureToken == signal.Key)
	}
	return true
}

func setCORSHeaders(writer http.ResponseWriter, allHeaders bool) {
	log.Trace().Msg("setCORSHeaders")
	origin, allowAny := config.AllowedOrigin()
	if allowAny {
		origin = "*"
	}
	writer.Header().Set("Access-Control-Allow-Origin", origin)
	if allHeaders {
		writer.Header().Set("Access-Control-Allow-Methods", http.MethodPost+","+http.MethodOptions)
		writer.Header().Set("Access-Control-Allow-Headers", "Accept, Content-Type, Content-Length, "+headerAuthToken)
		writer.Header().Set("Access-Control-Max-Age", "600") // 10 minutes
	}
}

func allowedOperations() map[string]func(writer http.ResponseWriter, request *http.Request, ctx context.Context) {
	log.Trace().Msg("allowedOperations")
	return map[string]func(writer http.ResponseWriter, request *http.Request, ctx context.Context){
		http.MethodPost:    handlePost,
		http.MethodOptions: handleOptions,
	}
}

func createContext(requestId string) context.Context {
	log.Trace().Msg("createContext")
	return context.WithValue(context.Background(), config.RequestIdKey(), requestId)
}

func handleHoneyPot(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("handleHoneyPot")
	writer.Header().Add(headerContentType, contentTypeText)
	writer.WriteHeader(http.StatusOK)
	writer.Write([]byte(http.StatusText(http.StatusOK)))
}

func handleOptions(writer http.ResponseWriter, request *http.Request, ctx context.Context) {
	log.Trace().Msg("handleOptions")
	log.Debug().Msg("options handled")
	setCORSHeaders(writer, true)
	writer.Header().Add(headerContentType, contentTypeText)
	writer.WriteHeader(http.StatusNoContent)
}

func handlePost(writer http.ResponseWriter, request *http.Request, ctx context.Context) {
	log.Trace().Msg("handlePost")
	requestId := fmt.Sprintf("%s", ctx.Value(config.RequestIdKey()))
	setCORSHeaders(writer, false)
	if config.RequireAuthHeader() {
		if !isAuthHeaderAllowed(request, requestId) {
			log.Warn().Str(keyRequestId, requestId).Msg("unauthorized header")
			http.Error(writer, http.StatusText(http.StatusUnauthorized), http.StatusUnauthorized)
			return
		}
	}

	var data []byte
	var err error
	defer request.Body.Close()
	if data, err = io.ReadAll(request.Body); err != nil {
		log.Error().Str(keyRequestId, requestId).Err(err).Msg("error on reading request.Body")
		http.Error(writer, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
		return
	}

	var signal signals.SignalEvent
	if signal, err = signals.ParseSignal(data); err != nil {
		log.Warn().Str(keyRequestId, requestId).RawJSON("data", data).Err(err).Msg("user provided invalid json")
		http.Error(writer, http.StatusText(http.StatusBadRequest), http.StatusBadRequest)
		return
	}

	if config.RequireSignalKey() {
		if !isObjectAuthorized(signal) {
			log.Warn().Str(keyRequestId, requestId).Str("key", signal.Key).Msg("invalid signal key provided")
			http.Error(writer, http.StatusText(http.StatusUnauthorized), http.StatusUnauthorized)
			return
		}
	}

	if err = signals.Store(signal, ctx); err != nil {
		log.Error().Str(keyRequestId, requestId).Err(err).Msg("failed to store signal")
		http.Error(writer, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
		return
	}

	responseData, _ := signals.SignalToData(signal)
	log.Info().Str(keyRequestId, requestId).RawJSON("signal", responseData).Msg("store signal succeeded")
	writer.Header().Add(headerContentType, contentTypeJson)
	writer.WriteHeader(http.StatusOK)
	writer.Write(responseData)
}
