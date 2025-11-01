# RTSP Time-lapse Screenshot Capture

A Docker-based service that captures screenshots from an RTSP stream at regular intervals using ffmpeg. Optimized for UDP streams and designed to create time-lapse videos where 1 day of real-time equals approximately 1 minute of video.

## Features

- 📸 Automated screenshot capture from RTSP streams
- 🔄 Stream preloading for stable connections
- 🐳 Fully containerized with Docker
- 🎬 Optimized for time-lapse creation (1 day = ~1 minute)
- 📺 Uses ffmpeg for excellent UDP/RTSP stream handling
- 🔧 Configurable via environment variables
- ☁️ TrueNAS Scale compatible

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

### 4. Check Screenshots

Screenshots will be saved in the `./screenshots` directory with timestamps:
- Format: `screenshot_YYYYMMDD_HHMMSS.png`
- Example: `screenshot_20251101_143022.png`

## Configuration

All settings can be configured via environment variables in `docker-compose.yml`:

| Variable | Default | Description |
|----------|---------|-------------|
| `RTSP_URL` | `rtsp://example.com/stream` | Your RTSP stream URL |
| `PRELOAD_TIME` | `10` | Seconds to preload stream before capture |
| `CYCLE_TIME` | `60` | Total seconds per complete cycle (preload + capture + sleep) |
| `IMAGE_WIDTH` | `1920` | Screenshot width in pixels |
| `IMAGE_HEIGHT` | `1080` | Screenshot height in pixels |
| `OUTPUT_DIR` | `/screenshots` | Output directory (inside container) |

**Note:** Actual sleep time = `CYCLE_TIME - PRELOAD_TIME` (automatically calculated)

### Time-lapse Calculation

With default settings (60-second cycle time):
- **1 day** (24 hours) = 1,440 screenshots
- At **24 fps**: 1,440 frames = **60 seconds** of video
- At **30 fps**: 1,440 frames = **48 seconds** of video

To adjust the time-lapse ratio, modify `CYCLE_TIME`:
- 30 seconds → 1 day = ~2 minutes of video
- 120 seconds → 1 day = ~30 seconds of video

**Example:** For 1 day = 2 minutes of video at 24fps:
- Set `CYCLE_TIME=30` (captures 2,880 screenshots per day)

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
   - Mount host path for screenshots

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

For unstable connections, increase the preload time:
```yaml
- PRELOAD_TIME=20  # 20 seconds preload
- CYCLE_TIME=60    # Keep same cycle time
```
This gives more time for connection stability while maintaining the same screenshot frequency.

## Creating the Time-lapse Video

Once you have screenshots, create a video using ffmpeg:

```bash
# Navigate to screenshots directory
cd screenshots

# Create video at 24fps (1 day = ~60 seconds)
ffmpeg -framerate 24 -pattern_type glob -i 'screenshot_*.png' \
  -c:v libx264 -pix_fmt yuv420p -crf 23 timelapse.mp4

# Create video at 30fps (1 day = ~48 seconds)
ffmpeg -framerate 30 -pattern_type glob -i 'screenshot_*.png' \
  -c:v libx264 -pix_fmt yuv420p -crf 23 timelapse.mp4
```

## Troubleshooting

### No screenshots are being created

1. Check logs: `docker-compose logs -f`
2. Verify RTSP URL is correct
3. Test stream with ffmpeg: `ffmpeg -i rtsp://your-url -frames:v 1 test.png`
4. Try using TCP or UDP depending on your camera

### Connection timeout errors

- Increase `PRELOAD_TIME` to 120+ seconds
- Check network connectivity to camera
- Verify firewall rules allow RTSP traffic

### Black/corrupted screenshots

- Increase `PRELOAD_TIME` for better stream stability
- Check if stream resolution matches `IMAGE_WIDTH`/`IMAGE_HEIGHT`
- Verify camera is streaming at configured resolution
- Try different quality settings in ffmpeg command

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
