from typing import Dict, Any
import os
from dotenv import load_dotenv
from web3 import Web3
import json
from web3.gas_strategies.rpc import rpc_gas_price_strategy
import concurrent.futures
from web3.gas_strategies.rpc import rpc_gas_price_strategy
from datetime import datetime

load_dotenv()
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')

# todo -- consider our JSON file and issues we may have when having multiple
# tokens and double counting them, like SDAO. Currently, this won't happen.


class TokenYield:
    def __init__(self, token_info: Dict[str, Any]):
        """
        Initializes the TokenYield class with token information.

        Args:
        token_info (Dict[str, Any]): A dictionary containing token and blockchain information.
        """
        self.token_info = token_info
        self.decompress_token_info()
        self.load_web3()
        if not self.web3:
            print(f'how do we handle this?')
        self.load_ABIs() # could be done in parent class
        self.fetch_token_data()
        self.calculate_totals()
        self.print_data()

    def fetch_token_data(self) -> Dict[str, Any]:
        """
        Fetches and calculates token data based on the provided token information.

        Returns:
        Dict[str, Any]: A dictionary with fetched and calculated token data.
        """

        if not (
                self.web3 or
                self.bonded_staking_address or
                self.unbonded_staking_address or
                len(self.liquidity_pool_info_list)
        ):
            return {}

        self.get_wallet_balance()
        self.get_yield()
        self.get_bonded()
        self.get_unbonded()

        # Fetching token data
        # token_contract = self.web3.eth.contract(address=self.token_address, abi=self.PAIR_ABI)


    def decompress_token_info(self) -> None:
        self.name = self.token_info.get("name")
        self.symbol = self.token_info.get("symbol")
        self.decimals = self.token_info.get("decimals")
        self.blockchain = self.token_info.get('blockchain')
        self.token_address = self.checksum_address(self.token_info.get("tokenAddress"))
        self.bonded_staking_address = self.checksum_address(self.token_info.get("bondedStakingAddress"))
        self.unbonded_staking_address = self.checksum_address(self.token_info.get("unbondedStakingAddress"))
        self.liquidity_pool_info_list = self.token_info.get("liquidityPool", [{}])
        self.in_wallet = self.token_info.get("inWallet")

    def load_web3(self) -> None:
        blockchain = self.token_info.get("blockchain")
        web3 = None
        if blockchain == "Ethereum":
            rpc_url = os.getenv('ETH_RPC')
        elif blockchain == "Binance":
            rpc_url = os.getenv('BNB_RPC')
        else:
            print(f'unable to find rpc for blockchain: {blockchain}')
            return

        # Setup Web3 connection
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))

        if not self.web3:
            print(f'unsupported blockchain')



    def load_ABIs(self) -> None:
        # Load ABI files (assuming these are stored in a directory named 'ABI')
        with open('ABI/pair.json', 'r') as file:
            self.PAIR_ABI = json.load(file)
        with open('ABI/yieldVault.json', 'r') as file:
            self.YIELD_VAULT_ABI = json.load(file)
        with open('ABI/ERC20.json', 'r') as file:
            self.ERC20_ABI = json.load(file)

    def print_data(self) -> None:
        """
        Prints the token data in a formatted manner.
        """
        print(f'... {self.symbol} data ...')
        # print(json.dumps(self.token_info, indent=4))

    def get_wallet_balance(self) -> None:
        """
        Fetches and returns bonded data.
        """
        token_contract = self.web3.eth.contract(address=self.token_address, abi=self.ERC20_ABI)
        bal = token_contract.functions.balanceOf(WALLET_ADDRESS).call() / 10**token_contract.functions.decimals().call()

    def get_bonded(self) -> None:
        """
        Fetches and returns bonded data.
        """
        # Implement logic to fetch bonded data
        return {}

    def get_unbonded(self) -> None:
        """
        Fetches and returns unbonded data.
        """
        # Implement logic to fetch unbonded data
        return {}

    def get_yield(self) -> None:
        """
        Fetches and returns yield data.
        """
        # Initialize values to zero before iterating over list
        total_token = 0
        total_paired_token = 0
        my_token_data = dict()

        for lp_dict in self.liquidity_pool_info_list:
            liquidity_pool_address = self.checksum_address(lp_dict.get("liquidityPoolAddress"))
            yield_contract_address = self.checksum_address(lp_dict.get("liquidityTokenStakingAddress"))
            special_number = int(lp_dict.get("liquidityTokenStakingNumber")) if lp_dict.get("liquidityTokenStakingNumber") else None
            paired_token_symbol = lp_dict.get("pairedTokenSymbol")

            if not liquidity_pool_address:
                continue

            liquidity_pool_contract = self.web3.eth.contract(address=liquidity_pool_address, abi=self.PAIR_ABI)

            # todo this can be more generic
            paired_decimals = 18 if paired_token_symbol == "ETH" else 6

            # Uniswap Pair
            reserves = liquidity_pool_contract.functions.getReserves().call()
            token_zero = liquidity_pool_contract.functions.token0().call()

            # get liquidity
            my_lp = liquidity_pool_contract.functions.balanceOf(WALLET_ADDRESS).call()
            total_lp = liquidity_pool_contract.functions.totalSupply().call()

            # if ther eis a yield vault, get amount of lp tokens staked there
            if yield_contract_address:
                yield_contract = self.web3.eth.contract(address=yield_contract_address, abi=self.YIELD_VAULT_ABI)
                yield_lp, _ = yield_contract.functions.userInfo(special_number, WALLET_ADDRESS).call()
                # print(yield_lp)
                # print(total_lp)
                my_lp += yield_lp

            if token_zero == self.token_address:
                total_token += reserves[0] * my_lp / total_lp / (10 ** self.decimals)
                total_paired_token += reserves[1] * my_lp / total_lp / (10 ** paired_decimals)
                # token_price = (reserves[1] / 10 ** paired_decimals) / (reserves[0] / 10 ** decimals)
            else:
                total_token += reserves[1] * my_lp / total_lp / (10 ** self.decimals)
                total_paired_token += reserves[0] * my_lp / total_lp / (10 ** paired_decimals)
                # token_price = (reserves[0] / 10 ** paired_decimals) / (reserves[1] / 10 ** decimals)
            my_token_data[self.symbol] = my_token_data.get(self.symbol, 0) + total_token
            my_token_data[paired_token_symbol] = my_token_data.get(paired_token_symbol, 0) + total_paired_token

            lp_dict['mainAssetAmountNow'] = total_token
            lp_dict['pairedAssetAmountNow'] = total_paired_token
            lp_dict['pendingRewardsFromYieldVault'] = 0 # todo

            print(f'fraction of pool: {my_lp / total_lp * 100:.2f}%')

        return my_token_data

    def get_all(self) -> None:
        """
        Calls all data-fetching methods and aggregates the results.
        """
        print(f'get_all called. We should remove this function in the future.')
        return {
            "bonded": self.get_bonded(),
            "unbonded": self.get_unbonded(),
            "yield": self.get_yield()
        }

    def export(self) -> None:
        """
        Exports the current data with a datetime stamp.
        """
        print(f'exporting...')
        return {
            "current_datetime": datetime.now().isoformat(),
            "data": self.data
        }

    def calculate_totals(self) -> None:
        """
        Fetches and returns bonded data.
        """
        # Implement logic to fetch bonded data
        bonded = self.token_info.get('bondedStaking').get('staked', 0) + self.token_info.get('bondedStaking').get('pendingRewards', 0)
        unbonded = self.token_info.get('unbondedStaking').get('staked') + self.token_info.get('unbondedStaking').get('pendingRewards', 0)
        totals = dict({self.symbol: self.token_info.get('inWallet', 0) + bonded + unbonded})

        for lp_dict in self.liquidity_pool_info_list:
            totals[self.symbol] += lp_dict.get("mainAssetAmountNow")
            paired_token_symbol = lp_dict.get("pairedTokenSymbol")
            paired_amount = lp_dict.get("pairedAssetAmountNow")
            totals[paired_token_symbol] = totals.get(paired_token_symbol,0) + paired_amount

        self.token_info['totalAssetsOwned'] = totals

    # @staticmethod
    # def checksum_address(address: str) -> str:
    def checksum_address(self, address: str) -> str:
        """
        Converts an Ethereum address to its checksummed version.

        Args:
        address (str): The Ethereum address to checksum.

        Returns:
        str: The checksummed Ethereum address.
        """
        return self.web3.utils.toChecksumAddress(address)


