from web3 import Web3
import json
from datetime import datetime, timezone

from session_data import SessionData
import logging


logger = logging.getLogger("ContractReader")


class ContractReader:
    def __init__(
        self,
        rpc_arb: str = None,
        contract_cor_cognetive_address: str = None
    ):
        self.web_arb = Web3(Web3.HTTPProvider(rpc_arb))

        if not self.web_arb.is_connected():
            raise ConnectionError("Web3 arb is not connected to the RPC endpoint!")
        
        with open("abis/cor_cognetive.json") as f:
            abi = json.load(f)

        contract_address_checksum_address = Web3.to_checksum_address(contract_cor_cognetive_address)
        self.contract_cor_cognitive = self.web_arb.eth.contract(address=contract_address_checksum_address, abi=abi)


    def parse_timestamp(self, ts) -> datetime:
        return datetime.fromtimestamp(ts, timezone.utc).isoformat(sep=' ', timespec='seconds')


    def get_eth_balance(self, address):
        try:

            checksum_addr = self.web_arb.to_checksum_address(address)
            balance_wei = self.web_arb.eth.get_balance(checksum_addr)
            balance_eth = self.web_arb.from_wei(balance_wei, 'ether')
            # print(f"{checksum_addr} balance: {balance_eth} ETH")
            return float(balance_eth)
        except Exception:
            logger.exception(f"Failed to read balance for address '{address}'!")
            return 0


    def get_latest_cor_session_data(self):
        try:
            session_id = self.contract_cor_cognitive.functions.getLatestSessionId().call()
            print(session_id)

            session_data = self.contract_cor_cognitive.functions.get(session_id).call()

            return SessionData(session_id, session_data[1], session_data[10], session_data[11])
        except Exception:
            logger.exception("Failed to read latest session data from contract!")
            return None