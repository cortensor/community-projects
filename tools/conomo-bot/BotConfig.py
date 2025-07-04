from environs import env


class BotConfig:
    def __init__(self, env_file=".env"):
        # Load the .env file
        env.read_env(env_file) 

    @property
    def AUTHORIZED_ADMIN_IDS(self) -> list[int]: 
        return env.list("AUTHORIZED_ADMIN_IDS", subcast=int)

    @property
    def TELEGRAM_BOT_TOKEN(self) -> str:
        return env.str("TELEGRAM_BOT_TOKEN")
    
    @property
    def ETH_API_KEY(self) -> str:
        return env.str("ETH_API_KEY", None)   
        
    @property
    def ARBISCAN_TX_URL_PREFIX(self) -> str:
        return env.str("ARBISCAN_TX_URL_PREFIX", "https://sepolia.arbiscan.io/tx/")

    @property
    def ARBISCAN_ADDRESS_URL_PREFIX(self) -> str:
        return env.str("ARBISCAN_ADDRESS_URL_PREFIX", "https://sepolia.arbiscan.io/address/")
    
    @property
    def COR_DASHBOARD_URL_PREFIX(self) -> str:
        return env.str("COR_DASHBOARD_URL_PREFIX", "https://dashboard-devnet5.cortensor.network/stats/node/")
    
    @property
    def COR_LEADERBOARD_URL(self) -> str:
        return env.str("COR_LEADERBOARD_URL", "https://lb-be-5.cortensor.network/leaderboard-by-address")
    
    @property
    def COR_SESSION_URL(self) -> str:
        return env.str("COR_SESSION_URL", "https://dashboard-devnet5.cortensor.network/cognitive")

    @property
    def RPC_ARB_SEPOLIA(self) -> str:
        return env.str("RPC_ARB_SEPOLIA", None)

    @property
    def CONTRACT_COR_COGNETIVE(self) -> str:
        return env.str("CONTRACT_COR_COGNETIVE", "0x073C1f568d372F7E79A599Dcc624aDf718dd10f3")

    @property
    def BALANCE_WARNING_THRESHOLD(self) -> float:
        return env.float("BALANCE_WARNING_THRESHOLD", 0.05)
    
    @property
    def NODE_STALL_THRESHOLD(self) -> int:
        return env.int("NODE_STALL_THRESHOLD", 25)
    
    @property
    def MAIN_SLEEP_SEC(self) -> int:  
        return env.int("MAIN_SLEEP_MIN", 5) * 60 + 5
    
    @property
    def ALIVE_THRESHOLD_SEC(self) -> int:  
        return env.int("ALIVE_THRESHOLD_MIN", 6) * 60
    
    @property
    def BOT_DB_FILE(self) -> str:  
        return env.str("BOT_DB_FILE", "bot.db")