# # used for getting prices (in terms of each other)
# reserves = liquidity_pool_contract.functions.getReserves().call()
# token_zero = liquidity_pool_contract.functions.token0().call()


def load_token_data(json_file: str = 'tokenInfo.json') -> Dict:
    """
    Loads token data from a JSON file.
    """
    with open(json_file, 'r') as file:
        data = json.load(file)
    return data


def main():
    """
    Main function to load all tokens and create TokenYield instances in parallel.
    Then prints the data in series.
    """
    token_data = load_token_data()  # Load token data from JSON
    results = {}

    # Create TokenYield instances in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(TokenYield, token): token for token in token_data}
        for future in concurrent.futures.as_completed(futures):
            token = futures[future]
            try:
                token_yield_instance = future.result()
                # results[token['symbol']] = token_yield_instance.get_all()
            except Exception as exc:
                print(f'{token["symbol"]} generated an exception: {exc}')

    # Print the results in series
    # todo -- have container class print all
    # print_group_data(results)

def print_group_data(results: Dict):
    """
    Prints grouped data and uses print_individual to print each token's data.
    """
    print(f'printing group data... todo -- please impliment holder class')
    # for symbol, data in results.items():
    #     print_individual(data)

def print_individual(data: Dict):
    """
    Prints individual token data.
    """
    print(json.dumps(data, indent=4))

# Rest of the TokenYield class and other functions

if __name__ == '__main__':
    main()
