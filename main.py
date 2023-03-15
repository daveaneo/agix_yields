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

YIELD_VAULT_CONTRACT_ADDRESS= os.getenv('YIELD_VAULT_CONTRACT_ADDRESS')

AGIX_CONTRACT_ADDRESS= os.getenv('AGIX_CONTRACT_ADDRESS')
USDT_CONTRACT_ADDRESS= os.getenv('USDT_CONTRACT_ADDRESS')
ETH_CONTRACT_ADDRESS= os.getenv('ETH_CONTRACT_ADDRESS')

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
yield_vault_contract = my_provider.eth.contract(address=YIELD_VAULT_CONTRACT_ADDRESS, abi=YIELD_VAULT_ABI)


decimals = {
    "usdt": 6,
    "eth": 18,
    "agix": 8,
}

def get_my_returns(my_wallet):
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



# these return percents out of 100
def get_APY():
    # (USDC) Lending Contract
    total_usdc_stake = USDC_lending_contract.functions.totalDepositedUsdc().call() / 10 ** decimals["usdc"]

    harvest_info = USDC_lending_contract.functions.harvestInfo().call()
    total_yield_USDC = harvest_info[1] / 10 ** decimals["usdc"]
    rewardRate = harvest_info[0]  # seconds

    # (GSD) Staking Contract
    total_gsd_stake = GSD_staking_contract.functions.aggregateTVL().call() / 10 ** decimals['gsd']  # aggregate_TVL

    # Pair Contract for GSD
    reserves = pair_contract.functions.getReserves().call()
    #    gsd_price = 0  # pair_contract.functions.getReserves().call()
    token_zero = pair_contract.functions.token0().call()

    # get price per gsd wei
    if token_zero == GSD_CONTRACT_ADDRESS:
        gsd_price = (reserves[1] / 10 ** decimals['usdc']) / (reserves[0] / 10 ** decimals['gsd'])
    else:
        gsd_price = (reserves[0] / 10 ** decimals['usdc']) / (reserves[1] / 10 ** decimals['gsd'])

    # ts stores the time in seconds
    # ts = time.time()

    seconds_in_year = 365 * 24 * 60 * 60

    totalYieldInDollars = total_yield_USDC
    totalYieldFromStakeInUSD = totalYieldInDollars * 0.05  # 5% of USDC Lending yield
    totalGSDStakedValueInUSD = total_gsd_stake * gsd_price
    totalUsdcStakeInUSD = total_usdc_stake

    # Lending
    periodInterestRateLending = 1 if totalUsdcStakeInUSD == 0 else (1 + totalYieldInDollars * 0.9 / totalUsdcStakeInUSD)
    periodBaseLending = periodInterestRateLending

    # Staking
    periodInterestRateStaking = 1 if totalGSDStakedValueInUSD == 0 else ( totalYieldFromStakeInUSD / totalGSDStakedValueInUSD) + 1
    periodBaseStaking = periodInterestRateStaking

    yearly_apy_lending = 100 * (periodBaseLending ** (seconds_in_year / rewardRate)) - 100
    yearly_apy_staking = 100 * (periodBaseStaking ** (seconds_in_year / rewardRate)) - 100

    # these return percents out of 100
    return {
        "gsd_apy": None if totalUsdcStakeInUSD == 0 else yearly_apy_staking,
        "usdc_apy": None if totalGSDStakedValueInUSD == 0 else yearly_apy_lending
    }

# get_APY()

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    get_my_returns(WALLET_ADDRESS)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
