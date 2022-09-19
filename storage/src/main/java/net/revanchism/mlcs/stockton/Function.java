package net.revanchism.mlcs.stockton;

import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Logger;

import org.apache.commons.lang3.StringUtils;

import com.azure.data.tables.TableClient;
import com.azure.data.tables.TableClientBuilder;
import com.azure.data.tables.models.ListEntitiesOptions;
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
import com.microsoft.azure.functions.annotation.TableInput;
import com.microsoft.azure.functions.annotation.TableOutput;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;

public class Function {

    @FunctionName("stockton-delete-old-signals")
    public HttpResponseMessage deleteOldSignals(@HttpTrigger(name = "deleteOldSignals",
                                                             methods = {HttpMethod.DELETE}, 
                                                             authLevel = AuthorizationLevel.ANONYMOUS, 
                                                             route="signals") 
                                                final HttpRequestMessage<Optional<Signal>> request,
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
        return request.createResponseBuilder(HttpStatus.OK).body(String.format("deleted %d signals", counter.get())).build();
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
    public HttpResponseMessage storeSignal (@HttpTrigger(name = "storeSignal",
                                                        methods = {HttpMethod.POST},
                                                        authLevel = AuthorizationLevel.ANONYMOUS,
                                                        route="signals/{partitionKey}/{rowKey}") 
                                            final HttpRequestMessage<Optional<Signal>> request,
                                            @BindingName("partitionKey") 
                                            final String partitionKey,
                                            @BindingName("rowKey") 
                                            final String rowKey,
                                            @TableOutput(name="signals", 
                                                        partitionKey="{partitionKey}", 
                                                        rowKey = "{rowKey}", 
                                                        tableName="signals", 
                                                        connection="SignalsStorageConnectionString") 
                                            final OutputBinding<Signal> outputSignal,
                                            final ExecutionContext context)
    {
        final Logger logger = context.getLogger();

        logger.fine("new request received");

        if (request.getBody().isEmpty()) {
            logger.warning("missing body in request");
            return request.createResponseBuilder(HttpStatus.BAD_REQUEST).body("invalid request").build();
        }

        final Signal requestSignal = request.getBody().get();
        if (!isValidSignal(requestSignal, partitionKey, rowKey, logger)) {
            logger.warning("validation failures in request");
            return request.createResponseBuilder(HttpStatus.BAD_REQUEST).body("invalid request").build();
        }
        
        logger.fine("storing new signal...");

        final Signal newSignal = new Signal();
        newSignal.setPartitionKey(partitionKey);
        newSignal.setRowKey(rowKey);
        newSignal.setAction(requestSignal.getAction());
        newSignal.setClose(requestSignal.getClose());
        newSignal.setContracts(requestSignal.getContracts());
        newSignal.setTicker(requestSignal.getTicker());
        newSignal.setNotes(requestSignal.getNotes());

        if (Config.useStubbedStorage()) {
            logger.warning("using stubbed storage - will not store the new signal");
        } else {
            outputSignal.setValue(newSignal);
        }

        logger.info("new signal stored: " + newSignal.toString());

        return request.createResponseBuilder(HttpStatus.OK).body(newSignal).build();
    }

    private static boolean isValidSignal(final Signal signal, 
                                         final String partitionKey,
                                         final String rowKey,
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
        if (partitionKey.length() > Byte.MAX_VALUE) {
            logger.warning("partitionKey is too long");
            return false;
        }
        if (rowKey.length() > Byte.MAX_VALUE) {
            logger.warning("rowKey is too long");
            return false;
        }
        if (partitionKey.isEmpty() || !StringUtils.isAlphanumeric(partitionKey)) {
            logger.warning("invalid partitionKey: " + partitionKey);
            return false;
        }
        if (rowKey.isEmpty() || !StringUtils.isAlphanumeric(rowKey)) {
            logger.warning("invalid rowKey: " + rowKey);
            return false;
        }
        return true;
    }
}
