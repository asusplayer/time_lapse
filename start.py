#!/usr/bin/env python3
"""
Smart startup script that:
1. Checks for existing PNG/JPG frames
2. Runs migration if frames found
3. Starts video recording mode
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/videos')
AUTO_MIGRATE = os.getenv('AUTO_MIGRATE', 'true').lower() == 'true'
DELETE_OLD_FRAMES = os.getenv('DELETE_OLD_FRAMES', 'true').lower() == 'true'


def check_for_old_frames():
    """Check if there are old PNG/JPG frames that need migration."""
    output_path = Path(OUTPUT_DIR)
    
    # Look for screenshot frames (old naming pattern)
    old_frames = []
    patterns = ['screenshot_*.png', 'screenshot_*.jpg', 'frame_*.png', 'frame_*.jpg']
    
    for pattern in patterns:
        old_frames.extend(output_path.glob(pattern))
    
    # Filter out files in temp directories
    old_frames = [f for f in old_frames if 'temp' not in str(f) and f.is_file()]
    
    return old_frames


def run_migration():
    """Run the migration script to convert old frames to videos."""
    logger.info("=" * 60)
    logger.info("🔄 OLD FRAMES DETECTED - STARTING MIGRATION")
    logger.info("=" * 60)
    
    # Set environment variables for migration
    os.environ['FRAMES_DIR'] = OUTPUT_DIR
    os.environ['DELETE_FRAMES_AFTER'] = 'true' if DELETE_OLD_FRAMES else 'false'
    
    # Import and run migration
    try:
        import migrate_frames
        migrate_frames.main()
        logger.info("✓ Migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"✗ Migration failed: {e}")
        logger.warning("Continuing with video recording mode anyway...")
        return False


def start_video_recording():
    """Start the main video recording application."""
    logger.info("=" * 60)
    logger.info("🎥 STARTING VIDEO RECORDING MODE")
    logger.info("=" * 60)
    
    # Import and run main app
    import app
    app.main()


def main():
    """Main startup logic."""
    logger.info("=" * 60)
    logger.info("🚀 TIME-LAPSE SERVICE STARTING")
    logger.info("=" * 60)
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Auto-migration: {AUTO_MIGRATE}")
    logger.info(f"Delete old frames: {DELETE_OLD_FRAMES}")
    logger.info("=" * 60)
    
    # Check for old frames
    if AUTO_MIGRATE:
        old_frames = check_for_old_frames()
        
        if old_frames:
            logger.info(f"Found {len(old_frames)} old frames to migrate")
            
            # Ask user confirmation (but auto-proceed after 10 seconds in container)
            if os.getenv('SKIP_MIGRATION_CONFIRM', 'true').lower() == 'true':
                logger.info("Auto-confirming migration in container mode...")
                run_migration()
            else:
                logger.info("Starting migration in 10 seconds (Ctrl+C to cancel)...")
                import time
                try:
                    time.sleep(10)
                    run_migration()
                except KeyboardInterrupt:
                    logger.info("Migration cancelled by user")
        else:
            logger.info("No old frames found, starting fresh")
    else:
        logger.info("Auto-migration disabled, skipping check")
    
    # Start main video recording
    start_video_recording()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
