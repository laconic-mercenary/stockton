package net.revanchism.mlcs.stockton;

import java.io.Serializable;

import org.apache.commons.lang3.builder.CompareToBuilder;
import org.apache.commons.lang3.builder.EqualsBuilder;
import org.apache.commons.lang3.builder.HashCodeBuilder;

import com.fasterxml.jackson.annotation.JsonGetter;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public final class Signal implements Serializable, Comparable<Signal> {

    public Signal(final Signal signal) {
        this(signal.getTicker(), 
            signal.getAction(), 
            signal.getClose(), 
            signal.getContracts(), 
            signal.getNotes(), 
            signal.getPartitionKey(), 
            signal.getRowKey());
    }

    public Signal(@NotEmpty(message = "ticker must not be empty") @Size(min = 1, max = 50) final String ticker,
            @NotEmpty(message = "action must not be empty") @Pattern(regexp = "(sell|buy)", message = "action must be either 'buy' or 'sell'") final String action,
            @DecimalMin("0.0") @DecimalMax("9999999.99") final double close, @Min(1) @Max(99999) final int contracts,
            @Size(min = 0, max = 500) final String notes, final String partitionKey, final String rowKey) {
        this.ticker = ticker;
        this.action = action;
        this.close = close;
        this.contracts = contracts;
        this.notes = notes;
        this.PartitionKey = partitionKey;
        this.RowKey = rowKey;
    }

    public Signal() {
    }

    @NotEmpty(message = "ticker must not be empty")
    @Size(min = 1, max = 50)
    private String ticker;

    @NotEmpty(message = "action must not be empty")
    @Pattern(regexp = "(sell|buy)", message = "action must be either 'buy' or 'sell'")
    private String action;

    @DecimalMin(value = "0.0")
    @DecimalMax(value = "9999999.99")
    private double close;

    @Min(value = 1)
    @Max(value = 99999)
    private int contracts;

    @Size(min = 0, max = 500)
    private String notes;

    private String PartitionKey;

    private String RowKey;

    public void setPartitionKey(final String partitionKey) {
        this.PartitionKey = partitionKey;
    }

    public String getPartitionKey() {
        return PartitionKey;
    }

    public void setRowKey(final String rowKey) {
        this.RowKey = rowKey;
    }

    public String getRowKey() {
        return RowKey;
    }

    public void setNotes(final String notes) {
        this.notes = notes;
    }

    @JsonGetter("notes")
    public String getNotes() {
        return notes;
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

    @JsonGetter("contracts")
    public int getContracts() {
        return contracts;
    }

    public void setContracts(final int contracts) {
        this.contracts = contracts;
    }

    @Override
    public String toString() {
        try { return new ObjectMapper().writeValueAsString(this); }
        catch (final JsonProcessingException ex) { throw new RuntimeException(ex); }
    }

    @Override
    public boolean equals(final Object obj) {
        if (obj instanceof Signal) {
            final Signal source = (Signal)obj;
            return new EqualsBuilder().append(getClose(), source.getClose())
                                      .append(getContracts(), source.getContracts())
                                      .append(getAction(), source.getAction())
                                      .append(getTicker(), source.getTicker())
                                      .append(getNotes(), source.getNotes())
                                      .append(getPartitionKey(), source.getPartitionKey())
                                      .append(getRowKey(), source.getRowKey())
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
                                    .append(getNotes())
                                    .append(getPartitionKey())
                                    .append(getRowKey())
                                    .toHashCode();
    }

    @Override
    public int compareTo(final Signal o) {
        return new CompareToBuilder().append(getRowKey(), o.getRowKey())
                                     .toComparison();
    }
}
