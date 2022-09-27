package net.revanchism.mlcs.stockton;

import java.util.Arrays;
import java.util.Comparator;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
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

    private static Signal fromMessage(final String signalMessage) throws JacksonException {
        return new ObjectMapper().readValue(signalMessage, Signal.class);
    }

    private static String generateRowKey() {
        return Long.toString(System.currentTimeMillis());
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

    @FunctionName("stockton-delete-old-signals")
    public void deleteOldSignals(@TimerTrigger(name = "timerInfo", 
                                               schedule = "0 30 2 * * *")
                                               final String timerInfo,
                                               final ExecutionContext context)
    {
        final Logger logger = context.getLogger();
        final long current = System.currentTimeMillis();
        final long expiry = (current - Config.getSignalExpiryDays());
        final AtomicInteger counter = new AtomicInteger(0);

        logger.info(String.format("deleting signals older than %d, current is %d", expiry, current));
        
        if (Config.useStubbedStorage()) {
            logger.warning("using stubbed storage - will not delete any signals");
        } else {
            final String connectionString = Config.getSignalsTableConnectionString();
            final TableClient client =  new TableClientBuilder().connectionString(connectionString)
                                                                .tableName(TABLE_NAME)
                                                                .buildClient();
            final String filter = String.format("RowKey le '%s'", expiry);
            final ListEntitiesOptions options = new ListEntitiesOptions().setFilter(filter);
            client.listEntities(options, null, null)
                .stream()
                .forEach(entity -> { 
                    logger.fine(String.format("removing %s - %s", entity.getPartitionKey(), entity.getRowKey()));
                    client.deleteEntity(entity.getPartitionKey(), entity.getRowKey()); 
                    counter.incrementAndGet();
                });

            logger.info(String.format("deleted %d entries", counter.get()));
        }
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

        if (!isAuthorized(request.getHeaders(), logger)) {
            // this looks silly but, AuthorizationLevel seems painful
            logger.warning("user not authorized for request - returning empty response");
            return EMPTY_RESPONSE;
        }

        logger.info(new StringBuilder().append("query for ticker: ")
                                        .append(ticker)
                                        .append(" resulted in ")
                                        .append(signals.length)
                                        .append(" signals")
                                        .toString());

        return Arrays.asList(signals)
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

        logger.info("new request received: " + signalMessage);

        if (StringUtils.isEmpty(signalMessage)){
            logger.severe("signalMessage cannot be empty");
            return;
        }

        Signal queueSignal = null; 
        try {
            queueSignal = fromMessage(signalMessage);
        } catch (final JacksonException ex) {
            logger.severe("validation failures in request");
            ex.printStackTrace();
            return;
        }

        if (!isValidSignal(queueSignal, logger)) {
            logger.severe("validation failures in request");
            return;
        }

        queueSignal.setPartitionKey(queueSignal.getTicker());
        queueSignal.setRowKey(generateRowKey());

        if (Config.useStubbedStorage()) {
            logger.warning("using stubbed storage - will not store the new signal");
        } else {
            outputSignal.setValue(queueSignal);
        }

        logger.info("new signal successfully stored");
    }
}
