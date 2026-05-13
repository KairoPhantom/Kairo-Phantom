import logging
import sys
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("W3_Test")

# Add scripts directory to path
sys.path.append(r"c:\Users\SANDIP\Desktop\Memory\KairoPhantom\scripts\win")

import scenario_word

# Ensure tests dir exists
os.makedirs(r"C:\tests", exist_ok=True)

# Run W3
logger.info("Starting W3 Standalone Test")
success, message = scenario_word.run_word_scenario("W3", logger)

logger.info(f"Test Finished. Success: {success}")
logger.info(f"Message: {message}")
