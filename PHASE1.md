# Phase 1 — NIFTY Options Trading Engine

## Scope

Phase 1 establishes the production foundation for algorithmic NIFTY options trading on Upstox. It is intentionally conservative: **paper trading is the default**, risk controls are enforced before every order, and all events are journaled.

### Delivered

- **Trading engine** — poll-based loop with NSE market hours gating
- **Upstox REST integration** — instruments search, LTP quotes, order placement
- **NIFTY options resolver** — ATM CE/PE contract lookup by expiry preset
- **Order pipeline** — signal → risk check → broker → journal
- **Paper broker** — instant fills at LTP for development and backtesting
- **Live broker** — OrderApiV3 with `X-Algo-Name` header for SEBI compliance
- **Risk manager** — max positions, max lots, daily loss cap, kill switch
- **Trade journal** — append-only JSONL in `data/trade_journal.jsonl`
- **Reference strategy** — `nifty_momentum`: enter ATM CE/PE on ±50pt NIFTY move from session open
- **Tests** — models, market hours, risk, broker, strategy

### Not in Phase 1 (future phases)

- WebSocket-driven strategy triggers (uses REST polling)
- Options greeks feed parsing
- Exit/stop-loss logic and PnL tracking
- Portfolio streamer integration for fill confirmation
- Multi-strategy orchestration
- Backtesting framework
- Token refresh / OAuth flow
- Database persistence

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Strategy   │────▶│ OrderManager │────▶│   Broker    │
│ (momentum)  │     │              │     │ paper/live  │
└──────▲──────┘     └──────┬───────┘     └─────────────┘
       │                   │
       │            ┌──────▼───────┐
       │            │ RiskManager  │
       │            └──────────────┘
       │
┌──────┴──────┐     ┌──────────────┐
│ MarketData  │◀────│ Upstox REST  │
│   Service   │     │    Client    │
└─────────────┘     └──────────────┘
                           │
                    ┌──────▼───────┐
                    │ Instruments  │
                    │    API       │
                    └──────────────┘
```

## Event flow

1. Engine polls NIFTY spot LTP every `ODYSSEY_POLL_INTERVAL_SEC` seconds
2. Strategy compares spot to session open; emits signal if threshold breached
3. Resolver fetches ATM option contract (CE or PE)
4. Risk manager validates position limits, lot size, kill switch
5. Broker executes (paper fill at LTP, or live order to Upstox)
6. Journal records signal, order, and result

## Safety defaults

| Setting | Default | Rationale |
|---------|---------|-----------|
| `ODYSSEY_TRADING_MODE` | `paper` | No real capital at risk during development |
| `ODYSSEY_MAX_ORDER_LOTS` | `1` | Minimum viable size (75 qty for NIFTY) |
| `ODYSSEY_MAX_OPEN_POSITIONS` | `2` | Prevents over-exposure |
| `ODYSSEY_MAX_DAILY_LOSS_INR` | `5000` | Circuit breaker |
| `ODYSSEY_KILL_SWITCH` | `false` | Set `true` to halt all trading immediately |

## Adding a new strategy

1. Subclass `BaseStrategy` in `src/odyssey_algo/trading/strategy/`
2. Implement `on_tick(context) -> list[Signal]`
3. Register in `build_strategy()` and `VALID_STRATEGIES`
4. Set `ODYSSEY_STRATEGY=<name>` in `.env`
