import os
import json
from pathlib import Path
from typing import Dict, Any

class ModelsConfig:
    """Configuration for AI models used by employees"""
    
    # Default model configurations
    DEFAULT_MODELS = {
        "smart": {
            "name": "openrouter/google/gemini-2.5-pro",
            "description": "High-performance model for complex planning and analysis",
            "cost_level": "high"
        },
        "normal": {
            "name": "openrouter/qwen/qwen3-coder",
            "description": "Efficient model for code writing and execution",
            "cost_level": "low"
        }
    }
    
    # Supported providers and models
    SUPPORTED_MODELS = {
        "openrouter": [
            "google/gemini-2.5-pro",
            "google/gemini-pro",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-opus",
            "meta-llama/llama-3.1-405b",
            "qwen/qwen3-coder",
            "mistralai/mistral-large"
        ],
        "openai": [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4o",
            "gpt-3.5-turbo"
        ]
    }
    
    def __init__(self, config_path: str = "models_config.json"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from file or use defaults"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading model config: {e}. Using defaults.")
                return self.DEFAULT_MODELS
        else:
            # Create default config file
            self._save_config(self.DEFAULT_MODELS)
            return self.DEFAULT_MODELS
    
    def _save_config(self, config: Dict[str, Any]):
        """Save configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving model config: {e}")
    
    def get_model_for_level(self, level: str) -> str:
        """Get model name for a given smartness level"""
        return self.config.get(level, {}).get("name", self.DEFAULT_MODELS.get(level, {}).get("name"))
    
    def get_all_models(self) -> Dict[str, Any]:
        """Get all configured models"""
        return self.config
    
    def update_model(self, level: str, model_name: str, description: str = "", cost_level: str = "medium"):
        """Update model configuration for a specific level"""
        self.config[level] = {
            "name": model_name,
            "description": description or self.config.get(level, {}).get("description", ""),
            "cost_level": cost_level
        }
        self._save_config(self.config)
    
    def is_supported_model(self, model_name: str) -> bool:
        """Check if a model is supported"""
        for provider, models in self.SUPPORTED_MODELS.items():
            for model in models:
                if model_name.endswith(model):
                    return True
        return False

# Global instance
models_config = ModelsConfig()