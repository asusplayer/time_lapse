# RTSP Time-lapse Video Recorder

A Docker-based service that records time-lapse videos directly from RTSP streams using ffmpeg. Records continuously and compiles frames into daily video files automatically. Optimized for minimal storage space - records 24 hours into ~50-100 MB video files.

## Features

- 🎥 **Direct video recording** - No frame storage overhead
- � **Automatic daily videos** - Creates video files for each time period
- 💾 **98% space savings** - 5 GB/day → 50-100 MB/day
- 🔄 **Continuous operation** - Records 24/7 without manual intervention
- 🐳 **Fully containerized** with Docker
- 📺 Uses ffmpeg for excellent UDP/RTSP stream handling
- 🔧 Configurable FPS, quality, and video duration
- ☁️ TrueNAS Scale compatible
- 🔄 **Migration tool** included for existing frames

## Quick Start

### 1. Configure Your Stream

Edit `docker-compose.yml` and set your RTSP stream URL:

```yaml
- RTSP_URL=rtsp://your-camera-ip:554/stream
```

### 2. Build and Run

```bash
docker-compose up -d
```

### 3. View Logs

```bash
docker-compose logs -f timelapse-capture
```

### 4. Check Videos

Videos will be saved in the `./videos` directory with timestamps:
- Format: `timelapse_YYYYMMDD_HHMMSS.mp4`
- Example: `timelapse_20251104_000000.mp4`
- Each file represents the configured duration (default: 24 hours)

**First Run:** If you have old PNG/JPG frames in the directory, they will be automatically migrated to video format and then deleted.

## Configuration

All settings can be configured via environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `RTSP_URL` | `rtsp://example.com/stream` | Your RTSP stream URL |
| `CYCLE_TIME` | `60` | Seconds between each frame capture |
| `VIDEO_FPS` | `24` | Frames per second in output video |
| `VIDEO_QUALITY` | `23` | CRF quality (18-28, lower=better, 23=default) |
| `VIDEO_DURATION_HOURS` | `24` | Real-time hours per video file |
| `KEEP_TEMP_FRAMES` | `false` | Keep temporary frames after video creation |
| `OUTPUT_DIR` | `/videos` | Output directory (inside container) |

**Note:** Actual sleep time = `CYCLE_TIME - PRELOAD_TIME` (automatically calculated)

### Time-lapse Calculation

With default settings (60-second cycle, 24 fps output):
- **24 hours** real-time = 1,440 frames captured
- **Output video** = 60 seconds (1,440 frames ÷ 24 fps)
- **File size** = ~50-100 MB (compressed H.264)

To adjust the time compression, modify `CYCLE_TIME`:
- **30 seconds** → 2,880 frames/day → 2 minutes of video
- **120 seconds** → 720 frames/day → 30 seconds of video

**Example:** For 1 day = 2 minutes of video at 24fps:
- Set `CYCLE_TIME=30` (captures 2,880 frames per day)
- Output: 2,880 frames ÷ 24 fps = 120 seconds (2 minutes)

## TrueNAS Scale Deployment

### Option 1: Using Docker Compose (Custom App)

1. Create a custom app in TrueNAS Scale
2. Clone this repository to a dataset
3. Navigate to the directory in the TrueNAS shell
4. Run: `docker-compose up -d`

### Option 2: Build and Push to Registry

1. **Build the image:**
   ```bash
   docker build -t your-registry/timelapse-capture:latest .
   ```

2. **Push to your registry:**
   ```bash
   docker push your-registry/timelapse-capture:latest
   ```

3. **Deploy in TrueNAS Scale:**
   - Use the "Launch Docker Image" option
   - Set image: `your-registry/timelapse-capture:latest`
   - Configure environment variables
   - Mount host path for videos: `/mnt/your-pool/videos` → `/videos`

## 🔄 Migrating from Frame-Based System

**Good news!** Migration is now **automatic**! 

When you deploy the new version:
1. Service detects existing PNG/JPG frames
2. Automatically converts them to videos
3. Deletes old frames after successful conversion
4. Starts normal video recording

### Migration Settings

Control migration behavior with environment variables:

```yaml
environment:
  - AUTO_MIGRATE=true         # Auto-detect and migrate old frames
  - DELETE_OLD_FRAMES=true    # Delete PNGs after migration
```

