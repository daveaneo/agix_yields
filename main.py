import os
from dotenv import load_dotenv
from web3 import Web3
import json
from web3.gas_strategies.rpc import rpc_gas_price_strategy

# load data from env
load_dotenv()
PRIVATE_KEY = os.getenv('PRIVATE_KEY')
WALLET_ADDRESS = os.getenv('WALLET_ADDRESS')


AGIX_USDT_CONTRACT_ADDRESS= os.getenv('AGIX_USDT_CONTRACT_ADDRESS')
ETH_USDT_CONTRACT_ADDRESS= os.getenv('ETH_USDT_CONTRACT_ADDRESS')
AGIX_ETH_CONTRACT_ADDRESS= os.getenv('AGIX_ETH_CONTRACT_ADDRESS')
RJV_ETH_CONTRACT_ADDRESS= os.getenv('RJV_ETH_CONTRACT_ADDRESS')

YIELD_VAULT_CONTRACT_ADDRESS= os.getenv('YIELD_VAULT_CONTRACT_ADDRESS')

AGIX_CONTRACT_ADDRESS= os.getenv('AGIX_CONTRACT_ADDRESS')
USDT_CONTRACT_ADDRESS= os.getenv('USDT_CONTRACT_ADDRESS')
ETH_CONTRACT_ADDRESS= os.getenv('ETH_CONTRACT_ADDRESS')
RJV_CONTRACT_ADDRESS= os.getenv('RJV_CONTRACT_ADDRESS')

RPC = os.getenv('RPC')
CHAIN_ID = int(str(os.getenv('CHAIN_ID')))

# Set up Contract
with open('ABI/pair.json', 'r') as file:
    PAIR_ABI = json.load(file)

with open('ABI/yieldVault.json', 'r') as file:
    YIELD_VAULT_ABI = json.load(file)


my_provider = Web3(Web3.HTTPProvider(RPC))
# my_provider.eth.default_account = WALLET_ADDRESS

# Set the gas price strategy
my_provider.eth.set_gas_price_strategy(rpc_gas_price_strategy)

# create contract instance from address and abi
agix_usdt_pair_contract = my_provider.eth.contract(address=AGIX_USDT_CONTRACT_ADDRESS, abi=PAIR_ABI)
eth_usdt_pair_contract = my_provider.eth.contract(address=ETH_USDT_CONTRACT_ADDRESS, abi=PAIR_ABI)
agix_eth_pair_contract = my_provider.eth.contract(address=AGIX_ETH_CONTRACT_ADDRESS, abi=PAIR_ABI)
rjv_eth_pair_contract = my_provider.eth.contract(address=RJV_ETH_CONTRACT_ADDRESS, abi=PAIR_ABI)

yield_vault_contract = my_provider.eth.contract(address=YIELD_VAULT_CONTRACT_ADDRESS, abi=YIELD_VAULT_ABI)


decimals = {
    "usdt": 6,
    "eth": 18,
    "agix": 8,
    "rjv": 6,
}





def get_my_agix_returns(my_wallet):
    print(f'\n########################################')
    print(f'##########    AGIX     ################')
    ###################################################
    # get prices
    reserves = agix_usdt_pair_contract.functions.getReserves().call()
    token_zero = agix_usdt_pair_contract.functions.token0().call()
    if token_zero == AGIX_CONTRACT_ADDRESS:
        agix_price = (reserves[1] / 10 ** decimals['usdt']) / (reserves[0] / 10 ** decimals['agix'])
    else:
        agix_price = (reserves[0] / 10 ** decimals['usdt']) / (reserves[1] / 10 ** decimals['agix'])


    reserves = eth_usdt_pair_contract.functions.getReserves().call()
    token_zero = eth_usdt_pair_contract.functions.token0().call()
    if token_zero == ETH_CONTRACT_ADDRESS:
        eth_price = (reserves[1] / 10 ** decimals['usdt']) / (reserves[0] / 10 ** decimals['eth'])
    else:
        eth_price = (reserves[0] / 10 ** decimals['usdt']) / (reserves[1] / 10 ** decimals['eth'])

    #################################################
    # Get total tokens for each in lp
    total_agix = 0
    total_eth = 0
    # AGIX Vault
    my_lp, _ = yield_vault_contract.functions.userInfo(2, my_wallet).call()

    # Uniswap Pair
    reserves = agix_eth_pair_contract.functions.getReserves().call()
    token_zero = agix_eth_pair_contract.functions.token0().call()

    my_lp += agix_eth_pair_contract.functions.balanceOf(my_wallet).call()
    total_lp = agix_eth_pair_contract.functions.totalSupply().call()

    if token_zero == AGIX_CONTRACT_ADDRESS:
        total_agix += reserves[0]*my_lp/total_lp/(10**decimals["agix"])
        total_eth += reserves[1]*my_lp/total_lp/(10**decimals["eth"])
    else:
        total_agix += reserves[1]*my_lp/total_lp/(10**decimals["agix"])
        total_eth += reserves[0]*my_lp/total_lp/(10**decimals["eth"])

    print(f'Total Assets')
    print(f'  ETH: {round(total_eth, 2):,}')
    print(f'  AGIX: {round(total_agix, 2):,}')

    print(f'Prices')
    print(f'  ETH: ${round(eth_price, 2):,}')
    print(f'  AGIX: ${round(agix_price, 2):,}')

    print(f'Asset Value')
    print(f'  ETH: ${round(total_eth*eth_price, 2):,}')
    print(f'  AGIX: ${round(total_agix*agix_price, 2):,}')
    print(f'  Combined: ${round(total_eth*eth_price+total_agix*agix_price, 2):,}')

    print(f'Percent Of Liquidity Pool')
    print(f'  ETH-AGIX: {round(my_lp/total_lp*100, 2):,} %')


