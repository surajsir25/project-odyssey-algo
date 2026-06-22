# Upstox WebSocket Architecture Flowchart

## Complete WebSocket Flow

```mermaid
flowchart TD
    A["START: Initialize Handler"] --> B["Create UpstoxMarketDataHandler"]
    B --> C["Setup API Configuration<br/>access_token"]
    C --> D["Create ApiClient"]
    D --> E["Initialize CsvCandleStore"]
    
    E --> F["Call initialize_streamer()"]
    F --> G["Create MarketDataStreamerV3<br/>instrumentKeys & mode"]
    G --> H["Setup Event Handlers<br/>on: open, message, close, error, reconnecting"]
    
    H --> I["Enable Auto-Reconnect<br/>interval, retry_count"]
    I --> J["Call connect()"]
    
    J --> K{"WebSocket<br/>Connection"}
    
    %% Connection Open Path
    K -->|Success| L["_on_open() triggered"]
    L --> M["Log: Connection established"]
    M --> N["Call _resubscribe_all()"]
    N --> O["Subscribe to instruments<br/>in specified mode"]
    O --> P["Ready to receive messages"]
    
    %% Message Received Path
    P --> Q["_on_message() triggered"]
    Q --> R{"Parse JSON<br/>Message"}
    
    R -->|Decode Error| S["Log JSONDecodeError"]
    S --> Q
    
    R -->|Success| T{"Check Message<br/>Type"}
    T -->|market_info| U["Skip processing"]
    U --> Q
    
    T -->|market_data| V["Extract feeds"]
    V --> W{"Custom<br/>Callback?"}
    
    W -->|Yes| X["Call on_feed()<br/>Custom processing"]
    X --> Q
    
    W -->|No| Y["Extract candles<br/>from feed data"]
    Y --> Z["For each interval<br/>1min, 5min, etc"]
    Z --> AA["Write candle to CSV"]
    AA --> AB["Log OHLC data"]
    AB --> Q
    
    %% Error Handling Path
    K -->|Failure| AC["_on_error() triggered"]
    AC --> AD["Log WebSocket error"]
    AD --> AE{"Auto-Reconnect<br/>Enabled?"}
    
    AE -->|Yes| AF["_on_reconnecting() triggered"]
    AF --> AG["Wait reconnect_interval seconds"]
    AG --> AH["Retry connection"]
    AH --> K
    
    AE -->|No| AI["Stop connection"]
    
    %% Close Path
    P --> AJ["_on_close() triggered"]
    AJ --> AK["Log: Connection closed"]
    AK --> AL{"Graceful<br/>Disconnect?"}
    
    AL -->|Yes| AM["END: Cleanup"]
    AL -->|No| AN["Check error logs"]
    AN --> AE
    
    %% Operations during streaming
    P --> AO["subscribe_instruments()"]
    AO --> AP["Add to subscriptions"]
    AP --> AQ["Stream resumes with new instruments"]
    AQ --> Q
    
    P --> AR["unsubscribe_instruments()"]
    AR --> AS["Remove from subscriptions"]
    AS --> AT["Stream continues with remaining instruments"]
    AT --> Q
    
    style A fill:#90EE90
    style AM fill:#FFB6C6
    style K fill:#87CEEB
    style R fill:#87CEEB
    style T fill:#87CEEB
    style W fill:#87CEEB
    style AE fill:#87CEEB
    style AL fill:#87CEEB
```

## Message Processing Pipeline

```mermaid
flowchart LR
    A["Raw WebSocket<br/>Message"] --> B{"Message<br/>Format"}
    B -->|String| C["JSON Parse"]
    B -->|Dict| D["Use as-is"]
    C --> E["Extract Data"]
    D --> E
    E --> F["Get feeds dict"]
    F --> G["For each instrument_key"]
    G --> H{"Custom<br/>Handler?"}
    H -->|Yes| I["on_feed callback"]
    I --> J["Custom Processing"]
    H -->|No| K["extract_candles_from_feed"]
    K --> L["Generate candles<br/>1min, 5min"]
    L --> M["Write to CSV"]
    M --> N["Log OHLC<br/>Open/High/Low/Close<br/>Volume"]
    J --> O["Ready for next message"]
    N --> O
    
    style A fill:#FFE4E1
    style B fill:#87CEEB
    style H fill:#87CEEB
    style O fill:#90EE90
```

