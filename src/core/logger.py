import logging
import sys
from pathlib import Path

def setup_logging(level=logging.INFO):
    """Configura o sistema de logging para o AlcivinyEdger."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Garantir que o diretório de logs exista
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_dir / "system.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("AlcivinyEdger")

class BaseModule:
    """Classe base para todos os módulos do sistema para garantir contratos consistentes."""
    def __init__(self, name: str):
        self.logger = logging.getLogger(f"AlcivinyEdger.{name}")
        self.logger.info(f"Módulo {name} inicializado.")
