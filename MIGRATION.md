# Time-lapse Migration Guide

## � Automatic Migration (Recommended)

**The system now migrates automatically!** No manual steps required.

### How It Works

1. **Deploy new version** in Portainer
2. System **detects old PNG/JPG frames** on first startup
3. **Automatically converts** to video files
4. **Deletes old frames** after successful conversion
5. **Starts video recording** normally

### Configuration

Control auto-migration with environment variables in Portainer:

```yaml
environment:
  - AUTO_MIGRATE=true         # Enable auto-migration (default)
  - DELETE_OLD_FRAMES=true    # Delete PNGs after conversion (default)
```

### Monitoring Auto-Migration

Watch the container logs in Portainer:

1. Go to **Containers** → **timelapse-capture**
2. Click **Logs**
3. You'll see:
   ```
   🔄 OLD FRAMES DETECTED - STARTING MIGRATION
   Found 5000 old frames to migrate
   Creating video 1/4...
   ✓ Migration completed successfully
   🎥 STARTING VIDEO RECORDING MODE
   ```

---

## 📖 Manual Migration (Optional)

## 📖 Manual Migration (Optional)

If you prefer manual control or need to migrate from a different location:

### Step 1: Disable Auto-Migration

In your docker-compose or Portainer stack:

**Using Docker Compose:**

```bash
# Set your paths
export OLD_SCREENSHOTS_PATH=/mnt/bigData/tank/time-lapse  # Your existing frames
export VIDEO_PATH=/mnt/bigData/tank/time-lapse-videos     # New video output

# Run migration (one-time)
docker-compose -f docker-compose.migrate.yml up

# Check the logs
docker logs timelapse-migrate
```

**Or run manually in TrueNAS:**

```bash
# SSH into TrueNAS
ssh admin@your-truenas-ip

# Run migration script
docker run --rm \
  -v /mnt/bigData/tank/time-lapse:/old_screenshots:ro \
  -v /mnt/bigData/tank/time-lapse-videos:/videos \
  -e FRAMES_DIR=/old_screenshots \
  -e OUTPUT_DIR=/videos \
  -e VIDEO_FPS=24 \
  -e DELETE_FRAMES_AFTER=false \
  your-registry/timelapse-capture:latest \
  python -u migrate_frames.py
```

### Step 2: Review Migrated Videos

Check the output directory for your videos:

```bash
ls -lh /mnt/bigData/tank/time-lapse-videos
```

You should see files like:
- `timelapse_migrated_20251101_000000.mp4`
- `timelapse_migrated_20251102_000000.mp4`
- etc.

### Step 3: Update Main Service

Once migration is complete, update your main time-lapse service in Portainer:

1. **Stop** the old service
2. **Update** the stack with new docker-compose.yml
3. **Change** environment variables:
   - Remove: `PRELOAD_TIME`, `IMAGE_WIDTH`, `IMAGE_HEIGHT`
   - Add: `VIDEO_FPS`, `VIDEO_QUALITY`, `VIDEO_DURATION_HOURS`
4. **Update** volume path from screenshots to videos
5. **Redeploy** the stack

### Step 4: Clean Up Old Frames (Optional)

After verifying videos are good:

```bash
# CAREFUL: This deletes your frames permanently!
# Only do this after confirming videos are correct

# Option 1: Delete all
rm -rf /mnt/bigData/tank/time-lapse/*.png
rm -rf /mnt/bigData/tank/time-lapse/*.jpg

# Option 2: Re-run migration with DELETE_FRAMES_AFTER=true
docker run --rm \
  -v /mnt/bigData/tank/time-lapse:/old_screenshots \
  -v /mnt/bigData/tank/time-lapse-videos:/videos \
  -e DELETE_FRAMES_AFTER=true \
  your-registry/timelapse-capture:latest \
  python -u migrate_frames.py
```

## 📊 What Migration Does

1. **Finds all frames** in your screenshots directory
2. **Groups them** by time (default: 1440 frames = 1 day)
3. **Creates videos** for each group at 24 fps
4. **Names videos** with timestamp: `timelapse_migrated_YYYYMMDD_HHMMSS.mp4`
5. **Optionally deletes** original frames (if `DELETE_FRAMES_AFTER=true`)

## 🎬 Expected Results

**Before Migration:**
- 5 GB of PNG files (1,440 frames × 3-5 MB each)

**After Migration:**
- 50-100 MB of MP4 video (single file)
- **~98% space savings!**

## ⚙️ Migration Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FRAMES_DIR` | `/old_screenshots` | Directory with existing frames |
| `OUTPUT_DIR` | `/videos` | Output directory for videos |
| `VIDEO_FPS` | `24` | Frames per second in output video |
| `VIDEO_QUALITY` | `23` | CRF quality (18-28, lower=better) |
| `FRAMES_PER_VIDEO` | `1440` | Max frames per video file |
| `DELETE_FRAMES_AFTER` | `false` | Delete frames after conversion |

## 🔍 Troubleshooting

### Migration taking too long
- Normal for large frame counts
- 1000 frames ≈ 2-5 minutes
- Check logs: `docker logs -f timelapse-migrate`

### Out of memory
- Reduce `FRAMES_PER_VIDEO` to 720 (12 hours)
- Process in smaller batches

### Videos look wrong
- Check frame order with: `ls -lt /old_screenshots`
- Adjust `VIDEO_FPS` (try 30 instead of 24)
- Increase `VIDEO_QUALITY` to 20 for better quality

### Permission errors
- Ensure output directory is writable
- Run: `chmod 777 /mnt/bigData/tank/time-lapse-videos`

## ✅ Verification

After migration, verify videos:

```bash
# Check video info
ffprobe /mnt/bigData/tank/time-lapse-videos/timelapse_migrated_*.mp4

# Play a video (if you have ffplay)
ffplay /mnt/bigData/tank/time-lapse-videos/timelapse_migrated_*.mp4
```

## 📝 Notes

- **Safe by default**: Original frames are NOT deleted unless you set `DELETE_FRAMES_AFTER=true`
- **Idempotent**: Can run multiple times safely
- **Resume**: Skips already processed groups
- **PNG/JPEG**: Automatically converts PNG to JPEG during processing
