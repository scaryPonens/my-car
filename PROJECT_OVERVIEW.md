# Project Overview

Technical architecture and design decisions for Smart Car Virtual Assistant.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Smart Car VA                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   Telegram  │    │   FastAPI   │    │   Smartcar  │    │   Supabase  │  │
│  │     Bot     │◄──►│   Server    │◄──►│     API     │    │   Database  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│         │                  │                  │                  ▲          │
│         │                  │                  │                  │          │
│         ▼                  ▼                  ▼                  │          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │          │
│  │    User     │    │  LLM Service│    │   Vehicle   │─────────┘          │
│  │  Commands   │    │  (OpenAI/   │    │    Data     │                     │
│  │             │    │  Anthropic) │    │             │                     │
│  └─────────────┘    └─────────────┘    └─────────────┘                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI | REST API, OAuth callback, webhooks |
| Bot | python-telegram-bot | Telegram bot interface |
| Vehicle API | Smartcar SDK | Vehicle data and control |
| Database | Supabase (PostgreSQL) | User and vehicle storage |
| LLM | OpenAI/Anthropic | Natural language processing |
| Hosting | Railway | Cloud deployment |

## Design Principles

### Functional Programming

The codebase follows functional programming principles:

1. **Pure Functions**: Business logic has no side effects
   ```python
   def build_vehicle_context(vehicles: list[Vehicle], data: VehicleData) -> str:
       # Pure function - same inputs always produce same output
   ```

2. **Immutability**: All data models are Pydantic (treated as immutable)
   ```python
   class Vehicle(BaseModel):
       # Fields are not mutated after creation
   ```

3. **Higher-Order Functions**: Functions that take/return functions
   ```python
   def with_supabase_client(func):
       # Decorator injects database client
   ```

4. **Function Composition**: Building complex operations from simple ones
   ```python
   pipeline = pipe(validate_input, process_data, format_output)
   ```

5. **Type Safety**: Full type hints throughout
   ```python
   def get_user_by_telegram_id(client: Client, telegram_id: int) -> Optional[User]:
   ```

### Decorator Patterns

#### Client Injection
```python
@with_supabase_client
def get_user_vehicles(client: Client, user_id: str) -> list[Vehicle]:
    # Client is automatically injected
```

#### User Authentication
```python
@require_user
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = context.user_data["user"]  # User is guaranteed to exist
```

#### Error Handling
```python
@safe_api_call
def fetch_data():
    # Exceptions are caught and handled gracefully
```

### Maybe Monad

Handles optional values without null checks:

```python
result = (
    Maybe(user)
    .map(lambda u: u.profile)
    .map(lambda p: p.settings)
    .get_or(default_settings)
)
```

## Data Flow

### User Registration
```
Telegram /start → Bot Handler → get_or_create_user → Supabase
```

### Vehicle Connection
```
/connect → Generate Auth URL → User OAuth → Callback → Exchange Code →
Store Tokens → Fetch Vehicle Info → Save Vehicle
```

### Status Request
```
/status → Get User → Get Vehicles → Check Token → Refresh if needed →
Fetch Data from Smartcar → Format Response → Send to User
```

### Natural Language
```
User Message → Get Context (vehicles, data) → Build Prompt →
LLM Processing → Parse Response → Execute Action → Send Result
```

## Module Structure

### config/settings.py
- Pydantic Settings for configuration
- Environment variable loading
- Singleton pattern with `get_settings()`

### models/schemas.py
- All Pydantic data models
- Enums for status and actions
- No business logic, pure data

### integrations/supabase_client.py
- Database operations
- Decorator pattern for client injection
- Pure functions for CRUD operations

### integrations/smartcar_client.py
- Smartcar API wrapper
- Safe API call utilities
- Token management
- Comprehensive data fetching

### services/telegram_bot.py
- Command handlers
- Message handlers
- Action execution
- User state management

### services/llm_service.py
- Multi-provider LLM support
- System prompts
- Response parsing
- Context building

### utils/helpers.py
- Functional utilities
- Maybe monad
- Composition functions
- Retry logic

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Vehicles Table
```sql
CREATE TABLE vehicles (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    smartcar_vehicle_id VARCHAR(255),
    make VARCHAR(100),
    model VARCHAR(100),
    year INTEGER,
    access_token TEXT,
    refresh_token TEXT,
    token_expiration TIMESTAMP,
    status VARCHAR(50),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Row Level Security
All tables have RLS enabled with policies ensuring:
- Users can only access their own data
- Service role has full access for backend operations

## LLM Integration

### System Prompt
The LLM receives a system prompt that:
- Defines the assistant's role
- Lists available actions
- Specifies response format (JSON)
- Includes safety guidelines

### Response Format
```json
{
    "message": "User-friendly response",
    "action": "get_status|lock|unlock|none",
    "parameters": {},
    "confidence": 0.95
}
```

### Action Execution
1. Parse LLM response
2. Validate action and confidence
3. Execute appropriate function
4. Combine result with message
5. Send to user

## Error Handling

### Layers of Error Handling

1. **API Level**: `safe_api_call` wrapper returns defaults
2. **Database Level**: Try/except with logging
3. **Bot Level**: User-friendly error messages
4. **HTTP Level**: FastAPI exception handlers

### Token Refresh
```python
def ensure_valid_token(vehicle: Vehicle) -> Optional[dict]:
    if not vehicle.tokens or vehicle.tokens.is_expired():
        return refresh_access_token(vehicle.tokens.refresh_token)
    return None
```

## Testing Strategy

### Unit Tests
- Model validation
- Utility functions
- Pure function logic

### Integration Tests (Future)
- Database operations
- API endpoints
- Bot handlers

### End-to-End Tests (Future)
- Full user flows
- OAuth flows
- Vehicle control

## Security Considerations

1. **Secrets Management**: All secrets in environment variables
2. **Token Security**: OAuth tokens encrypted in database
3. **RLS Policies**: Database-level access control
4. **Input Validation**: Pydantic models validate all input
5. **Error Messages**: No internal details exposed to users

## Performance Optimizations

1. **Memoization**: Cache expensive computations
2. **Connection Pooling**: Supabase handles pooling
3. **Async Operations**: Telegram bot uses async handlers
4. **Parallel Fetching**: Vehicle data fetched in parallel

## Future Enhancements

1. **Webhook Mode**: Switch from polling to webhooks
2. **Redis Caching**: Cache vehicle data
3. **Analytics**: Track usage patterns
4. **Multi-language**: i18n support
5. **Web Dashboard**: Browser-based control panel
6. **More Vehicle Controls**: Start engine, climate control
7. **Scheduled Commands**: Automated status checks
8. **Voice Messages**: Audio command support
