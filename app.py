#!/usr/bin/env python3
"""
Time-lapse video recorder from RTSP stream using ffmpeg.
Records directly to video format instead of individual frames.
Periodically creates daily video files.
"""

import os
import time
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
import threading
import signal
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
RTSP_URL = os.getenv('RTSP_URL', 'rtsp://example.com/stream')
OUTPUT_DIR = os.getenv('OUTPUT_DIR', '/videos')
CYCLE_TIME = int(os.getenv('CYCLE_TIME', '60'))  # seconds between frames
VIDEO_FPS = int(os.getenv('VIDEO_FPS', '24'))  # output video FPS
VIDEO_QUALITY = os.getenv('VIDEO_QUALITY', '23')  # CRF value (18-28, lower = better)
VIDEO_DURATION_HOURS = int(os.getenv('VIDEO_DURATION_HOURS', '24'))  # hours per video file
KEEP_TEMP_FRAMES = os.getenv('KEEP_TEMP_FRAMES', 'false').lower() == 'true'  # Keep temp frames after video creation

# Calculate frames needed for one video
FRAMES_PER_VIDEO = int((VIDEO_DURATION_HOURS * 3600) / CYCLE_TIME)

# Global variable for graceful shutdown
recording_process = None
should_stop = False

def ensure_output_dir():
    """Create output directories if they don't exist."""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(OUTPUT_DIR, 'temp_frames')).mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {OUTPUT_DIR}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global should_stop, recording_process
    logger.info("Received shutdown signal, stopping gracefully...")
    should_stop = True
    if recording_process:
        recording_process.terminate()
        try:
            recording_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            recording_process.kill()
    sys.exit(0)


def capture_frame_to_file(output_file, preload_time=10):
    """
    Capture a single frame from RTSP stream and save to file.
    """
    try:
        cmd = [
            'ffmpeg',
            '-rtsp_transport', 'tcp',
            '-i', RTSP_URL,
            '-ss', str(preload_time),
            '-frames:v', '1',
            '-q:v', '2',
            '-y',
            output_file
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=preload_time + 30
        )
        
        return result.returncode == 0
    
    except Exception as e:
        logger.error(f"Error capturing frame: {e}")
        return False


def create_video_from_frames(frames_dir, output_video, fps=24, delete_frames=True):
    """
    Create a video from a directory of sequential frames.
    """
    logger.info(f"Creating video: {output_video}")
    
    try:
        # Get list of frame files sorted by name
        frame_files = sorted(Path(frames_dir).glob('frame_*.jpg'))
        
        if len(frame_files) == 0:
            logger.warning(f"No frames found in {frames_dir}")
            return False
        
        logger.info(f"Compiling {len(frame_files)} frames into video at {fps} fps")
        
        # Create a temporary file list for ffmpeg
        frames_list_file = os.path.join(frames_dir, 'frames_list.txt')
        with open(frames_list_file, 'w') as f:
            for frame_file in frame_files:
                # Calculate duration for each frame to match desired playback speed
                duration = 1.0 / fps
                f.write(f"file '{frame_file.name}'\n")
                f.write(f"duration {duration}\n")
            # Add last frame again (ffmpeg requirement)
            if frame_files:
                f.write(f"file '{frame_files[-1].name}'\n")
        
        # Create video using ffmpeg
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', frames_list_file,
            '-vsync', 'vfr',
            '-pix_fmt', 'yuv420p',
            '-c:v', 'libx264',
            '-crf', VIDEO_QUALITY,
            '-preset', 'medium',
            '-y',
            output_video
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=frames_dir,
            timeout=600  # 10 minute timeout for video creation
        )
        
        # Clean up frames list file
        os.remove(frames_list_file)
        
        if result.returncode == 0:
            logger.info(f"✓ Video created successfully: {output_video}")
            
            # Delete frames if requested
            if delete_frames and not KEEP_TEMP_FRAMES:
                logger.info("Cleaning up temporary frames...")
                for frame_file in frame_files:
                    try:
                        frame_file.unlink()
                    except Exception as e:
                        logger.warning(f"Could not delete {frame_file}: {e}")
            
            return True
        else:
            error_msg = result.stderr.decode('utf-8', errors='ignore')
            logger.error(f"Failed to create video: {error_msg[-500:]}")
            return False
    
    except Exception as e:
        logger.error(f"Error creating video: {e}")
        return False


