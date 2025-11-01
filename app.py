#!/usr/bin/env python3
"""
Time-lapse screenshot capture from RTSP stream using ffmpeg.
Captures one screenshot per minute, where 1 day = 1 minute of recording.
"""

import os
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
RTSP_URL = os.getenv('RTSP_URL', 'rtsp://example.com/stream')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/screenshots')
PRELOAD_TIME = int(os.getenv('PRELOAD_TIME', '60'))  # seconds to preload stream
SLEEP_TIME = int(os.getenv('SLEEP_TIME', '60'))  # seconds between screenshots (1 minute)
IMAGE_WIDTH = int(os.getenv('IMAGE_WIDTH', '1920'))
IMAGE_HEIGHT = int(os.getenv('IMAGE_HEIGHT', '1080'))

def ensure_output_dir():
    """Create output directory if it doesn't exist."""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {OUTPUT_DIR}")

def capture_screenshot():
    """
    Capture a screenshot from the RTSP stream using ffmpeg.
    Preloads the stream for stability before capturing.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"screenshot_{timestamp}.png")
    
    logger.info(f"Connecting to RTSP stream: {RTSP_URL}")
    
    try:
        # ffmpeg command to capture a single frame after preloading
        # -rtsp_transport tcp: Use TCP for RTSP (more reliable, change to udp if needed)
        # -i: Input stream URL
        # -ss: Seek to position (preload time)
        # -frames:v 1: Capture only 1 frame
        # -s: Set output resolution
        # -q:v 2: High quality (2-5 is good, lower is better)
        cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',  # Use TCP for RTSP
            '-i', RTSP_URL,
            '-ss', str(PRELOAD_TIME),  # Preload for stability
            '-frames:v', '1',  # Capture single frame
            '-s', f'{IMAGE_WIDTH}x{IMAGE_HEIGHT}',  # Output resolution
            '-q:v', '2',  # High quality
            '-y',  # Overwrite output file
            output_file
        ]
        
        logger.info(f"Capturing screenshot (preload: {PRELOAD_TIME}s)...")
        
        # Run ffmpeg command
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=PRELOAD_TIME + 30  # Add buffer to timeout
        )
        
        if result.returncode == 0:
            logger.info(f"✓ Screenshot saved: {output_file}")
        else:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            logger.error(f"✗ ffmpeg failed (exit code {result.returncode})")
            logger.error(f"Error: {error_msg[-500:]}")  # Last 500 chars of error
    
    except subprocess.TimeoutExpired:
        logger.error(f"✗ Timeout capturing screenshot after {PRELOAD_TIME + 30}s")
    except FileNotFoundError:
        logger.error("✗ ffmpeg not found! Please install ffmpeg.")
    except Exception as e:
        logger.error(f"✗ Error during capture: {e}")

def main():
    """Main loop for continuous screenshot capture."""
    logger.info("=== Time-lapse Screenshot Capture Service ===")
    logger.info(f"RTSP URL: {RTSP_URL}")
    logger.info(f"Preload time: {PRELOAD_TIME}s")
    logger.info(f"Sleep time between captures: {SLEEP_TIME}s")
    logger.info(f"Output resolution: {IMAGE_WIDTH}x{IMAGE_HEIGHT}")
    
    ensure_output_dir()
    
    # Calculate total cycle time
    cycle_time = PRELOAD_TIME + SLEEP_TIME
    logger.info(f"Total cycle time: {cycle_time}s per screenshot")
    logger.info(f"Time-lapse ratio: 1 day = ~{1440/SLEEP_TIME:.1f} screenshots")
    
    while True:
        try:
            capture_screenshot()
            logger.info(f"Sleeping for {SLEEP_TIME} seconds...")
            time.sleep(SLEEP_TIME)
        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.info(f"Retrying in {SLEEP_TIME} seconds...")
            time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    main()
