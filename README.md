# OpenCode Async Agents

## About

A general-purpose developer tool for managing asynchronous agent workflows. **No customer data, proprietary prompts, or core product logic.** This is an open-source framework for building and orchestrating AI-powered development agents.

## Features

- Asynchronous agent management and orchestration
- WebSocket-based real-time communication
- Secure authentication and authorization
- Performance monitoring and metrics
- Extensible plugin architecture
- CLI and web interfaces

## Install

1. Clone the repository:
```bash
git clone https://github.com/stanley-marketing/opencode-async-agents.git
cd opencode-async-agents
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

## Configure

Create `.env` from `.env.example`. Do not commit secrets.

Required configuration:
- `JWT_SECRET`: JWT signing secret
- `DATABASE_URL`: Database connection string
- `WEBSOCKET_HOST`: WebSocket server host
- `WEBSOCKET_PORT`: WebSocket server port

## Usage

### Start the server:
```bash
python src/server.py
```

### Run with Docker:
```bash
docker-compose up
```

### CLI usage:
```bash
python src/cli_server.py --help
```

### WebSocket connection:
```python
import asyncio
import websockets

async def connect():
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello, agent!")
        response = await websocket.recv()
        print(response)

asyncio.run(connect())
```

## Safety & Privacy

Do not upload PII or confidential data. See SECURITY.md for vulnerability reporting.

## Development

### Running Tests
```bash
pytest tests/
```

### Linting
```bash
python -m flake8 src/
```

### Performance Testing
```bash
./scripts/run_performance_tests.sh
```

## Architecture

- **Agent Management**: Asynchronous task distribution and execution
- **Communication**: WebSocket-based real-time messaging
- **Security**: JWT authentication, rate limiting, audit logging
- **Monitoring**: Performance metrics and health checks
- **Storage**: SQLite/PostgreSQL support

## License

MIT. See LICENSE and NOTICE.

## Contributing

See CONTRIBUTING.md for development guidelines.