### Manual Migration

If you prefer manual control, disable auto-migration:

```yaml
- AUTO_MIGRATE=false
```

Then run migration separately:
```bash
docker-compose -f docker-compose.migrate.yml up
```

See [MIGRATION.md](MIGRATION.md) for detailed manual migration instructions.

## 📊 Storage Comparison

**Old System (PNG frames):**
- 1,440 frames/day × 3-5 MB = **~5-7 GB per day**
- 30 days = **150-210 GB** 😱

**New System (MP4 videos):**
- 1 video/day × 50-100 MB = **~50-100 MB per day**
- 30 days = **1.5-3 GB** ✨
- **98% space savings!**

### Option 3: Using TrueNAS Scale Apps

1. Go to **Apps** → **Available Applications**
2. Click **Launch Docker Image**
3. Configure:
   - **Image Repository:** Build and push your image first
   - **Environment Variables:** Set RTSP_URL, etc.
   - **Storage:** Add host path volume (`/mnt/your-pool/screenshots` → `/screenshots`)
   - **Restart Policy:** Unless Stopped

## Advanced Configuration

### Using UDP instead of TCP

Edit `app.py` line 47 and change:
```python
'-rtsp_transport', 'tcp',  # Use TCP for RTSP
```
to:
```python
'-rtsp_transport', 'udp',  # Use UDP for RTSP
```

### Network Mode

If your camera is on the same network as the Docker host, uncomment in `docker-compose.yml`:
```yaml
network_mode: host
```

### Increasing Stability

For unstable connections, increase the frame capture interval:
```yaml
- CYCLE_TIME=120  # 2 minutes between frames (slower, more stable)
```

### Improving Video Quality

For better quality videos:
```yaml
- VIDEO_QUALITY=20  # Lower = better (18-28 range)
- VIDEO_FPS=30      # Smoother playback
```

### Changing Video Duration

Create shorter video files:
```yaml
- VIDEO_DURATION_HOURS=12  # 12-hour videos instead of 24-hour
```

## Creating the Time-lapse Video

Videos are automatically created! The system continuously records and compiles frames into video files.

**To combine multiple daily videos into one:**

```bash
# Navigate to videos directory
cd videos

# Create a file list
ls timelapse_*.mp4 | sed 's/^/file /' > filelist.txt

# Combine videos
ffmpeg -f concat -safe 0 -i filelist.txt -c copy combined_timelapse.mp4

# Or re-encode with custom settings
ffmpeg -f concat -safe 0 -i filelist.txt \
  -c:v libx264 -crf 23 -preset medium combined_timelapse.mp4
```

**To adjust playback speed:**

```bash
# Speed up 2x
ffmpeg -i timelapse_20251104_000000.mp4 -filter:v "setpts=0.5*PTS" output_2x.mp4

# Slow down 0.5x
ffmpeg -i timelapse_20251104_000000.mp4 -filter:v "setpts=2*PTS" output_half.mp4
```

## Troubleshooting

### No videos are being created

1. Check logs: `docker-compose logs -f`
2. Verify RTSP URL is correct
3. Test stream with ffmpeg: `ffmpeg -i rtsp://your-url -frames:v 1 test.jpg`
4. Ensure sufficient disk space
5. Check temp_frames directory for accumulated frames

### Videos are choppy or low quality

- Increase `VIDEO_QUALITY` to 20 or lower (better quality, larger files)
- Reduce `CYCLE_TIME` for more frames (smoother video)
- Increase `VIDEO_FPS` to 30 for smoother playback

### Running out of storage

- Increase `CYCLE_TIME` for fewer frames
- Decrease `VIDEO_QUALITY` to 25-28 (smaller files)
- Set up auto-deletion of old videos (use cron or TrueNAS tasks)

### Container crashes or restarts

- Check available memory
- Reduce `FRAMES_PER_VIDEO` if running out of memory during compilation
- Check logs for specific errors

## Building from Source

```bash
# Build the image
docker build -t timelapse-capture .

# Run manually
docker run -d \
  -e RTSP_URL=rtsp://your-camera/stream \
  -v $(pwd)/screenshots:/screenshots \
  timelapse-capture
```

## License

MIT License - Feel free to modify and use as needed.

## Contributing

Pull requests are welcome! For major changes, please open an issue first.
