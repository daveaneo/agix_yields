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


class TokenPortfolio:
    def __init__(self, token_data_list: list):
        self.tokens = []
        # self.tokens = [TokenYield(token_data) for token_data in token_data_list]
        # self.load_ABIs()  # Load ABIs once for all tokens
        self.load_tokens_async(token_data_list)
        self.sum_all_tokens()
        self.dust_threshold = 0.0001

    def load_tokens_async(self, token_data_list: list):
        # Asynchronously create TokenYield instances
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(TokenYield, token_data) for token_data in token_data_list]
            for future in concurrent.futures.as_completed(futures):
                try:
                    token_yield_instance = future.result()
                    self.tokens.append(token_yield_instance)
                except Exception as exc:
                    print(f'Error creating TokenYield instance error: {exc}')

    def print_all_tokens(self):
        for token_yield in self.tokens:
            token_yield.print_data()

    def print_holdings(self):
        print(f'\nAll tokens in portfolio:')
        for k, v in self.all_tokens.items():
            if v > self.dust_threshold:
                print(f'{k}: {v:.2f}')

    def sum_all_tokens(self):
        # Logic to sum all tokens
        all_tokens = dict()
        for token in self.tokens:
            my_sum = token.get_all_assets()
            for k,v in my_sum.items():
                all_tokens[k] = all_tokens.get(k, 0) + v

        self.all_tokens = all_tokens

    def get_net_value(self):
        def get_val_in_terms_of_pair(liquidity_pool_address, token_yield):
            x_addr = token_yield.token_info.get('tokenAddress')

            liquidity_pool_address = token_yield.checksum_address(liquidity_pool_address)
            liquidity_pool_contract = token_yield.web3.eth.contract(address=liquidity_pool_address, abi=token_yield.PAIR_ABI)

            reserves = liquidity_pool_contract.functions.getReserves().call()
            token_zero = liquidity_pool_contract.functions.token0().call()
            token_one = liquidity_pool_contract.functions.token1().call()

            decimals_zero = token_yield.web3.eth.contract(address=token_zero, abi=token_yield.ERC20_ABI).functions.decimals().call()
            decimals_one = token_yield.web3.eth.contract(address=token_one, abi=token_yield.ERC20_ABI).functions.decimals().call()

            rate = reserves[0] * (10 ** decimals_one) / (10 ** decimals_zero) / reserves[1]

            if token_zero == x_addr:
                return 1/rate
            else:
                return rate


        # todo -- price in BNB is wrong.?????
        def get_token_price_in_usdt(symbol: str):
            if symbol == "USDT":
                return 1

            token_yield = next(x for x in self.tokens if x.symbol == symbol)
            info = token_yield.token_info
            lp = info.get('liquidityPool')

            pool_dictionary = dict({x.get('pairedTokenSymbol'): x.get('liquidityPoolAddress') for x in lp if x.get('pairedTokenSymbol') in ["USDT", "ETH", 'BNB']})

            if symbol in ["RJV", "SOPH"]:
                print(f'{symbol} pool dictionary:')

                # print(f'\nlp:')
                # for k,v in lp.items():
                #     print(f'{k} -> {v}')

                # print(f'\n\npool dictionary:')
                print(pool_dictionary)

                # for k,v in pool_dictionary.items():
                #     print(f'{k} -> {v}')

            if 'USDT' in pool_dictionary:
                return get_val_in_terms_of_pair(pool_dictionary['USDT'], token_yield)
            elif 'ETH' in pool_dictionary:
                eth_equiv = get_val_in_terms_of_pair(pool_dictionary['ETH'], token_yield)
                eth_in_usdt = get_token_price_in_usdt('ETH')
                print(f'\nsymbol: {symbol} ----      eth_equiv: {eth_equiv}, eth_in_usdt: {eth_in_usdt} ==> price: {eth_equiv*eth_in_usdt}')

                return eth_equiv * eth_in_usdt
            elif 'BNB' in pool_dictionary:
                bnb_equiv = get_val_in_terms_of_pair(pool_dictionary['BNB'], token_yield)
                bnb_in_usdt = get_token_price_in_usdt('BNB')
                print(f'\nsymbol: {symbol} ----     bnb_equiv: {bnb_equiv}, bnb_in_usdt: {bnb_in_usdt} ==> price: {bnb_equiv*bnb_in_usdt}')
                return bnb_equiv * bnb_in_usdt
            else:
                print(f'pool: {pool_dictionary}')
                raise Exception(f"Error in get_token_price_in_usdt for symbol {symbol}. Lacking token pair contract.")


        eth_price = get_token_price_in_usdt('ETH')
        bnb_price = get_token_price_in_usdt('BNB')

        print(f'eth: {eth_price}; bnb: {bnb_price}')

        total = 0
        for symbol, amount in self.all_tokens.items():
            usdt_equivalent = get_token_price_in_usdt(symbol) * amount
            print(f'{amount} {symbol} equals ${usdt_equivalent}')
            total += usdt_equivalent
        return total