def get_my_rjv_returns(my_wallet):
    print(f'\n########################################')
    print(f'##########    REJUVE     ################')
    ###################################################
    # get prices
    reserves = rjv_eth_pair_contract.functions.getReserves().call()
    token_zero = rjv_eth_pair_contract.functions.token0().call()
    if token_zero == RJV_CONTRACT_ADDRESS:
        rjv_price_in_eth = (reserves[1] / 10 ** decimals['eth']) / (reserves[0] / 10 ** decimals['rjv'])
    else:
        rjv_price_in_eth = (reserves[0] / 10 ** decimals['eth']) / (reserves[1] / 10 ** decimals['rjv'])


    # Get ETH Price
    reserves = eth_usdt_pair_contract.functions.getReserves().call()
    token_zero = eth_usdt_pair_contract.functions.token0().call()
    if token_zero == ETH_CONTRACT_ADDRESS:
        eth_price = (reserves[1] / 10 ** decimals['usdt']) / (reserves[0] / 10 ** decimals['eth'])
    else:
        eth_price = (reserves[0] / 10 ** decimals['usdt']) / (reserves[1] / 10 ** decimals['eth'])


    rjv_price = rjv_price_in_eth *eth_price


    #################################################
    # Get total tokens for each in lp
    total_rjv = 0
    total_eth = 0
    # AGIX Vault
    # my_lp, _ = yield_vault_contract.functions.userInfo(2, my_wallet).call()

    # Uniswap Pair
    reserves = rjv_eth_pair_contract.functions.getReserves().call()
    token_zero = rjv_eth_pair_contract.functions.token0().call()

    my_lp = rjv_eth_pair_contract.functions.balanceOf(my_wallet).call()
    total_lp = rjv_eth_pair_contract.functions.totalSupply().call()

    if token_zero == RJV_CONTRACT_ADDRESS:
        total_rjv += reserves[0]*my_lp/total_lp/(10**decimals["rjv"])
        total_eth += reserves[1]*my_lp/total_lp/(10**decimals["eth"])
    else:
        total_rjv += reserves[1]*my_lp/total_lp/(10**decimals["rjv"])
        total_eth += reserves[0]*my_lp/total_lp/(10**decimals["eth"])

    print(f'Total Assets')
    print(f'  ETH: {round(total_eth, 2):,}')
    print(f'  RJV: {round(total_rjv, 2):,}')

    print(f'Prices')
    print(f'  ETH: ${round(eth_price, 2):,}')
    print(f'  RJV: ${round(rjv_price, 2):,}')

    print(f'Asset Value')
    print(f'  ETH: ${round(total_eth*eth_price, 2):,}')
    print(f'  RJV: ${round(total_rjv*rjv_price, 2):,}')
    print(f'  Combined: ${round(total_eth*eth_price+total_rjv*rjv_price, 2):,}')

    print(f'Percent Of Liquidity Pool')
    print(f'  ETH-RJV: {round(my_lp/total_lp*100, 2):,} %')


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    get_my_agix_returns(WALLET_ADDRESS)
    get_my_rjv_returns(WALLET_ADDRESS)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
