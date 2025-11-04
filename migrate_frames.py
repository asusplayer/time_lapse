#!/usr/bin/env python3
"""
Migration script to convert existing PNG/JPEG screenshots into time-lapse videos.
Run this once to process all existing frames before switching to the new video recording system.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
FRAMES_DIR = os.getenv('FRAMES_DIR', '/screenshots')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/videos')
VIDEO_FPS = int(os.getenv('VIDEO_FPS', '24'))
VIDEO_QUALITY = os.getenv('VIDEO_QUALITY', '23')
DELETE_FRAMES_AFTER = os.getenv('DELETE_FRAMES_AFTER', 'false').lower() == 'true'
FRAMES_PER_VIDEO = int(os.getenv('FRAMES_PER_VIDEO', '1440'))  # Default: 1 day at 1 frame/min

def get_frame_timestamp(filename):
    """Extract timestamp from filename for sorting."""
    # Try to extract timestamp from filename (format: screenshot_YYYYMMDD_HHMMSS.png)
    match = re.search(r'(\d{8}_\d{6})', filename)
    if match:
        try:
            return datetime.strptime(match.group(1), '%Y%m%d_%H%M%S')
        except:
            pass
    # Fallback to file modification time
    return None


def group_frames_by_time(frame_files, hours_per_group=24):
    """Group frames into time-based chunks."""
    groups = []
    current_group = []
    group_start_time = None
    
    for frame_file in sorted(frame_files, key=lambda f: get_frame_timestamp(f.name) or f.stat().st_mtime):
        timestamp = get_frame_timestamp(frame_file.name)
        
        if timestamp:
            if group_start_time is None:
                group_start_time = timestamp
                current_group = [frame_file]
            else:
                # Check if this frame should be in a new group
                time_diff = (timestamp - group_start_time).total_seconds() / 3600
                if time_diff >= hours_per_group or len(current_group) >= FRAMES_PER_VIDEO:
                    groups.append((group_start_time, current_group))
                    group_start_time = timestamp
                    current_group = [frame_file]
                else:
                    current_group.append(frame_file)
        else:
            # No timestamp, just add to current group
            if not current_group:
                group_start_time = datetime.fromtimestamp(frame_file.stat().st_mtime)
            current_group.append(frame_file)
            
            # Start new group if we hit the frame limit
            if len(current_group) >= FRAMES_PER_VIDEO:
                groups.append((group_start_time, current_group))
                group_start_time = None
                current_group = []
    
    # Add remaining frames as final group
    if current_group:
        groups.append((group_start_time or datetime.now(), current_group))
    
    return groups


def convert_frame_to_jpg(frame_file, temp_dir):
    """Convert PNG frame to JPG if needed, return new path."""
    if frame_file.suffix.lower() in ['.jpg', '.jpeg']:
        return frame_file
    
    # Convert PNG to JPG
    jpg_path = temp_dir / f"{frame_file.stem}.jpg"
    try:
        cmd = [
            'ffmpeg',
            '-i', str(frame_file),
            '-q:v', '2',
            '-y',
            str(jpg_path)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if result.returncode == 0:
            return jpg_path
        else:
            logger.warning(f"Failed to convert {frame_file.name}, using original")
            return frame_file
    except Exception as e:
        logger.warning(f"Error converting {frame_file.name}: {e}")
        return frame_file


def create_video_from_frames(frame_files, output_video, fps=24):
    """Create a video from a list of frame files."""
    logger.info(f"Creating video: {output_video}")
    logger.info(f"Processing {len(frame_files)} frames at {fps} fps")
    
    try:
        # Create temporary directory for JPG conversion if needed
        temp_dir = Path(FRAMES_DIR) / 'temp_conversion'
        temp_dir.mkdir(exist_ok=True)
        
        # Create frames list file
        frames_list_file = temp_dir / 'frames_list.txt'
        
        with open(frames_list_file, 'w') as f:
            for i, frame_file in enumerate(frame_files):
                # Convert to JPG if needed
                jpg_frame = convert_frame_to_jpg(frame_file, temp_dir)
                
                duration = 1.0 / fps
                f.write(f"file '{jpg_frame.absolute()}'\n")
                f.write(f"duration {duration}\n")
                
                if (i + 1) % 100 == 0:
                    logger.info(f"  Processed {i + 1}/{len(frame_files)} frames...")
            
            # Add last frame again (ffmpeg requirement)
            if frame_files:
                last_jpg = convert_frame_to_jpg(frame_files[-1], temp_dir)
                f.write(f"file '{last_jpg.absolute()}'\n")
        
        # Create video
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(frames_list_file),
            '-vsync', 'vfr',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            '-crf', VIDEO_QUALITY,
            '-preset', 'medium',
            '-y',
            output_video
        ]
        
        logger.info("Compiling video (this may take a while)...")
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1800  # 30 minute timeout
        )
        
        # Cleanup temporary files
        frames_list_file.unlink()
        for jpg_file in temp_dir.glob('*.jpg'):
            # Only delete converted files, not originals
            if jpg_file.parent == temp_dir:
                jpg_file.unlink()
        temp_dir.rmdir()
        
        if result.returncode == 0:
            logger.info(f"✓ Video created successfully: {output_video}")
            return True
        else:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            logger.error(f"Failed to create video: {error_msg[-500:]}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        return False


def main():
    """Main migration process."""
    logger.info("=== Frame Migration Tool ===")
    logger.info(f"Frames directory: {FRAMES_DIR}")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"Video FPS: {VIDEO_FPS}")
    logger.info(f"Frames per video: {FRAMES_PER_VIDEO}")
    logger.info(f"Delete frames after: {DELETE_FRAMES_AFTER}")
    logger.info("=" * 60)
    
    # Create output directory
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Find all frame files
    frames_path = Path(FRAMES_DIR)
    frame_patterns = ['screenshot_*.png', 'screenshot_*.jpg', 'frame_*.png', 'frame_*.jpg', '*.png', '*.jpg']
    
    all_frames = []
    for pattern in frame_patterns:
        all_frames.extend(frames_path.glob(pattern))
    
    # Remove duplicates and filter out already processed files
    all_frames = list(set([f for f in all_frames if f.is_file() and 'temp' not in str(f)]))
    
    if not all_frames:
        logger.warning("No frames found to migrate!")
        logger.info("Migration complete (nothing to do).")
        return
    
    logger.info(f"Found {len(all_frames)} frames to process")
    
    # Group frames by time period
    logger.info(f"Grouping frames into videos (max {FRAMES_PER_VIDEO} frames each)...")
    frame_groups = group_frames_by_time(all_frames, hours_per_group=24)
    
    logger.info(f"Created {len(frame_groups)} video groups")
    logger.info("=" * 60)
    
    # Process each group
    success_count = 0
    failed_count = 0
    
    for i, (start_time, frames) in enumerate(frame_groups, 1):
        logger.info(f"\n📹 Processing group {i}/{len(frame_groups)}")
        logger.info(f"   Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Frame count: {len(frames)}")
        
        # Create video filename
        video_filename = f"timelapse_migrated_{start_time.strftime('%Y%m%d_%H%M%S')}.mp4"
        video_path = os.path.join(OUTPUT_DIR, video_filename)
        
        if create_video_from_frames(frames, video_path, VIDEO_FPS):
            success_count += 1
            logger.info(f"✓ Video {i}/{len(frame_groups)} completed")
            
            # Delete frames if requested
            if DELETE_FRAMES_AFTER:
                logger.info("   Deleting processed frames...")
                for frame in frames:
                    try:
                        frame.unlink()
                    except Exception as e:
                        logger.warning(f"   Could not delete {frame.name}: {e}")
        else:
            failed_count += 1
            logger.error(f"✗ Video {i}/{len(frame_groups)} failed")
    
    logger.info("\n" + "=" * 60)
    logger.info("🎬 Migration Summary:")
    logger.info(f"   Total frames processed: {len(all_frames)}")
    logger.info(f"   Videos created: {success_count}/{len(frame_groups)}")
    logger.info(f"   Failed: {failed_count}")
    
    if DELETE_FRAMES_AFTER and success_count > 0:
        logger.info(f"   Original frames deleted: {DELETE_FRAMES_AFTER}")
    
    logger.info("=" * 60)
    logger.info("✓ Migration complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
