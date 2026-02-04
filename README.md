# Smart Car Virtual Assistant

A Telegram bot for managing connected vehicles through the Smartcar API, with natural language processing powered by OpenAI/Anthropic.

## Features

- **Telegram Bot Interface**: Interact with your car through Telegram commands or natural language
- **Vehicle Connection**: Connect any Smartcar-compatible vehicle (Tesla, Ford, BMW, etc.)
- **Real-time Data**: Get fuel/battery level, odometer, location, and tire pressure
- **Vehicle Control**: Lock and unlock your car remotely
- **Multi-Vehicle Support**: Manage multiple vehicles per user
- **AI-Powered Conversations**: Natural language processing for intuitive interactions

## Quick Start

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Smartcar Developer Account ([dashboard.smartcar.com](https://dashboard.smartcar.com))
- Supabase Project ([supabase.com](https://supabase.com))
- OpenAI or Anthropic API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd smart-car-va
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Set up database**
   - Go to your Supabase project's SQL Editor
   - Run the contents of `database/schema.sql`

6. **Run the application**
   ```bash
   python main.py
   ```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message and introduction |
| `/connect` | Connect a new vehicle via Smartcar |
| `/vehicles` | List all connected vehicles |
| `/status` | Get current vehicle status |
| `/help` | Show available commands |

### Natural Language

You can also chat naturally with the bot:

- "What's my fuel level?"
- "Where is my car parked?"
- "Lock my car"
- "Show me the battery status"
- "What's the tire pressure?"

## Project Structure

```
smart-car-va/
├── config/
│   └── settings.py          # Configuration management
├── models/
│   └── schemas.py           # Pydantic data models
├── integrations/
│   ├── supabase_client.py   # Database operations
│   └── smartcar_client.py   # Smartcar API wrapper
├── services/
│   ├── telegram_bot.py      # Telegram bot handlers
│   └── llm_service.py       # LLM integration
├── utils/
│   └── helpers.py           # Functional utilities
├── database/
│   └── schema.sql           # PostgreSQL schema
├── tests/
│   └── test_models.py       # Unit tests
├── main.py                  # FastAPI application
├── requirements.txt
├── .env.example
└── README.md
```

## Configuration

All configuration is managed through environment variables. See `.env.example` for all available options.

### Required Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
| `SMARTCAR_CLIENT_ID` | Smartcar OAuth client ID |
| `SMARTCAR_CLIENT_SECRET` | Smartcar OAuth client secret |
| `SMARTCAR_REDIRECT_URI` | OAuth callback URL |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/public key |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | - | Anthropic API key |
| `DEFAULT_LLM_PROVIDER` | `openai` | Default LLM provider |
| `ENVIRONMENT` | `development` | App environment |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PORT` | `8000` | Server port |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info and status |
| `/health` | GET | Health check |
| `/callback` | GET | Smartcar OAuth callback |
| `/auth/smartcar` | GET | Generate auth URL |

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Style

The project follows PEP 8 and uses functional programming patterns:
- Pure functions with no side effects
- Immutable data models (Pydantic)
- Function composition with pipe/compose
- Decorator patterns for cross-cutting concerns

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions for Railway and other platforms.

### Quick Railway Deploy

1. Push to GitHub
2. Connect repo to Railway
3. Add environment variables
4. Deploy

## Security

- All OAuth tokens are stored securely in Supabase
- Row Level Security (RLS) policies protect user data
- Tokens are automatically refreshed when expired
- No sensitive data is logged

## License

MIT

## Support

For issues and feature requests, please open a GitHub issue.
