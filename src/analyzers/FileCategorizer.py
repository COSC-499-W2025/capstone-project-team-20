import yaml
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any

from language_detector import LANGUAGE_MAP, MARKUP_LANGUAGE_MAP

CONFIG_DIR = Path(__file__).parent.parent / "config"
CATEGORIES_FILE = CONFIG_DIR / "categories.yml"