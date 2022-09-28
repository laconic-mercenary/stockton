package signals

import (
	"context"
	"encoding/base64"
	"fmt"
	"time"

	"github.com/Azure/azure-storage-queue-go/azqueue"
	"github.com/rs/zerolog/log"
	"github.com/stockton/internal/config"
)

func enqueue(signal SignalEvent, ctx context.Context) error {
	log.Trace().Msg("enqueue")
	var err error
	requestId := fmt.Sprintf("%s", ctx.Value(config.RequestIdKey()))
	log.Debug().Str("requestId", requestId).Msg("getting credentials...")
	var credential azqueue.Credential
	credential, err = getCredentials()
	if err != nil {
		return err
	}

	log.Debug().Str("requestId", requestId).Msg("creating pipeline...")
	queueUrl := azqueue.NewQueueURL(config.SignalQueueUrl(), azqueue.NewPipeline(credential, getMessageOptions()))

	queueCtx, cancel := getContext(ctx)
	defer cancel()

	log.Debug().Str("requestId", requestId).Msg("getting properties...")
	props, err := getProperties(queueUrl, queueCtx)
	if err != nil {
		return err
	}

	log.Debug().Str("requestId", requestId).Int32("messageCount", props.ApproximateMessagesCount()).Msg("approximate number of messages currently on the queue")

	addRequestId(&signal, requestId)

	var signalMessage string
	signalMessage, err = getSignalMessage(signal)
	if err != nil {
		return err
	}

	err = enqueueMessage(signalMessage, queueCtx, queueUrl)
	if err != nil {
		return err
	}

	return nil
}

func enqueueMessage(signalMessage string, ctx context.Context, queueUrl azqueue.QueueURL) error {
	log.Debug().Msg("enqueuing message...")
	var err error
	var enqueueResult *azqueue.EnqueueMessageResponse
	var messageUrl azqueue.MessagesURL = queueUrl.NewMessagesURL()
	var messageTTL time.Duration = config.SignalQueueMessageTTL()
	enqueueResult, err = messageUrl.Enqueue(ctx, signalMessage, 0, messageTTL)
	if err != nil {
		return err
	}
	requestId := fmt.Sprintf("%s", ctx.Value(config.RequestIdKey()))
	log.Info().Str("requestId", requestId).Str("data", signalMessage).Str("status", enqueueResult.Status()).Str("queueRequestId", enqueueResult.RequestID()).Str("queueMessageId", string(enqueueResult.MessageID)).Msg("enqueued message")
	return nil
}

func getContext(ctx context.Context) (context.Context, context.CancelFunc) {
	return context.WithTimeout(ctx, config.SignalQueueClientTimeout())
}

func getMessageOptions() azqueue.PipelineOptions {
	return azqueue.PipelineOptions{
		Retry: azqueue.RetryOptions{
			MaxTries: config.SignalQueueClientRetry(),
		},
	}
}

func getSignalMessage(signal SignalEvent) (string, error) {
	signalData, err := SignalToData(signal)
	if err != nil {
		return "", err
	}
	signalMessage := base64.StdEncoding.EncodeToString(signalData)
	return signalMessage, nil
}

func addRequestId(signal *SignalEvent, requestId string) {
	if len(signal.Notes) > 0 {
		signal.Notes = ";requestId=" + requestId
	} else {
		signal.Notes = "requestId=" + requestId
	}
}

func getProperties(queueUrl azqueue.QueueURL, ctx context.Context) (*azqueue.QueueGetPropertiesResponse, error) {
	var err error
	var props *azqueue.QueueGetPropertiesResponse
	props, err = queueUrl.GetProperties(ctx)
	if err != nil {
		errorType := err.(azqueue.StorageError).ServiceCode()
		if errorType == azqueue.ServiceCodeQueueNotFound {
			log.Warn().Msg("Queue does not exist, creating")
			_, err = queueUrl.Create(ctx, azqueue.Metadata{})
			if err != nil {
				return nil, err
			}
			props, err = queueUrl.GetProperties(ctx)
			if err != nil {
				return nil, err
			}
		} else {
			return nil, err
		}
	}
	return props, nil
}

func getCredentials() (azqueue.Credential, error) {
	var err error
	var credential azqueue.Credential
	accountName := config.SignalQueueAccountName()
	accountKey := config.SignalQueueAccountKey()
	credential, err = azqueue.NewSharedKeyCredential(accountName, accountKey)
	if err != nil {
		return nil, err
	}
	return credential, nil
}
