# Smartness Levels Implementation Summary

## Overview
This implementation adds configurable smartness levels for employees, allowing you to choose between high-performance models for complex tasks and efficient models for code writing.

## Key Features

### 1. Two Configurable Smartness Levels
- **Smart**: High-performance model for complex planning and analysis (default: `openrouter/google/gemini-2.5-pro`)
- **Normal**: Efficient model for code writing and execution (default: `openrouter/qwen/qwen3-coder`)

### 2. Configuration Management
- Models are stored in `models_config.json`
- Can be updated via CLI: `model-set <level> <model_name>`
- Supports all OpenRouter and OpenAI models

### 3. Employee Hiring with Smartness Level
- When hiring: `hire <name> <role> [smartness]`
- Smartness defaults to "normal" if not specified
- Stored in database with each employee

### 4. Automatic Model Selection
- Sessions automatically use employee's configured smartness level
- Can still override per-task with specific model parameter

## Database Changes
- Added `smartness` column to `employees` table
- Column defaults to "normal" for backward compatibility

## CLI Commands Added
- `models` - Show configured models
- `model-set <level> <model_name>` - Update model for smartness level
- Extended `hire` command to accept smartness parameter

## Usage Examples

### Hiring Employees
```
hire sarah developer smart      # Hire smart developer
hire john developer             # Hire normal developer (default)
```

### Configuring Models
```
models                          # Show current model configuration
model-set smart openrouter/anthropic/claude-3.5-sonnet  # Set smart model
model-set normal openai/gpt-3.5-turbo                  # Set normal model
```

### Assigning Tasks
```
assign sarah 'implement user authentication'  # Uses smart model
assign john 'fix login bug' claude-3.5        # Override with specific model
```

## Benefits
1. **Cost Optimization**: Use expensive models only when needed
2. **Performance**: Get appropriate intelligence level for each task
3. **Flexibility**: Easy configuration via CLI
4. **Backward Compatibility**: Existing commands work unchanged