## State Transitions

```mermaid
stateDiagram-v2
    [*] --> Initialized
    Initialized --> Connected: connect()
    Connected --> Streaming: _on_open()
    
    Streaming --> Streaming: _on_message()
    Streaming --> Streaming: subscribe_instruments()
    Streaming --> Streaming: unsubscribe_instruments()
    
    Streaming --> Error: _on_error()
    Error --> Reconnecting: auto_reconnect enabled
    Reconnecting --> Connected: reconnect_interval elapsed
    
    Streaming --> Closed: _on_close()
    Connected --> Closed: disconnect()
    Reconnecting --> Closed: max_retries exceeded
    
    Closed --> [*]
    
    note right of Streaming
        Active message processing
        Can change subscriptions
        Auto-logging enabled
    end note
    
    note right of Reconnecting
        Waiting to retry
        interval: reconnect_interval
        max attempts: max_retries
    end note
```

## Component Interaction

```mermaid
graph TB
    subgraph Client["Client Layer"]
        CLI["CLI/Application"]
        Handler["UpstoxMarketDataHandler"]
    end
    
    subgraph Config["Configuration"]
        Settings["Settings<br/>access_token, mode<br/>reconnect_interval"]
        ApiConfig["API Configuration"]
    end
    
    subgraph Upstox["Upstox SDK"]
        ApiClient["ApiClient"]
        Streamer["MarketDataStreamerV3"]
    end
    
    subgraph Events["Event Handlers"]
        OnOpen["_on_open()"]
        OnMsg["_on_message()"]
        OnClose["_on_close()"]
        OnErr["_on_error()"]
        OnRecon["_on_reconnecting()"]
    end
    
    subgraph Processing["Data Processing"]
        Extract["extract_candles_from_feed()"]
        Store["CsvCandleStore"]
    end
    
    subgraph Output["Output"]
        CSV["CSV Files<br/>1min, 5min"]
        Logs["Log Files"]
    end
    
    CLI -->|initialize_streamer| Handler
    Handler -->|uses| Settings
    Handler -->|creates| ApiClient
    ApiClient -->|uses| ApiConfig
    Handler -->|creates| Streamer
    
    Streamer -->|emits| OnOpen
    Streamer -->|emits| OnMsg
    Streamer -->|emits| OnClose
    Streamer -->|emits| OnErr
    Streamer -->|emits| OnRecon
    
    OnOpen -->|subscribes| Streamer
    OnMsg -->|processes| Extract
    Extract -->|writes| Store
    Store -->|saves| CSV
    
    Handler -->|logs| Logs
    Events -->|logs| Logs
    
    style Handler fill:#90EE90
    style Streamer fill:#87CEEB
    style Extract fill:#FFD700
    style CSV fill:#FFB6C6
```

---

## Key Methods Reference

| Method | Purpose | Parameters |
|--------|---------|-----------|
| `initialize_streamer()` | Setup streamer with instruments | `instruments: list[str]`, `mode: str` |
| `connect()` | Establish WebSocket connection | None |
| `disconnect()` | Close WebSocket connection | None |
| `enable_auto_reconnect()` | Configure reconnection behavior | `enabled, interval, retry_count` |
| `subscribe_instruments()` | Add new instruments to stream | `instruments: list[str]`, `mode: str` |
| `unsubscribe_instruments()` | Remove instruments from stream | `instruments: list[str]` |
| `set_subscriptions()` | Replace entire subscription list | `instruments: list[str]`, `mode: str` |

## Error Handling Flow

```
Error Occurs
    ↓
_on_error() callback
    ↓
Log error message
    ↓
Check: auto_reconnect enabled?
    ├─ YES → _on_reconnecting()
    │        ↓
    │        Wait reconnect_interval seconds
    │        ↓
    │        Retry connection
    │        ↓
    │        Check: retry_count < max_retries?
    │        ├─ YES → Attempt reconnect
    │        └─ NO → Stop
    │
    └─ NO → Stop connection
```

