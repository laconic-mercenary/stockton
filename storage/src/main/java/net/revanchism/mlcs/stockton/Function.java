package net.revanchism.mlcs.stockton;

import java.time.Duration;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;

import com.azure.data.tables.TableClient;
import com.azure.data.tables.TableClientBuilder;
import com.azure.data.tables.models.ListEntitiesOptions;
import com.fasterxml.jackson.core.JacksonException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.microsoft.azure.functions.ExecutionContext;
import com.microsoft.azure.functions.HttpMethod;
import com.microsoft.azure.functions.HttpRequestMessage;
import com.microsoft.azure.functions.HttpResponseMessage;
import com.microsoft.azure.functions.HttpStatus;
import com.microsoft.azure.functions.OutputBinding;
import com.microsoft.azure.functions.annotation.AuthorizationLevel;
import com.microsoft.azure.functions.annotation.BindingName;
import com.microsoft.azure.functions.annotation.FunctionName;
import com.microsoft.azure.functions.annotation.HttpTrigger;
import com.microsoft.azure.functions.annotation.QueueTrigger;
import com.microsoft.azure.functions.annotation.TableInput;
import com.microsoft.azure.functions.annotation.TableOutput;
import com.microsoft.azure.functions.annotation.TimerTrigger;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;

public class Function {

    private static final String TABLE_NAME = "signals";

    private static final String TABLE_CONNECTION_STRING = Config.ENV_SIGNALS_TABLE_CONNSTR;

    private static final String QUEUE_CONNECTION_STRING = "SignalsQueueConnectionString";

    private static final Signal[] EMPTY_RESPONSE = new Signal[0];

    private static final Comparator<Signal> SORT_REVERSE_ROWKEY = Comparator.comparing(Signal::getRowKey).reversed();

    private static final String CRON_DELETE = "0 30 2 * * *";

    private static final Duration STORAGE_TIMEOUT = Duration.ofSeconds(30L);

    private static Signal fromMessage(final String signalMessage) throws JacksonException {
        return new ObjectMapper().readValue(signalMessage, Signal.class);
    }

    private static String generateRowKey() {
        return Long.toString(System.currentTimeMillis());
    }

    private static String generateRequestId() {
        return String.format("req-%d-%d", System.currentTimeMillis(), new Random().nextInt());
    }

    private static boolean isValidSignal(final Signal signal, 
                                         final Logger logger) {
        final Set<ConstraintViolation<Signal>> results = Validation.buildDefaultValidatorFactory()
                                                                   .getValidator()
                                                                   .validate(signal);
        if (!results.isEmpty()) {
            results.stream().forEach(failure -> logger.warning(failure.getMessage()));
            return false;    
        }
        return true;
    }

    private static boolean isAuthorized(final Map<String, String> headers, 
                                        final Logger logger) {
        final String authHeader = Config.getAuthHeaderName();
        if (!headers.containsKey(authHeader)) {
            return false;
        }
        final String userProvidedAuthKey = headers.get(authHeader);
        final String authKey = Config.getAuthHeaderKey();
        return authKey.equals(userProvidedAuthKey);
    }

    private static String listToJson(List<String> list) {
        final StringBuilder json = new StringBuilder();
        json.append("[");
        list.stream().forEach(item -> json.append(item).append(","));
        if (json.length() > 1) {
            json.deleteCharAt(json.lastIndexOf(","));
        }
        json.append("]");
        return json.toString();
    }

    private static void logRequestDuration(final long startMillis, 
                                           final String requestId,
                                           final Logger logger) {
        log(String.format("request completed in %d ms", System.currentTimeMillis() - startMillis), requestId, logger, Level.INFO);
    }

    private static void log(final String message, 
                            final String requestId, 
                            final Logger logger,
                            final Level level) {
        if (logger.isLoggable(level)) {
            logger.log(level, String.format("msg='%s', requestId=%s", message, requestId));
        }
    }

    @FunctionName("stockton-delete-old-signals")
    public void deleteOldSignals(@TimerTrigger(name = "timerInfo", 
                                               schedule = CRON_DELETE)
                                               final String timerInfo,
                                               final ExecutionContext context)
    {
        final Logger logger = context.getLogger();
        final long current = System.currentTimeMillis();
        final long expiry = (current - Config.getSignalExpiryDays());
        final String requestId = generateRequestId();
        final AtomicInteger counter = new AtomicInteger(0);

        log(String.format("deleting signals older than %d, current is %d", expiry, current), requestId, logger, Level.INFO);
        
        if (Config.useStubbedStorage()) {
            log("using stubbed storage - will not delete any signals", requestId, logger, Level.WARNING);
        } else {
            final TableClient client =  new TableClientBuilder().connectionString(Config.getSignalsTableConnectionString())
                                                                .tableName(TABLE_NAME)
                                                                .buildClient();
            final String filter = String.format("RowKey le '%s'", expiry);
            final ListEntitiesOptions options = new ListEntitiesOptions().setFilter(filter);
            client.listEntities(options, STORAGE_TIMEOUT, null)
                .stream()
                .forEach(entity -> { 
                    if (logger.isLoggable(Level.FINE)) {
                        log(String.format("removing %s - %s", entity.getPartitionKey(), entity.getRowKey()), requestId, logger, Level.FINE);
                    }
                    client.deleteEntity(entity.getPartitionKey(), entity.getRowKey());
                    counter.incrementAndGet();
                });
        }
        logger.info(String.format("deleted %d entries", counter.get()));
        logRequestDuration(current, requestId, logger);
    }

