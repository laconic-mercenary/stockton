package internal

import (
	"io"
	"net/http"
	"strings"

	"github.com/stockton/internal/config"
	"github.com/stockton/internal/signals"

	"github.com/rs/zerolog/log"
)

const (
	headerContentType = "Content-Type"
	contentTypeJson   = "application/json"
)

func Gateway(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("Gateway")
	if !isAuthorized(request) {
		log.Warn().Msg("user not authorized")
		http.Error(writer, "not authorized", http.StatusUnauthorized)
		return
	}
	ops := allowedOperations()
	if op, ok := ops[request.Method]; ok {
		op(writer, request)
		return
	}
	log.Warn().Str("method", request.Method).Msg("method not allowed")
	http.Error(writer, "not allowed", http.StatusMethodNotAllowed)
}

func isAuthorized(request *http.Request) bool {
	log.Trace().Msg("isAuthorized")
	secureToken := config.AuthorizationToken()
	if strings.Compare(secureToken, "ALLOW") == 0 {
		return true
	}
	if auth, ok := request.Header["XX-allow-token"]; ok {
		log.Debug().Msg("token provided")
		if len(auth) == 1 {
			userProvidedToken := auth[0]
			log.Debug().Str("token", userProvidedToken).Msg("user token info")
			return (strings.Compare(secureToken, userProvidedToken) == 0)
		}
	}
	return false
}

func handlePost(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("handlePost")
	var data []byte
	var err error
	defer request.Body.Close()
	if data, err = io.ReadAll(request.Body); err != nil {
		log.Error().Err(err).Msg("error on reading request.Body")
		http.Error(writer, "server error", http.StatusInternalServerError)
		return
	}
	// log.Debug().Int("length", len(data)).RawJSON("json", data).Msg("request json")
	var signal signals.SignalEvent
	if signal, err = signals.ParseSignal(data); err != nil {
		log.Warn().RawJSON("data", data).Msg("user provided invalid json")
		http.Error(writer, "bad request", http.StatusBadRequest)
		return
	}
	responseData, _ := signals.SignalToData(signal)
	log.Info().RawJSON("response", responseData).Msg("response OK")
	writer.Header().Add(headerContentType, contentTypeJson)
	writer.WriteHeader(http.StatusOK)
	writer.Write(responseData)
}

func handleGet(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("handleGet")
	//name := request.URL.Query().Get("name")
	// http.NotFound(writer, request)
	http.StatusText(http.StatusOK)
}

func allowedOperations() map[string]func(writer http.ResponseWriter, request *http.Request) {
	log.Trace().Msg("allowedOperations")
	return map[string]func(writer http.ResponseWriter, request *http.Request){
		http.MethodPost: handlePost,
		http.MethodGet:  handleGet,
	}
}
