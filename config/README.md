# OpenCode-Slack Configuration Guide

This directory contains all configuration files for the OpenCode-Slack Agent Orchestration System. The configuration is organized into logical sections for easy management and deployment.

## 📁 Directory Structure

```
config/
├── README.md                    # This documentation file
├── config.yaml                  # Master configuration file
├── config_loader.py            # Configuration loading utilities
├── validate_config.py          # Configuration validation script
├── manage_config.py            # Configuration management utilities
├── models.json                 # AI model configurations
├── performance.json            # Performance optimization settings
├── environments/               # Environment-specific configurations
│   ├── .env.template          # Template for new environments
│   ├── .env.development       # Development environment
│   ├── .env.production        # Production environment
│   └── .env.staging           # Staging environment (optional)
├── deployment/                # Deployment configurations
│   ├── docker-compose.yml     # Docker Compose configuration
│   ├── Dockerfile             # Docker container configuration
│   └── nginx.conf             # Nginx reverse proxy configuration
├── monitoring/                # Monitoring configurations
│   └── prometheus.yml         # Prometheus monitoring configuration
└── security/                  # Security configurations
    └── security.yaml          # Security policies and settings
```

## 🚀 Quick Start

### 1. Initial Setup

1. **Copy the environment template:**
   ```bash
   cp config/environments/.env.template config/environments/.env.development
   ```

2. **Generate secure secrets:**
   ```bash
   python config/manage_config.py generate-secrets development
   ```

3. **Configure external services:**
   Edit `config/environments/.env.development` and set:
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `OPENAI_API_KEY`
   - `SLACK_SIGNING_SECRET`
   - `SLACK_BOT_TOKEN`

4. **Validate configuration:**
   ```bash
   python config/validate_config.py
   ```

### 2. Environment Management

**Create a new environment:**
```bash
python config/manage_config.py create-env staging --copy-from development
```

**List available environments:**
```bash
python config/manage_config.py list-envs
```

**Validate an environment:**
```bash
python config/manage_config.py validate-env production
```

## 📋 Configuration Files

### Master Configuration (`config.yaml`)

The master configuration file defines the structure and default values for all configuration options. It uses environment variable substitution in the format `${VARIABLE_NAME:-default_value}`.

**Key sections:**
- `app`: Application metadata
- `server`: Server configuration
- `database`: Database settings
- `security`: Security configuration
- `services`: External service configurations
- `monitoring`: Monitoring and alerting
- `performance`: Performance optimization

### Environment Files (`environments/.env.*`)

Environment-specific configuration files contain actual values for environment variables. These files should **never be committed to version control** with real secrets.

**Required variables:**
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Telegram chat ID
- `OPENAI_API_KEY`: OpenAI API key
- `SECRET_KEY`: Application secret key (32+ characters)
- `ENCRYPTION_KEY`: Data encryption key (32 bytes, base64 encoded)

**Environment-specific settings:**
- **Development**: Debug mode enabled, local paths, verbose logging
- **Production**: Security hardened, absolute paths, minimal logging
- **Staging**: Production-like with test data

### Models Configuration (`models.json`)

Defines AI model configurations for different use cases:

```json
{
  "smart": {
    "name": "openrouter/google/gemini-2.5-pro",
    "description": "High-performance model for complex tasks",
    "cost_level": "high"
  },
  "normal": {
    "name": "openrouter/qwen/qwen3-coder",
    "description": "Efficient model for routine tasks",
    "cost_level": "low"
  }
}
```

### Performance Configuration (`performance.json`)

Optimizes system performance with settings for:
- Database connections and caching
- Async processing limits
- Rate limiting
- Connection pooling
- Batch operations

### Security Configuration (`security/security.yaml`)

Comprehensive security settings including:
- Authentication policies
- API security (rate limiting, CORS)
- Encryption settings
- Network security (TLS, headers)
- File security
- Input validation
- Compliance settings

## 🔧 Configuration Loading

The configuration system uses a hierarchical loading approach:

1. **Load environment file** (`.env.{environment}`)
2. **Load master configuration** (`config.yaml`)
3. **Load additional configs** (`models.json`, `performance.json`)
4. **Substitute environment variables**
5. **Validate configuration**

### Using the Configuration Loader

```python
from config.config_loader import get_config, get_config_loader

# Get configuration loader
loader = get_config_loader('production')

# Get specific configuration sections
server_config = loader.get_server_config()
db_config = loader.get_database_config()

# Get individual values
api_key = get_config('services.openai.api_key')
debug_mode = get_config('server.debug_mode', False)
```

## 🛡️ Security Best Practices

### 1. Environment Variables

- **Never commit** `.env.*` files with real secrets
- Use **strong, unique secrets** for each environment
- **Rotate secrets** regularly (recommended: every 90 days)
- Use **environment variables** or secret management systems in production

### 2. File Permissions

Set secure permissions on configuration files:
```bash
python config/manage_config.py set-permissions
```

This sets:
- `600` (owner read/write only) on environment files
- `644` (owner read/write, others read) on other config files

### 3. Secret Generation

Generate cryptographically secure secrets:
```bash
python config/manage_config.py generate-secrets production
```

### 4. Configuration Validation

Always validate configuration before deployment:
```bash
python config/validate_config.py --config-dir config
```

## 🚀 Deployment

### Development Deployment

```bash
# Load development environment
export ENVIRONMENT=development

# Start with Docker Compose
docker-compose --profile dev up -d
```

### Production Deployment

```bash
# Load production environment
export ENVIRONMENT=production

# Start with Docker Compose
docker-compose --profile prod up -d
```

### Environment Variables in Production

For production deployments, consider using:
- **Docker secrets**
- **Kubernetes secrets**
- **Cloud provider secret managers** (AWS Secrets Manager, Azure Key Vault, etc.)
- **HashiCorp Vault**

## 📊 Monitoring Configuration

### Prometheus Monitoring

The system includes Prometheus monitoring configuration:
- **Metrics collection** from application endpoints
- **Health checks** and alerting
- **Performance monitoring**
- **Custom dashboards** with Grafana

### Alerting

Configure alerting through multiple channels:
- **Email alerts** for critical issues
- **Slack notifications** for team communication
- **Webhook alerts** for custom integrations

## 🔍 Troubleshooting

### Common Issues

1. **Missing environment variables:**
   ```bash
   python config/validate_config.py
   ```

2. **Invalid configuration syntax:**
   ```bash
   python config/validate_config.py --json
   ```

3. **Permission errors:**
   ```bash
   python config/manage_config.py set-permissions
   ```

4. **Secret generation:**
   ```bash
   python config/manage_config.py generate-secrets <environment>
   ```

### Validation Errors

The validation script checks for:
- **Syntax errors** in YAML/JSON files
- **Missing required variables**
- **Insecure configurations**
- **File permission issues**
- **Exposed sensitive data**

### Debug Mode

Enable debug mode for troubleshooting:
```bash
export DEBUG_MODE=true
export LOG_LEVEL=DEBUG
```

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Nginx Configuration Guide](https://nginx.org/en/docs/)
- [Prometheus Configuration](https://prometheus.io/docs/prometheus/latest/configuration/configuration/)
- [Security Best Practices](../docs/SECURITY_IMPLEMENTATION.md)

## 🤝 Contributing

When adding new configuration options:

1. **Update the master config** (`config.yaml`)
2. **Add environment variable** to templates
3. **Update documentation**
4. **Add validation rules**
5. **Test with all environments**

## 📞 Support

For configuration issues:
1. Check this documentation
2. Run validation scripts
3. Review logs for specific errors
4. Consult the main project documentation