package net.revanchism.mlcs.stockton;

import java.io.Serializable;

import javax.validation.constraints.DecimalMax;
import javax.validation.constraints.DecimalMin;
import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.NotEmpty;
import javax.validation.constraints.Pattern;
import javax.validation.constraints.Size;

import org.apache.commons.lang3.builder.CompareToBuilder;
import org.apache.commons.lang3.builder.EqualsBuilder;
import org.apache.commons.lang3.builder.HashCodeBuilder;

import com.fasterxml.jackson.annotation.JsonGetter;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

public final class Signal implements Serializable, Comparable<Signal> {
    
    @NotEmpty
    @Size(min = 1, max = 50)
    private String ticker;

    @NotEmpty
    @Pattern(regexp = "(sell|buy)", message = "action must be either 'buy' or 'sell'")
    private String action;

    @DecimalMin(value = "0.0")
    @DecimalMax(value = "9999999.99")
    private double close;

    @Min(value = 1)
    @Max(value = 99999)
    private int contracts;

    private String PartitionKey;

    private String RowKey;

    private long timestamp;

    public void setPartitionKey(String partitionKey) {
        PartitionKey = partitionKey;
    }

    public String getPartitionKey() {
        return PartitionKey;
    }

    public void setRowKey(String rowKey) {
        RowKey = rowKey;
    }

    public String getRowKey() {
        return RowKey;
    }

    @JsonGetter("ticker")
    public String getTicker() {
        return ticker;
    }

    public void setTicker(final String ticker) {
        this.ticker = ticker;
    }

    @JsonGetter("action")
    public String getAction() {
        return action;
    }

    public void setAction(final String action) {
        this.action = action;
    }

    @JsonGetter("close")
    public double getClose() {
        return close;
    }

    public void setClose(final double close) {
        this.close = close;
    }

    @JsonGetter("contracts_count")
    public int getContracts() {
        return contracts;
    }

    public void setContracts(final int contracts) {
        this.contracts = contracts;
    }

    public void setTimestamp(long timestamp) {
        this.timestamp = timestamp;
    }

    @JsonGetter("timestamp")
    public long getTimestamp() {
        return timestamp;
    }

    @Override
    public String toString() {
        try { return new ObjectMapper().writeValueAsString(this); }
        catch (JsonProcessingException ex) { throw new RuntimeException(ex); }
    }

    @Override
    public boolean equals(Object obj) {
        if (obj instanceof Signal) {
            final Signal source = (Signal)obj;
            return new EqualsBuilder().append(getClose(), source.getClose())
                                      .append(getContracts(), source.getContracts())
                                      .append(getAction(), source.getAction())
                                      .append(getTicker(), source.getTicker())
                                      .append(getTimestamp(), source.getTimestamp())
                                      .isEquals();
        }
        return false;
    }

    @Override
    public int hashCode() {
        return new HashCodeBuilder().append(getContracts())
                                    .append(getClose())
                                    .append(getAction())
                                    .append(getTicker())
                                    .append(getTimestamp())
                                    .toHashCode();
    }

    @Override
    public int compareTo(Signal o) {
        return new CompareToBuilder().append(getTimestamp(), o.getTimestamp())
                                     .toComparison();
    }
}
