package net.revanchism.mlcs.stockton;

import java.util.Optional;
import java.util.logging.Logger;

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

public class Function {

    //
    // GET

    @FunctionName("stockton-get-signals")
    public Signal[] get(
        @HttpTrigger(name = "getSignals", 
                    methods = {HttpMethod.GET}, 
                    authLevel = AuthorizationLevel.ANONYMOUS, 
                    route="signals/{ticker}") 
        final HttpRequestMessage<Optional<Signal>> request,
        @BindingName("ticker") 
        final String ticker,
        @TableInput(name="signals", 
                    filter="Ticker eq '{ticker}'", 
                    take = "9999", 
                    tableName="%SIGNALS%", 
                    connection="SignalsStorageConnectionString") 
        final Signal[] signals,
        final ExecutionContext context
    ) 
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

    //
    // POSt

    @FunctionName("stockton-store-signal")
    public HttpResponseMessage store (
        @HttpTrigger(name = "storeSignal",
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
                     tableName="%SIGNALS%", 
                     connection="SignalsStorageConnectionString") 
        final OutputBinding<Signal> outputSignal,
        final ExecutionContext context
    )
    {
        final Logger logger = context.getLogger();

        logger.fine("new request received");

        if (request.getBody().isEmpty()) {
            logger.warning("missing body in request");
            return request.createResponseBuilder(HttpStatus.BAD_REQUEST).build();
        }
        
        logger.fine("storing new signal...");
        final Signal requestSignal = request.getBody().get();
        final Signal newSignal = new Signal();
        newSignal.setPartitionKey(partitionKey);
        newSignal.setRowKey(rowKey);
        newSignal.setAction(requestSignal.getAction());
        newSignal.setClose(requestSignal.getClose());
        newSignal.setContracts(requestSignal.getContracts());
        newSignal.setPartitionKey(requestSignal.getPartitionKey());
        newSignal.setTimestamp(requestSignal.getTimestamp());

        outputSignal.setValue(newSignal);

        logger.info("new signal stored: " + newSignal.toString());

        return request.createResponseBuilder(HttpStatus.OK).build();
    }
}
