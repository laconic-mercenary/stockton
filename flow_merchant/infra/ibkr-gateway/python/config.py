import os
import time

def ENV_IBKR_API_ADDR() -> str:
    return "IBKR_API_ADDR"

def ENV_IBKR_API_PORT() -> str:
    return "IBKR_API_PORT"

def ENV_IBKR_CLIENT_ID() -> str:
    return "IBKR_CLIENT_ID"

def ENV_SERVER_PORT() -> str:
    return "SERVER_PORT"

def ENV_GATEWAY_PASSWORD() -> str:
    return "GATEWAY_PASSWORD"

def ENV_IBKR_API_ACCOUNT() -> str:
    return "IBKR_API_ACCOUNT"

def __get_required_env(env_var_name: str, default=None) -> str:
    env_var_value = os.getenv(env_var_name)
    if env_var_value is None:
        if default is not None:
            return default
        else:
            raise ValueError(f"Environment variable {env_var_name} is not set.")
    return env_var_value

def ibkr_api_addr() -> str:
    return __get_required_env(ENV_IBKR_API_ADDR(), default="127.0.0.1")

def ibkr_api_port() -> int:
    return int(__get_required_env(ENV_IBKR_API_PORT(), default="7497"))

def ibkr_api_account() -> str:
    return __get_required_env(ENV_IBKR_API_ACCOUNT())

def ibkr_client_id(rand=False) -> int:
    if rand:
        return int(time.time())
    return int(__get_required_env(ENV_IBKR_CLIENT_ID()))

def server_port() -> int:
    return int(__get_required_env(ENV_SERVER_PORT(), default="8080"))

def gateway_password() -> str:
    return __get_required_env(ENV_GATEWAY_PASSWORD())

def order_currency() -> str:
    return "USD"

def tls_cert_file() -> str:
    return "/tmp/domain.cert.pem"

def tls_key_file() -> str:
    return "/tmp/private.key.pem"