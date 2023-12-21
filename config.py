# config.py
import json

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

API_TOKEN = config['API_TOKEN']
ADMIN_PASSWORD = config['ADMIN_PASSWORD']
CSV_FILE = config['CSV_FILE']
IMAGE_DIR = config['IMAGE_DIR']
USER_STATS_FILE = config['USER_STATS_FILE']
USER_IDS_FILE = config['USER_IDS_FILE']
ADMIN_USER_IDS = config['ADMIN_USER_IDS']
