"""Trading engine orchestrating market data, strategy, risk, and orders."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from odyssey_algo.trading.journal import TradeJournal
from odyssey_algo.trading.market_data import MarketDataService
from odyssey_algo.trading.market_hours import is_market_open, now_ist, seconds_until_market_open
from odyssey_algo.trading.models import TradingMode
from odyssey_algo.trading.nifty_instruments import NiftyOptionsResolver
from odyssey_algo.trading.orders.broker import LiveBroker, PaperBroker
from odyssey_algo.trading.orders.manager import OrderManager
from odyssey_algo.trading.risk.manager import RiskManager
from odyssey_algo.trading.settings import TradingSettings
from odyssey_algo.trading.strategy.base import BaseStrategy, StrategyContext, build_strategy
from odyssey_algo.trading.upstox_rest import UpstoxRestClient

logger = logging.getLogger("odyssey_algo")


@dataclass
class TradingEngine:
    settings: TradingSettings
    client: UpstoxRestClient
    market_data: MarketDataService
    resolver: NiftyOptionsResolver
    broker: PaperBroker | LiveBroker
    risk: RiskManager
    journal: TradeJournal
    orders: OrderManager
    strategy: BaseStrategy
    context: StrategyContext
    _fired_today: set[str] = field(default_factory=set)
    _running: bool = False

    @classmethod
    def from_settings(cls, settings: TradingSettings) -> TradingEngine:
        client = UpstoxRestClient(settings.access_token)
        market_data = MarketDataService(client)
        resolver = NiftyOptionsResolver(
            client,
            underlying=settings.underlying,
            expiry=settings.option_expiry,
        )

        if settings.trading_mode == TradingMode.PAPER:
            broker = PaperBroker()
        else:
            broker = LiveBroker(client, algo_name=settings.algo_name)

        risk = RiskManager(
            broker=broker,
            max_open_positions=settings.max_open_positions,
            max_daily_loss_inr=settings.max_daily_loss_inr,
            max_order_lots=settings.max_order_lots,
            kill_switch=settings.kill_switch,
        )
        journal = TradeJournal(settings.output_dir, enabled=settings.journal_enabled)
        orders = OrderManager(broker, risk, market_data, journal)
        strategy = build_strategy(settings)
        context = StrategyContext(settings=settings, resolver=resolver)

        return cls(
            settings=settings,
            client=client,
            market_data=market_data,
            resolver=resolver,
            broker=broker,
            risk=risk,
            journal=journal,
            orders=orders,
            strategy=strategy,
            context=context,
        )

    def run(self) -> None:
        self._running = True
        logger.info(
            "Engine started: mode=%s strategy=%s underlying=%s expiry=%s",
            self.settings.trading_mode.value,
            self.settings.strategy_name,
            self.settings.underlying,
            self.settings.option_expiry,
        )
        self.journal.record(
            "engine_start",
            {
                "mode": self.settings.trading_mode.value,
                "strategy": self.settings.strategy_name,
                "algo_name": self.settings.algo_name,
            },
        )

        while self._running:
            if not is_market_open():
                wait_sec = min(seconds_until_market_open(), 60)
                logger.info("Market closed. Sleeping %ss (IST: %s)", wait_sec, now_ist())
                time.sleep(wait_sec)
                continue

            self._poll_once()
            time.sleep(self.settings.poll_interval_sec)

    def stop(self) -> None:
        self._running = False
        summary = self.orders.positions_summary()
        self.journal.record("engine_stop", {"positions": summary})
        logger.info("Engine stopped. Open positions: %d", len(summary))

    def _poll_once(self) -> None:
        spot = self.market_data.get_spot(self.settings.nifty_index_key)
        self.context.spot_price = spot

        if spot is None:
            logger.warning("No NIFTY spot quote available")
            return

        logger.info("NIFTY spot: %.2f", spot)
        signals = self.strategy.on_tick(self.context)
        if not signals:
            return

        for signal in signals:
            dedupe_key = f"{signal.instrument_key}:{signal.action.value}"
            if dedupe_key in self._fired_today:
                continue

            order_request = self.strategy.signal_to_order(signal)
            if order_request is None:
                continue

            result = self.orders.execute_signal(signal, order_request)
            if result is not None:
                self._fired_today.add(dedupe_key)
                logger.info("Signal executed: %s -> %s", signal.reason, result.status.value)
