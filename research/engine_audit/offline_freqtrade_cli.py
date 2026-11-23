#!/usr/bin/env python3
"""Run Freqtrade backtesting with locally supplied Binance USD-M market metadata.

The exchange adapter is constructed with validate=False and seeded from static
contract metadata. This prevents CCXT from calling exchangeInfo/markets endpoints;
all OHLCV inputs must already exist locally and are checksum-verified separately.
"""
from __future__ import annotations
import sys

def install_offline_exchange_metadata(exchange):
    markets = []
    for base, symbol, amount_tick, price_tick, min_cost in (
        ("BTC", "BTC/USDT:USDT", 0.001, 0.1, 5.0),
        ("ETH", "ETH/USDT:USDT", 0.001, 0.01, 5.0),
    ):
        markets.append({
            "id": f"{base}USDT",
            "symbol": symbol,
            "base": base,
            "quote": "USDT",
            "settle": "USDT",
            "baseId": base,
            "quoteId": "USDT",
            "settleId": "USDT",
            "type": "swap",
            "spot": False,
            "margin": False,
            "swap": True,
            "future": False,
            "option": False,
            "active": True,
            "contract": True,
            "linear": True,
            "inverse": False,
            "contractSize": 1.0,
            "precision": {"amount": amount_tick, "price": price_tick},
            "limits": {
                "amount": {"min": amount_tick, "max": None},
                "price": {"min": price_tick, "max": None},
                "cost": {"min": min_cost, "max": None},
                "leverage": {"min": 1, "max": 125},
            },
            "maker": 0.0002,
            "taker": 0.0005,
            "info": {"symbol": f"{base}USDT", "contractType": "PERPETUAL", "status": "TRADING"},
        })
    exchange._api.set_markets(markets)
    exchange._api_async.set_markets(markets)
    exchange._markets = exchange._api.markets
    # Keep sync and async CCXT views identical for Freqtrade helper methods.
    exchange._api_async.markets = exchange._api.markets
    exchange._markets = exchange._api.markets

def main():
    from freqtrade.resolvers import ExchangeResolver
    original_load = ExchangeResolver.load_exchange

    def load_exchange_offline(config, *, exchange_config=None, validate=True, load_leverage_tiers=False):
        instance = original_load(
            config,
            exchange_config=exchange_config,
            validate=False,
            load_leverage_tiers=False,
        )
        install_offline_exchange_metadata(instance)
        return instance

    ExchangeResolver.load_exchange = staticmethod(load_exchange_offline)
    from freqtrade.main import main as freqtrade_main
    freqtrade_main(sys.argv[1:])

if __name__ == "__main__":
    main()