    @FunctionName("stockton-get-tickers")
    public HttpResponseMessage getTickers(@HttpTrigger(name = "getTickers",
                                                        methods = { HttpMethod.GET }, 
                                                        authLevel = AuthorizationLevel.ANONYMOUS,
                                                        route = "signals/tickers") 
                                            final HttpRequestMessage<Optional<Signal>> request,
                                            final ExecutionContext context) {
        final Logger logger = context.getLogger();
        final long current = System.currentTimeMillis();
        final String requestId = generateRequestId();
        List<String> results = Collections.emptyList();

        if (!isAuthorized(request.getHeaders(), logger)) {
            // this looks silly but, AuthorizationLevel seems painful
            log("user not authorized for request - returning empty response", requestId, logger, Level.WARNING);
            return request.createResponseBuilder(HttpStatus.UNAUTHORIZED)
                            .header("Content-Type", "text/plain")
                            .body(HttpStatus.UNAUTHORIZED.toString())
                            .build();
        }
        
        if (Config.useStubbedStorage()) {
            log("using stubbed storage - will not delete any signals", requestId, logger, Level.WARNING);
        } else {
            final TableClient client =  new TableClientBuilder().connectionString(Config.getSignalsTableConnectionString())
                                                                .tableName(TABLE_NAME)
                                                                .buildClient();
            final ListEntitiesOptions options = new ListEntitiesOptions().setSelect(Arrays.asList("ticker"));
            results = client.listEntities(options , STORAGE_TIMEOUT, null)
                            .stream()
                            .map(entity -> entity.getPartitionKey()) // partitionKey ... which should be the ticker
                            .distinct()
                            .sorted()
                            .collect(Collectors.toList());
        }
        logRequestDuration(current, requestId, logger);
        return request.createResponseBuilder(HttpStatus.ACCEPTED)
                        .header("Content-Type", "application/json")
                        .body(listToJson(results))
                        .build();
    }

    @FunctionName("stockton-get-signals")
    public Signal[] getSignals(@HttpTrigger(name = "getSignalsByTicker",
                                            methods = { HttpMethod.GET }, 
                                            authLevel = AuthorizationLevel.ANONYMOUS,
                                            route = "signals/{ticker}") 
                                final HttpRequestMessage<Optional<Signal>> request,
                                @BindingName("ticker") 
                                final String ticker,
                                @TableInput(name=TABLE_NAME, 
                                            filter="ticker eq '{ticker}'", 
                                            take = "9999", 
                                            tableName = TABLE_NAME, 
                                            connection = TABLE_CONNECTION_STRING) 
                                final Signal[] signals,
                                final ExecutionContext context)
    {
        final Logger logger = context.getLogger();
        final String requestId = generateRequestId();
        final long startMillis = System.currentTimeMillis();

        if (!isAuthorized(request.getHeaders(), logger)) {
            // this looks silly but, AuthorizationLevel seems painful
            log("user not authorized for request - returning empty response", requestId, logger, Level.WARNING);
            return EMPTY_RESPONSE;
        }

        log(new StringBuilder().append("query for ticker: ")
                                        .append(ticker)
                                        .append(" resulted in ")
                                        .append(signals.length)
                                        .append(" signals")
                                        .toString(), requestId, logger, Level.INFO);

        final Signal[] results = Arrays.asList(signals)
                                        .stream()
                                        .sorted(SORT_REVERSE_ROWKEY)
                                        .map(signal -> {
                                                String notes = signal.getNotes();
                                                if (StringUtils.isEmpty(notes)) {
                                                    notes = "";
                                                } else {
                                                    notes = notes + ";";
                                                }
                                                notes = notes + "timestamp=" + signal.getRowKey();
                                                signal.setNotes(notes);
                                                return signal;
                                            })
                                        .collect(Collectors.toUnmodifiableList())
                                        .toArray(new Signal[signals.length]);
        logRequestDuration(startMillis, requestId, logger);
        return results;
    }

    @FunctionName("stockton-store-signal")
    public void storeSignal (@QueueTrigger(name = "signalMessage",
                                           queueName = TABLE_NAME,
                                           connection = QUEUE_CONNECTION_STRING)
                            final String signalMessage,
                            @TableOutput(name = TABLE_NAME, 
                                        tableName = TABLE_NAME, 
                                        connection = TABLE_CONNECTION_STRING) 
                            final OutputBinding<Signal> outputSignal,
                            final ExecutionContext context)
    {
        final Logger logger = context.getLogger();
        final String requestId = generateRequestId();
        final long startMillis = System.currentTimeMillis();

        log("new request received: " + signalMessage, requestId, logger, Level.FINE);

        if (StringUtils.isEmpty(signalMessage)){
            log("signalMessage cannot be empty", requestId, logger, Level.SEVERE);
            return;
        }

        Signal queueSignal = null; 
        try {
            queueSignal = fromMessage(signalMessage);
        } catch (final JacksonException ex) {
            log("validation failures in request", requestId, logger, Level.SEVERE);
            ex.printStackTrace();
            return;
        }

        if (!isValidSignal(queueSignal, logger)) {
            log("validation failures in request", requestId, logger, Level.SEVERE);
            return;
        }

        queueSignal.setPartitionKey(queueSignal.getTicker());
        queueSignal.setRowKey(generateRowKey());

        if (Config.useStubbedStorage()) {
            log("using stubbed storage - will not store the new signal", requestId, logger, Level.WARNING);
        } else {
            outputSignal.setValue(queueSignal);
        }

        log("new signal successfully stored", requestId, logger, Level.INFO);
        logRequestDuration(startMillis, requestId, logger);
    }
}
