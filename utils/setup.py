import logging
import json
import os
from pathlib import Path
from typing import Dict, Any

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('jagerbot.log', encoding='utf-8'),
            logging.StreamHandler(stream=open(os.devnull, 'w')
)
        ]
    )

def load_data() -> Dict[str, Any]:
    data = {}
    data_dir = Path('data')
    
    try:
        if (data_dir / 'planes.json').exists():
            with open(data_dir / 'planes.json', 'r', encoding='utf-8') as f:
                data['planes'] = json.load(f)
                
        if (data_dir / 'alerts.json').exists():
            with open(data_dir / 'alerts.json', 'r', encoding='utf-8') as f:
                data['alerts'] = json.load(f)
                
        if (data_dir / 'trivia_scores.json').exists():
            with open(data_dir / 'trivia_scores.json', 'r', encoding='utf-8') as f:
                data['trivia_scores'] = json.load(f)
    
    except Exception as e:
        logging.error(f"Error loading data: {e}")
        
    return data