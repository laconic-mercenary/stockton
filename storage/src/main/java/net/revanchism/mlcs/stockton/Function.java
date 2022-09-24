package net.revanchism.mlcs.stockton;

import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Logger;

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
                                                                .tableName("signals")
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
        }
    }

    @FunctionName("stockton-get-signals")
    public Signal[] getSignals(@HttpTrigger(name = "getSignalsByTicker",
                                            methods = {HttpMethod.GET}, 
                                            authLevel = AuthorizationLevel.ANONYMOUS, 
                                            route="signals/{ticker}") 
                                final HttpRequestMessage<Optional<Signal>> request,
                                @BindingName("ticker") 
                                final String ticker,
                                @TableInput(name="signals", 
                                            filter="ticker eq '{ticker}'", 
                                            take = "9999", 
                                            tableName="signals", 
                                            connection="SignalsStorageConnectionString") 
                                final Signal[] signals,
                                final ExecutionContext context)
    {
        final String log = new StringBuilder().append("query for ticker: ")
                                              .append(ticker)
                                              .append(" resulted in ")
                                              .append(signals.length)
                                              .append(" signals")
                                              .toString();
        context.getLogger().info(log);
        return signals;
    }

    @FunctionName("stockton-store-signal")
    public void storeSignal (@QueueTrigger(name = "signalMessage",
                                           queueName = "signals",
                                           connection = "SignalsQueueConnectionString")
                            final String signalMessage,
                            @TableOutput(name="signals", 
                                        tableName="signals", 
                                        connection="SignalsStorageConnectionString") 
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

        final String partitionKey = queueSignal.getTicker();
        final String rowKey = generateRowKey();
        
        queueSignal.setPartitionKey(partitionKey);
        queueSignal.setRowKey(rowKey);

        if (Config.useStubbedStorage()) {
            logger.warning("using stubbed storage - will not store the new signal");
        } else {
            outputSignal.setValue(queueSignal);
        }

        logger.info("new signal successfully stored");
    }

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
            for (ConstraintViolation<Signal> validationFailure : results) {
                logger.warning(validationFailure.getMessage());
            }
            return false;    
        }
        return true;
    }
}
