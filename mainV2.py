from typing import Dict
import os
from dotenv import load_dotenv
from web3 import Web3
import json
from web3.gas_strategies.rpc import rpc_gas_price_strategy
import concurrent.futures
from web3.gas_strategies.rpc import rpc_gas_price_strategy

load_dotenv()
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')


def get_web3_given_chain_info(blockchain: str) -> Web3:
    if blockchain == "Ethereum":
        rpc_url = os.getenv('ETH_RPC')
        # chain_id = int(os.getenv('CHAIN_ID'))
    else:
        return None

    # Setup Web3 connection
    web3 = Web3(Web3.HTTPProvider(rpc_url))
    # web3.eth.set_chain_id(chain_id)

    # Set the gas price strategy
    web3.eth.set_gas_price_strategy(rpc_gas_price_strategy)

    return web3


def fetch_token_data(token_info: Dict) -> Dict:
    """
    Fetches token data based on the input dictionary containing token information.

    Args:
    token_info: Dictionary with token and blockchain information.

    Returns:
    A dictionary with fetched token data.
    """
    name = token_info.get("name")
    symbol = token_info.get("symbol")
    decimals = token_info.get("decimals")
    blockchain = token_info.get('blockchain')
    token_address = token_info.get("tokenAddress")
    bonded_staking_address = token_info.get("bondedStakingAddress")
    unbonded_staking_address = token_info.get("unbondedStakingAddress")

    liquidity_pool_info_liist = token_info.get("liquidityPool", [{}])

    if not (bonded_staking_address or unbonded_staking_address or len(liquidity_pool_info_liist)):
        return {}

    # Setup Web3 connection
    web3 = get_web3_given_chain_info(blockchain)
    if not web3:
        return {}

    # it may make more sense to load these once
    # Load ABI files (assuming these are stored in a directory named 'ABI')
    with open('ABI/pair.json', 'r') as file:
        PAIR_ABI = json.load(file)
    with open('ABI/yieldVault.json', 'r') as file:
        YIELD_VAULT_ABI = json.load(file)

    # Fetching token data
    token_contract = web3.eth.contract(address=token_address, abi=PAIR_ABI)

    # Set total tokens for each in lp
    total_token = 0
    total_paired_token = 0

    my_token_data = dict()

    for lp_dict in liquidity_pool_info_liist:
        (liquidity_pool_address, yield_contract_address, special_number, paired_token_symbol) = lp_dict.values()
        special_number = int(special_number)
        # print(f'\n########################################')
        # print(f'##########    {symbol}     ################')

        if not liquidity_pool_address:
            continue

        liquidity_pool_contract = web3.eth.contract(address=liquidity_pool_address, abi=PAIR_ABI)

        # used for getting prices (in terms of each other)
        reserves = liquidity_pool_contract.functions.getReserves().call()
        token_zero = liquidity_pool_contract.functions.token0().call()

        # todo this can be more generic
        paired_decimals = 18 if paired_token_symbol == "ETH" else 6

        # yield vault liquidity
        my_lp = 0

        # Uniswap Pair
        reserves = liquidity_pool_contract.functions.getReserves().call()
        token_zero = liquidity_pool_contract.functions.token0().call()

        my_lp += liquidity_pool_contract.functions.balanceOf(WALLET_ADDRESS).call()
        total_lp = liquidity_pool_contract.functions.totalSupply().call()

        if yield_contract_address:
            yield_contract = web3.eth.contract(address=yield_contract_address, abi=YIELD_VAULT_ABI)
            yield_lp, _ = yield_contract.functions.userInfo(special_number, WALLET_ADDRESS).call()
            print(yield_lp)
            print(total_lp)
            my_lp += yield_lp

        if token_zero == token_address:
            total_token += reserves[0]*my_lp/total_lp/(10**decimals)
            total_paired_token += reserves[1]*my_lp/total_lp/(10**paired_decimals)
            # token_price = (reserves[1] / 10 ** paired_decimals) / (reserves[0] / 10 ** decimals)
        else:
            total_token += reserves[1]*my_lp/total_lp/(10**decimals)
            total_paired_token += reserves[0]*my_lp/total_lp/(10**paired_decimals)
            # token_price = (reserves[0] / 10 ** paired_decimals) / (reserves[1] / 10 ** decimals)
        my_token_data[symbol] = my_token_data.get(symbol, 0) + total_token
        my_token_data[paired_token_symbol] = my_token_data.get(paired_token_symbol, 0) + total_paired_token

        print(f'fraction of pool: {my_lp/total_lp*100}&')

        # todo -- add in wallet balance -- if have not already
        # todo -- add in bonded, unbonded staking
        # todo -- return the data in an informative way using a dictionary.
        # consider what is being returned


    # token_info["data"] = token_data
    return my_token_data


def print_token_data(token_data: Dict):
    """
    Prints the token data in a formatted manner.
    """
    print(f'token data:')
    print(token_data)
    # Implement the printing logic here
    print(f"Token Data for {token_data['symbol']} on {token_data['blockchain']}:")
    print(json.dumps(token_data, indent=4))


def load_token_data(json_file: str = 'tokenInfo.json') -> Dict:
    """
    Loads token data from a JSON file.
    """
    with open(json_file, 'r') as file:
        data = json.load(file)
    return data


def main():
    """
    Main function to load all tokens and fetch their data in parallel.
    Then prints the data in series.
    """
    token_data = load_token_data()  # Load token data from JSON
    results = {}


    # Fetch data in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_token_data, token): token for token in token_data}
        for future in concurrent.futures.as_completed(futures):
            token = futures[future]
            try:
                results[token['symbol']] = future.result()
            except Exception as exc:
                print(f'{token["symbol"]} generated an exception: {exc}')

    # Print the results in series
    print_group_data(results)


def print_group_data(results: Dict):
    """
    Prints grouped data and uses printIndividual to print each token's data.
    """
    # Implement group printing logic here
    # For each token in results, call printIndividual
    for symbol, data in results.items():
        print_individual(data)
    # Add any group summary logic here


def print_individual(data: Dict):
    """
    Prints individual token data.
    """
    print_token_data(data)  # Use the earlier defined function

main()