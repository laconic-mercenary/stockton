package internal

import (
	"fmt"
	"io"
	"net/http"
	"net/http/httputil"
	"regexp"
	"strings"

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
)

var validTicker = regexp.MustCompile(`^[a-zA-Z]{1,75}$`).MatchString

func Gateway(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("Gateway")
	logRequest(request)
	if !isAuthorized(request) {
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
	op(writer, request)
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

func isAuthHeaderAllowed(request *http.Request) bool {
	log.Debug().Msg("checking auth token in header...")
	if config.RequireSignalKey() {
		// TODO - consider cleaner approach
		log.Debug().Msg("will use signal key instead of auth header for auth")
		return true
	}
	secureToken, allowAll := config.AuthenticationToken()
	if !allowAll {
		auth, ok := request.Header[headerAuthToken]
		if !ok {
			log.Warn().Msg(fmt.Sprintf("%s header not found in request - denied", headerAuthToken))
			return false
		}
		if len(auth) != 1 {
			log.Warn().Strs("auth_values", auth).Msg("multiple auth headers specified - denied")
			return false
		}
		userProvidedToken := auth[0]
		log.Debug().Str("token", userProvidedToken).Msg("user token info")
		return (secureToken == userProvidedToken)
	} else {
		log.Warn().Msg("all origins are allowed - please confirm configuration")
	}
	return true
}

func isAuthorized(request *http.Request) bool {
	log.Trace().Msg("isAuthorized")
	return (isAuthHeaderAllowed(request) && isOriginAllowed(request))
}

func isObjectAuthorized(signal signals.SignalEvent) bool {
	if secureToken, allowAll := config.AuthenticationToken(); !allowAll && config.RequireSignalKey() {
		return (secureToken == signal.Key)
	}
	return true
}

func handlePost(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("handlePost")
	var data []byte
	var err error
	defer request.Body.Close()
	if data, err = io.ReadAll(request.Body); err != nil {
		log.Error().Err(err).Msg("error on reading request.Body")
		http.Error(writer, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
		return
	}
	var signal signals.SignalEvent
	if signal, err = signals.ParseSignal(data); err != nil {
		log.Warn().RawJSON("data", data).Err(err).Msg("user provided invalid json")
		http.Error(writer, http.StatusText(http.StatusBadRequest), http.StatusBadRequest)
		return
	}
	if !isObjectAuthorized(signal) {
		log.Warn().Str("key", signal.Key).Msg("invalid signal key provided")
		http.Error(writer, http.StatusText(http.StatusUnauthorized), http.StatusUnauthorized)
		return
	}
	if err = signals.Store(signal); err != nil {
		log.Error().Err(err).Msg("failed to store signal")
		http.Error(writer, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
		return
	}
	responseData, _ := signals.SignalToData(signal)
	log.Info().RawJSON("signal", responseData).Msg("store signal succeeded")
	writer.Header().Add(headerContentType, contentTypeJson)
	writer.WriteHeader(http.StatusOK)
	writer.Write(responseData)
}

func handleGet(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("handleGet")
	ticker := request.URL.Query().Get("ticker")
	if ticker == "" {
		log.Warn().Msg("no `ticker` parameter - assuming healthcheck")
		writer.Header().Add(headerContentType, contentTypeText)
		writer.WriteHeader(http.StatusOK)
		writer.Write([]byte(http.StatusText(http.StatusOK)))
		return
	}
	if !validTicker(ticker) {
		log.Warn().Str("ticker", ticker).Msg("client provided invalid ticker")
		http.Error(writer, http.StatusText(http.StatusBadRequest), http.StatusBadRequest)
		return
	}
	var results []signals.SignalEvent
	var err error
	var data []byte
	log.Debug().Str("ticker", ticker).Msg("fetching signals by ticker...")
	results, err = signals.GetByTicker(ticker)
	if err != nil {
		log.Error().Str("ticker", ticker).Err(err).Msg("failed to query ticker")
		http.Error(writer, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
		return
	}
	log.Info().Str("ticker", ticker).Int("total", len(results)).Msg("successfully fetched signals")
	data, err = signals.SignalsToData(results)
	if err != nil {
		log.Error().Err(err).Msg("failed to serialize signals")
		http.Error(writer, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
		return
	}
	writer.Header().Add(headerContentType, contentTypeJson)
	writer.WriteHeader(http.StatusOK)
	writer.Write(data)
}

func handleDelete(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("handleDelete")
	if err := signals.DeleteOld(); err != nil {
		log.Error().Err(err).Msg("failed to delete old signals")
		http.Error(writer, http.StatusText(http.StatusInternalServerError), http.StatusInternalServerError)
		return
	}
	writer.Header().Add(headerContentType, contentTypeText)
	writer.WriteHeader(http.StatusOK)
	writer.Write([]byte(http.StatusText(http.StatusOK)))
}

func allowedOperations() map[string]func(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("allowedOperations")
	return map[string]func(writer http.ResponseWriter, request *http.Request){
		http.MethodPost:   handlePost,
		http.MethodGet:    handleGet,
		http.MethodDelete: handleDelete,
	}
}
