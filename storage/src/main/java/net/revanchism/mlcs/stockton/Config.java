package net.revanchism.mlcs.stockton;

import java.util.concurrent.TimeUnit;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Validate;

public final class Config {

    private static final String ENV_SIGNAL_EXPIRY = "SIGNAL_EXPIRY";

    private static final String ENV_USE_STUBBED_STORAGE = "USE_STUBBED_STORAGE";

    private static final String ENV_SIGNALS_TABLE_CONNSTR = "SignalsStorageConnectionString";

    public static boolean useStubbedStorage() {
        final String useStubbedStorage = System.getenv(ENV_USE_STUBBED_STORAGE);
        if (StringUtils.isNotEmpty(useStubbedStorage)) {
            return Boolean.valueOf(useStubbedStorage);
        }
        return false;
    }
    
    public static long getSignalExpiryDays() {
        final String expiry = getEnv(ENV_SIGNAL_EXPIRY);
        final long days = Long.parseLong(expiry);
        return TimeUnit.DAYS.toMillis(days);
    }

    public static String getSignalsTableConnectionString() {
        return getEnv(ENV_SIGNALS_TABLE_CONNSTR);
    }

    private static String getEnv(final String env) {
        String result = System.getenv(env);
        if (StringUtils.isEmpty(result)) {
            result = System.getProperty(env);
        }
        Validate.notEmpty(result, "missing required enviornment var or property; " + env);
        return result;
    }
}
