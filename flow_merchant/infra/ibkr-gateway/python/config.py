import os

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

def __get_required_env(env_var_name: str) -> str:
    env_var_value = os.getenv(env_var_name)
    if env_var_value is None:
        raise ValueError(f"Environment variable {env_var_name} is not set.")
    return env_var_value

def ibkr_api_addr():
    return __get_required_env(ENV_IBKR_API_ADDR())

def ibkr_api_port():
    return int(__get_required_env(ENV_IBKR_API_PORT()))

def ibkr_client_id():
    return int(__get_required_env(ENV_IBKR_CLIENT_ID()))

def server_port():
    return int(__get_required_env(ENV_SERVER_PORT()))

def gateway_password():
    return __get_required_env(ENV_GATEWAY_PASSWORD())