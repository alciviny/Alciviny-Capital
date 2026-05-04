import sys
import os

# Adiciona a raiz do projeto ao PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.logger import setup_logging
from src.data.manager import DataManager

def main():
    setup_logging()
    dm = DataManager()
    dm.sync_from_config()

if __name__ == "__main__":
    main()