class TokenYield:
    def __init__(self, token_info: Dict[str, Any]):
        """
        Initializes the TokenYield class with token information.

        Args:
        token_info (Dict[str, Any]): A dictionary containing token and blockchain information.
        """
        self.pair_decimals = {
            "USDT": 6,
            "ETH": 18,
            "BNB": 18,
            "USDC": 6,
        }

        self.token_info = token_info
        self.load_web3()
        self.decompress_token_info()
        self.load_ABIs() # could be done in parent class
        self.fetch_token_data()
        self.calculate_totals()

    def fetch_token_data(self) -> Dict[str, Any]:
        """
        Fetches and calculates token data based on the provided token information.

        Returns:
        Dict[str, Any]: A dictionary with fetched and calculated token data.
        """

        if not self.web3 and \
                (
                self.bonded_staking_address or
                self.unbonded_staking_address or
                len(self.liquidity_pool_info_list)
        ):
            raise Exception("Missing web3 or other details")

        self.get_wallet_balance()
        self.get_yield()
        self.get_bonded()
        self.get_unbonded()

        # Fetching token data
        # token_contract = self.web3.eth.contract(address=self.token_address, abi=self.PAIR_ABI)


    def decompress_token_info(self) -> None:
        try:
            bonded_staking_address = self.token_info.get("bondedStaking", {}).get("contractAddress", None)
            unbonded_staking_address = self.token_info.get("unbondedStaking", {}).get("contractAddress", None)

            self.name = self.token_info.get("name")
            self.symbol = self.token_info.get("symbol")
            self.decimals = self.token_info.get("decimals")
            self.blockchain = self.token_info.get('blockchain')
            self.token_address = self.checksum_address(self.token_info.get("tokenAddress"))
            self.bonded_staking_address = self.checksum_address(bonded_staking_address)
            self.unbonded_staking_address = self.checksum_address(unbonded_staking_address)
            self.liquidity_pool_info_list = self.token_info.get("liquidityPool", [{}])
            self.in_wallet = self.token_info.get("inWallet")
        except Exception as e:
            raise Exception(f'Error. Failed in decomppress_token_info: {e}')

    def load_web3(self) -> None:
        blockchain = self.token_info.get("blockchain")
        self.web3 = None
        if blockchain == "Ethereum":
            rpc_url = os.getenv('ETH_RPC')
        elif blockchain == "Binance":
            rpc_url = os.getenv('BNB_RPC')
        else:
            raise Exception("Unable to load web3")

        # Setup Web3 connection
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))

    def load_ABIs(self) -> None:
        try:
            # Load ABI files (assuming these are stored in a directory named 'ABI')
            with open('ABI/pair.json', 'r') as file:
                self.PAIR_ABI = json.load(file)
            with open('ABI/yieldVault.json', 'r') as file:
                self.YIELD_VAULT_ABI = json.load(file)
            with open('ABI/ERC20.json', 'r') as file:
                self.ERC20_ABI = json.load(file)
            with open('ABI/unbondedStaking.json', 'r') as file:
                self.UNBONDED_STAKING_ABI = json.load(file)
            with open('ABI/singularityTokenStake.json', 'r') as file:
                self.SINGULARITY_TOKEN_STAKE = json.load(file)
            # with open('ABI/pairBNB.json', 'r') as file:
            #     self.PAIR_BNB_ABI = json.load(file)

        except Exception as e:
            raise Exception(f'Error in load_ABIs: {e}')

    def print_data(self) -> None:
        """
        Prints the token data in a formatted manner.
        """
        print(f'\n... printing {self.symbol} data ...')
        # print(json.dumps(self.token_info, indent=4))
        for k,v in self.token_info.get('totalAssetsOwned', {}).items():
            print(f'{k}: {v}')

    def get_wallet_balance(self) -> None:
        """
        Fetches and returns bonded data.
        """
        try:
            token_contract = self.web3.eth.contract(address=self.token_address, abi=self.ERC20_ABI)
            bal = token_contract.functions.balanceOf(WALLET_ADDRESS).call() / 10**self.decimals
            self.token_info['inWallet'] = bal
        except Exception as e:
            raise Exception(f'Error in get_wallet_balance: {e}')

    def get_bonded(self) -> None:
        """
        Fetches and returns bonded data.
        """
        # Implement logic to fetch bonded data
        try:
            if not self.bonded_staking_address:
                return
            elif self.symbol == "AGIX":
                sing_stake = self.web3.eth.contract(address=self.bonded_staking_address, abi=self.SINGULARITY_TOKEN_STAKE)
                staked = sing_stake.functions.balances(WALLET_ADDRESS).call() / 10**self.decimals
                pending_rewards = 0 # todo figure out how to get rewards
            else:
                staked = 0
                pending_rewards = 0

            self.token_info['bondedStaking']['staked'] = staked
            self.token_info['bondedStaking']['pendingRewards'] = pending_rewards
        except Exception as e:
            raise Exception(f'Error in get_bonded: {e}')

    def get_unbonded(self) -> None:
        """
        Fetches and returns unbonded data.
        """
        if not self.unbonded_staking_address:
            return
        try:

            # todo -- we can't hardcode the userinfo as it varies for each one.

            # Implement logic to fetch unbonded data
            unbonded_contract = self.web3.eth.contract(address=self.unbonded_staking_address, abi=self.UNBONDED_STAKING_ABI)
            user_info_number = self.token_info['unbondedStaking']['userInfoNumber']
            amount, user_debt = unbonded_contract.functions.userInfo(user_info_number, WALLET_ADDRESS).call()
            self.token_info['unbondedStaking']['staked'] = amount / 10 ** self.decimals
            # todo -- understand the logic for getting the rewards

            # print(f"{self.symbol}, in unbonded staking on {self.blockchain}, has tokens: {self.token_info['unbondedStaking']['staked']}")
        except Exception as e:
            raise Exception(f'Error in get_unbonded: {e}')

    def get_dollar_value(self) -> None:
        pass


    def get_yield(self) -> None:
        """
        Fetches and returns yield data.
        """
        if self.symbol in self.pair_decimals.keys():
            return

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
            # paired_decimals = 18 if paired_token_symbol == "ETH" else 6
            paired_decimals = self.pair_decimals[paired_token_symbol] # error if does not exist

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

        return my_token_data

    def get_all_assets(self) -> Dict:
        """
        Calls all data-fetching methods and aggregates the results.
        """
        return self.token_info.get('totalAssetsOwned')

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
    @staticmethod
    def checksum_address(address: str) -> str:
        """
        Converts an Ethereum address to its checksummed version.

        Args:
        address (str): The Ethereum address to checksum.

        Returns:
        str: The checksummed Ethereum address.
        """
        return address if not address else Web3.to_checksum_address(address)
        # return Web3.to_checksum_address(address)
        # return self.web3.utils.toChecksumAddress(address)


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

    portfolio = TokenPortfolio(token_data)
    # portfolio.print_all_tokens()
    portfolio.print_holdings()
    net_value = portfolio.get_net_value()
    print(f'net value: {net_value}')


def print_group_data(results: Dict):
    """
    Prints grouped data and uses print_individual to print each token's data.
    """
    print(f'printing group data...  -- please impliment holder class') # todo
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
