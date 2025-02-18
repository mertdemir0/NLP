import os
import yaml
from typing import Dict, Any

class Config:
    """Configuration manager for the NLP system."""
    
    def __init__(self, config_dir: str = None):
        """Initialize configuration manager.
        
        Args:
            config_dir (str, optional): Path to config directory. Defaults to project's config dir.
        """
        if config_dir is None:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config')
        
        self.config_dir = config_dir
        self.config = {}
        self._load_configs()
    
    def _load_configs(self):
        """Load all YAML configuration files from the config directory."""
        for filename in os.listdir(self.config_dir):
            if filename.endswith(('.yml', '.yaml')):
                filepath = os.path.join(self.config_dir, filename)
                config_name = os.path.splitext(filename)[0]
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.config[config_name] = yaml.safe_load(f)
    
    def get_bloomberg_config(self) -> Dict[str, Any]:
        """Get Bloomberg API configuration.
        
        Returns:
            Dict[str, Any]: Bloomberg configuration parameters
        """
        return self.config.get('bloomberg_config', {})
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration parameters.
        
        Returns:
            Dict[str, Any]: Model configuration parameters
        """
        return self.config.get('model_config', {})
    
    def get_italian_financial_terms(self) -> Dict[str, Any]:
        """Get Italian financial terms mapping.
        
        Returns:
            Dict[str, Any]: Italian financial terms and their translations
        """
        return self.config.get('italian_financial_terms', {})
    
    def get_report_periods(self) -> Dict[str, Any]:
        """Get report period configurations.
        
        Returns:
            Dict[str, Any]: Report period settings
        """
        return self.config.get('report_periods', {})
    
    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Get all configuration parameters.
        
        Returns:
            Dict[str, Dict[str, Any]]: All configuration parameters
        """
        return self.config
    
    def get_config(self, config_name: str) -> Dict[str, Any]:
        """Get configuration by name.
        
        Args:
            config_name (str): Name of the configuration file (without extension)
            
        Returns:
            Dict[str, Any]: Configuration parameters
        """
        return self.config.get(config_name, {})