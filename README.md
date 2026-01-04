# Sherlock Account Analysis - Production-Ready Multi-Agent System

A production-ready AI-powered financial analysis platform with streaming responses, conversation memory, data visualization, and multi-agent orchestration.

## Features

### ✅ Implemented Features

1. **Streaming Responses**: Real-time streaming of AI responses via WebSocket
2. **LLM-Powered Formatting**: GPT-4o handles all response formatting naturally
3. **Conversation Memory**: Redis-backed persistent conversation history
4. **Multi-Agent System**: Specialized agents for different analysis types
   - Data Analysis Agent
   - Visualization Agent
   - Insight Generation Agent
   - Report Generation Agent
5. **Data Visualization**: Automatic chart generation (bar, pie, line, tables)
6. **Production-Ready Architecture**: Error handling, logging, caching, rate limiting

## Architecture

```
sherlock-app/
├── app.py                      # Main application
├── config.py                   # Configuration management
├── requirements.txt
├── .env
├── agents/
│   ├── agent_orchestrator.py  # Multi-agent orchestration
│   ├── data_agent.py          # Data analysis
│   ├── visualization_agent.py # Chart generation
│   ├── insight_agent.py       # Business insights
│   └── report_agent.py        # Report generation
├── services/
│   └── conversation_service.py # Conversation memory
├── tools/
│   └── data_tools.py          # Data querying tools
├── utils/
│   └── logger.py              # Logging utilities
├── data/
│   └── domestic_accounts.xlsx # Your data file
└── logs/
    └── app.log
```

## Installation

### Prerequisites

- Python 3.9+
- Node.js 16+ (for React frontend)
- Redis (optional, for production)
- OpenAI API key

### Backend Setup

1. **Clone and setup environment**:
```bash
# Create project directory
mkdir sherlock-app && cd sherlock-app

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

2. **Configuration**:
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env  # or your preferred editor
```

3. **Prepare your data**:
```bash
# Create data directory
mkdir -p data

# Copy your domestic accounts Excel file
cp /path/to/your/domestic_accounts.xlsx data/
```

4. **Start the server**:
```bash
python app.py
```

Server will start on `http://localhost:8080`

### Frontend Setup

The React component provided is a self-contained artifact. To use it:

1. Create a new React app or use existing one
2. Install dependencies:
```bash
npm install lucide-react recharts
```

3. Copy the React component code
4. Update the WebSocket and API URLs if needed

## Usage

### API Endpoints

#### WebSocket (Streaming)
```
ws://localhost:8080/ws/chat
```

**Message Format**:
```json
{
  "message": "Show me accounts with overdraft > $1M",
  "conversation_id": "optional-uuid",
  "user_id": "user_123",
  "metadata": {}
}
```

#### REST API (Non-streaming)

**POST /api/chat**
```json
{
  "message": "What's the total balance by country?",
  "conversation_id": "optional",
  "user_id": "user_123"
}
```

**GET /api/conversations**
- List all conversations for a user
- Query params: `user_id`, `limit`, `offset`

**GET /api/conversations/:id**
- Get specific conversation with full history

**DELETE /api/conversations/:id**
- Delete a conversation

**GET /api/visualizations/:id**
- Get visualization data by ID

**GET /health**
- Health check endpoint

### Query Examples

Try these queries with your system:

```
- "Show me accounts with overdraft > $1M"
- "What's the total balance by country?"
- "Which accounts have overdraft tenure > 90 days?"
- "Show me the overdraft aging breakdown"
- "Top 10 accounts by balance"
- "Generate a report on high-risk accounts"
- "What insights can you provide about overdraft trends?"
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| OPENAI_API_KEY | - | Required: Your OpenAI API key |
| OPENAI_MODEL | gpt-4o | GPT model to use |
| DATA_FILE_PATH | data/domestic_accounts.xlsx | Path to your data file |
| REDIS_ENABLED | false | Enable Redis for persistence |
| LOG_LEVEL | INFO | Logging level |

### Redis Setup (Optional - Production Recommended)

For production deployments with multiple instances:

```bash
# Install Redis
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server

# Update .env
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Multi-Agent System

### Agent Routing

The orchestrator automatically routes queries to appropriate agents:

- **Data queries** → Data Agent
- **Visualization requests** → Data Agent + Visualization Agent
- **Insight questions** → Data Agent + Insight Agent
- **Report requests** → Data Agent + Report Agent

### Agent Collaboration

Agents work in sequence:
1. Data Agent retrieves and analyzes data
2. Secondary agents process the results
3. Responses are streamed in real-time

## Data Visualization

Supports automatic chart generation:

- **Bar Charts**: For comparisons and distributions
- **Pie Charts**: For proportions
- **Line Charts**: For trends over time
- **Tables**: For detailed data views

Visualizations are generated based on data patterns and user intent.

## Production Deployment

### Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "app.py"]
```

Build and run:
```bash
docker build -t sherlock-app .
docker run -p 8080:8080 --env-file .env sherlock-app
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in .env
- [ ] Enable Redis for conversation persistence
- [ ] Configure proper CORS origins
- [ ] Enable rate limiting
- [ ] Set up API key authentication
- [ ] Configure log rotation
- [ ] Set up monitoring and alerts
- [ ] Use HTTPS/WSS in production
- [ ] Set appropriate TTL values
- [ ] Back up data regularly

### Security Considerations

1. **API Keys**: Enable `API_KEY_REQUIRED=true` for production
2. **CORS**: Restrict `CORS_ORIGINS` to your frontend domain
3. **Rate Limiting**: Enable to prevent abuse
4. **Environment Variables**: Never commit `.env` to version control
5. **Data Security**: Ensure data files have proper permissions

## Monitoring

### Logs

Application logs are written to:
- Console (stdout)
- File: `logs/app.log` (rotated at 10MB)

### Health Check

```bash
curl http://localhost:8080/health
```

### Analytics

Get usage analytics:
```bash
curl "http://localhost:8080/api/analytics?user_id=user_123"
```

## Troubleshooting

### Common Issues

**WebSocket Connection Failed**
- Check if server is running on correct port
- Verify firewall settings
- Check CORS configuration

**Data File Not Found**
- Verify `DATA_FILE_PATH` in .env
- Ensure file exists and is readable
- Check file format (xlsx, csv, parquet)

**OpenAI API Errors**
- Verify API key is correct
- Check API rate limits
- Ensure sufficient credits

**Redis Connection Failed**
- Falls back to in-memory storage automatically
- Check Redis is running: `redis-cli ping`
- Verify Redis connection settings

## Development

### Running Tests

```bash
pytest tests/
```

### Adding New Agents

1. Create new agent class in `agents/`
2. Register in `agent_orchestrator.py`
3. Update routing logic
4. Add tool functions if needed

### Extending Data Tools

Add new analysis functions in `tools/data_tools.py`:
```python
def _analyze_custom(self, df: pd.DataFrame, query: str) -> Dict:
    # Your custom analysis logic
    return result
```

## Support

For issues or questions:
1. Check logs in `logs/app.log`
2. Verify configuration in `.env`
3. Test with curl or Postman
4. Review error messages carefully

## License
