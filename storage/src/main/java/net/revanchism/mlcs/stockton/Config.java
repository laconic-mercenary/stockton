package net.revanchism.mlcs.stockton;

import java.nio.charset.Charset;
import java.util.Base64;
import java.util.concurrent.TimeUnit;

import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.Validate;

public final class Config {

    private static final String ENV_SIGNAL_EXPIRY = "SIGNAL_EXPIRY";

    private static final String ENV_USE_STUBBED_STORAGE = "USE_STUBBED_STORAGE";

    static final String ENV_SIGNALS_TABLE_CONNSTR = "SignalsStorageConnectionString";

    private static final String ENV_AUTH_HEADER_NAME = "AUTH_HEADER_NAME";

    private static final String ENV_AUTH_HEADER_KEY = "AUTH_HEADER_KEY";

    private static final String ENV_ALLOW_ORIGIN = "ALLOWED_ORIGIN";

    private static final int MIN_AUTH_KEY_LENGTH = 10;

    public static String getAuthHeaderName() {
        return getEnv(ENV_AUTH_HEADER_NAME);
    }

    public static String getAuthHeaderKey() {
        final String authKey = getEnv(ENV_AUTH_HEADER_KEY);
        Validate.notEmpty(authKey, "authKey is empty");
        Validate.isTrue(authKey.length() >= MIN_AUTH_KEY_LENGTH, "authKey must be equal to or longer than " + MIN_AUTH_KEY_LENGTH + " chars");
        final byte[] authKeyDecoded = Base64.getDecoder().decode(authKey);
        return new String(authKeyDecoded, Charset.forName("UTF-8")).trim();
    }

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

    public static String getAllowedOrigin() {
        return getEnv(ENV_ALLOW_ORIGIN);
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
