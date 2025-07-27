import os
from dotenv import load_dotenv

load_dotenv()
import pytest
from src.api.coinmarketcap import CoinMarketCapClient


@pytest.mark.skipif(
    not os.getenv("COINMARKETCAP_API_KEY"),
    reason="COINMARKETCAP_API_KEY not set in environment",
)
def test_coinmarketcap_listings_latest():
    api_key = os.getenv("COINMARKETCAP_API_KEY")
    client = CoinMarketCapClient(api_key=api_key)
    coins = client.get_listings_latest(limit=2)
    assert isinstance(coins, list)
    assert len(coins) > 0
    assert "name" in coins[0]
    assert "symbol" in coins[0]


def test_coinmarketcap_quotes_latest():
    api_key = os.getenv("COINMARKETCAP_API_KEY")
    client = CoinMarketCapClient(api_key=api_key)
    data = client.get_quotes_latest(symbol="BTC")
    assert isinstance(data, dict)
    assert any("BTC" in k or "1" in k for k in data.keys())