def record_timelapse():
    """
    Main recording loop that captures frames at specified intervals
    and compiles them into video files.
    """
    global should_stop
    
    frame_count = 0
    video_count = 1
    temp_frames_dir = os.path.join(OUTPUT_DIR, 'temp_frames')
    video_start_time = datetime.now()
    
    logger.info(f"Starting time-lapse recording...")
    logger.info(f"Capturing 1 frame every {CYCLE_TIME} seconds")
    logger.info(f"Creating {VIDEO_DURATION_HOURS}h video files at {VIDEO_FPS} fps")
    logger.info(f"Each video will contain {FRAMES_PER_VIDEO} frames")
    
    while not should_stop:
        try:
            # Capture frame
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            frame_filename = f"frame_{frame_count:06d}_{timestamp}.jpg"
            frame_path = os.path.join(temp_frames_dir, frame_filename)
            
            logger.info(f"[{frame_count + 1}/{FRAMES_PER_VIDEO}] Capturing frame...")
            
            if capture_frame_to_file(frame_path):
                frame_count += 1
                logger.info(f"✓ Frame saved: {frame_filename}")
            else:
                logger.error("✗ Failed to capture frame, will retry...")
            
            # Check if we've collected enough frames for a video
            if frame_count >= FRAMES_PER_VIDEO:
                video_filename = f"timelapse_{video_start_time.strftime('%Y%m%d_%H%M%S')}.mp4"
                video_path = os.path.join(OUTPUT_DIR, video_filename)
                
                logger.info(f"Reached {frame_count} frames, creating video file...")
                
                if create_video_from_frames(temp_frames_dir, video_path, VIDEO_FPS, delete_frames=True):
                    logger.info(f"✓ Video #{video_count} completed: {video_filename}")
                    video_count += 1
                    frame_count = 0
                    video_start_time = datetime.now()
                else:
                    logger.error("Failed to create video, keeping frames and continuing...")
            
            # Wait for next cycle
            if not should_stop:
                logger.info(f"Waiting {CYCLE_TIME} seconds until next frame...")
                time.sleep(CYCLE_TIME)
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal...")
            break
        except Exception as e:
            logger.error(f"Error in recording loop: {e}")
            logger.info("Retrying in 30 seconds...")
            time.sleep(30)
    
    # Create final video from remaining frames on shutdown
    if frame_count > 0:
        logger.info(f"Creating final video from {frame_count} remaining frames...")
        video_filename = f"timelapse_{video_start_time.strftime('%Y%m%d_%H%M%S')}_partial.mp4"
        video_path = os.path.join(OUTPUT_DIR, video_filename)
        create_video_from_frames(temp_frames_dir, video_path, VIDEO_FPS, delete_frames=True)

def main():
    """Main entry point for time-lapse recording."""
    global should_stop
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=== Time-lapse Video Recorder ===")
    logger.info(f"RTSP URL: {RTSP_URL}")
    logger.info(f"Frame interval: {CYCLE_TIME}s")
    logger.info(f"Video FPS: {VIDEO_FPS}")
    logger.info(f"Video quality (CRF): {VIDEO_QUALITY}")
    logger.info(f"Video duration: {VIDEO_DURATION_HOURS}h per file")
    logger.info(f"Keep temp frames: {KEEP_TEMP_FRAMES}")
    
    ensure_output_dir()
    
    # Calculate video statistics
    frames_per_day = (24 * 60 * 60) / CYCLE_TIME
    videos_per_day = frames_per_day / FRAMES_PER_VIDEO
    video_length_seconds = FRAMES_PER_VIDEO / VIDEO_FPS
    
    logger.info(f"📊 Statistics:")
    logger.info(f"  - Frames captured per day: ~{frames_per_day:.0f}")
    logger.info(f"  - Videos created per day: ~{videos_per_day:.1f}")
    logger.info(f"  - Each video length: ~{video_length_seconds:.0f}s ({video_length_seconds/60:.1f} min)")
    logger.info(f"  - Time compression: {VIDEO_DURATION_HOURS}h → {video_length_seconds/60:.1f}min")
    logger.info("=" * 60)
    
    # Start recording
    record_timelapse()
    
    logger.info("Shutdown complete.")

if __name__ == "__main__":
    main()
