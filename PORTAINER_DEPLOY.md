# 🚀 Quick Deployment Guide for Portainer (TrueNAS Scale)

## Automatic Migration & Upgrade

This guide shows how to upgrade your existing time-lapse service in Portainer. The system will **automatically migrate your old PNG frames to videos and delete them**.

---

## 📋 Step-by-Step Instructions

### 1. **Build New Docker Image**

On your local machine (Windows):

```powershell
cd "C:\Users\Jonathan Schroeter\Documents\code_playground\time_lapse"

# Build the image
docker build -t asusplayer/timelapse-capture:latest .

# Push to Docker Hub (or your registry)
docker push asusplayer/timelapse-capture:latest
```

### 2. **Update Stack in Portainer**

1. Log into **Portainer** on TrueNAS
2. Go to **Stacks**
3. Click on your existing **timelapse-capture** stack
4. Click **Editor**

### 3. **Update the Stack Configuration**

Replace the entire content with this:

```yaml
version: '3.8'

services:
  timelapse-capture:
    image: asusplayer/timelapse-capture:latest
    container_name: timelapse-capture
    restart: unless-stopped
    
    environment:
      # RTSP stream URL
      - RTSP_URL=${RTSP_URL}
      
      # Frame capture interval (seconds)
      - CYCLE_TIME=60
      
      # Video output settings
      - VIDEO_FPS=24
      - VIDEO_QUALITY=23
      - VIDEO_DURATION_HOURS=24
      - KEEP_TEMP_FRAMES=false
      
      # Auto-migration (IMPORTANT!)
      - AUTO_MIGRATE=true
      - DELETE_OLD_FRAMES=true
      
      # Output directory
      - OUTPUT_DIR=/videos
    
    volumes:
      # Use SAME path as before (contains your PNG frames)
      - /mnt/bigData/tank/time-lapse:/videos
    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. **Set Environment Variables**

In Portainer, scroll down to **Environment variables** section and ensure:

| Variable | Value |
|----------|-------|
| `RTSP_URL` | `rtsp://asusplayer:Hyperaktiv12@192.168.50.125:554/stream1` |

### 5. **Deploy**

1. Click **Update the stack**
2. Select **Pull latest image version**
3. Click **Update**

### 6. **Monitor Migration**

1. Go to **Containers** → **timelapse-capture**
2. Click **Logs**
3. Watch the migration progress:

```
🚀 TIME-LAPSE SERVICE STARTING
Found 5000 old frames to migrate
🔄 OLD FRAMES DETECTED - STARTING MIGRATION
Creating video 1/4...
✓ Video created: timelapse_migrated_20251101_000000.mp4
Creating video 2/4...
✓ Video created: timelapse_migrated_20251102_000000.mp4
...
✓ Migration completed successfully
Deleting processed frames...
🎥 STARTING VIDEO RECORDING MODE
```

---

## ⏱️ Migration Time Estimate

| Frames | Estimated Time |
|--------|---------------|
| 1,000 | ~2-5 minutes |
| 5,000 | ~10-20 minutes |
| 10,000 | ~20-40 minutes |

---

## ✅ Verification

After migration completes:

### Check Videos Created
```bash
# SSH into TrueNAS
ssh admin@your-truenas-ip

# List videos
ls -lh /mnt/bigData/tank/time-lapse/*.mp4

# You should see files like:
# timelapse_migrated_20251101_000000.mp4  (80M)
# timelapse_migrated_20251102_000000.mp4  (85M)
```

### Verify Old Frames Deleted
```bash
# Check for old PNG files (should be none)
ls /mnt/bigData/tank/time-lapse/*.png
# ls: cannot access '*.png': No such file or directory  ✓ Good!
```

### Check Service Running
In Portainer logs, you should see:
```
🎥 STARTING VIDEO RECORDING MODE
Starting time-lapse recording...
[1/1440] Capturing frame...
✓ Frame saved: frame_000000_20251104_120000.jpg
Waiting 60 seconds until next frame...
```

---

## 🎛️ Configuration Options

### Disable Auto-Migration

If you want to migrate manually later:
```yaml
- AUTO_MIGRATE=false
- DELETE_OLD_FRAMES=false
```

### Keep Old Frames

If you want to keep PNG files after migration:
```yaml
- AUTO_MIGRATE=true
- DELETE_OLD_FRAMES=false
```

### Change Video Settings

Adjust compression and quality:
```yaml
- VIDEO_FPS=30              # Smoother video
- VIDEO_QUALITY=20          # Better quality
- VIDEO_DURATION_HOURS=12   # Shorter video files
```

---

## 🆘 Troubleshooting

### Migration Not Starting

Check logs for:
```
No old frames found, starting fresh
```

This means:
- Frames already migrated, OR
- Wrong volume path, OR
- Files have different naming pattern

**Solution:** Check your volume mapping matches where frames are stored.

### Migration Fails

Check logs for specific errors:
```
✗ Migration failed: ...
Continuing with video recording mode anyway...
```

**Solution:** 
1. Note the error message
2. Set `DELETE_OLD_FRAMES=false`
3. Redeploy
4. Contact support with error details

### Container Restarts During Migration

Check available memory:
```bash
# On TrueNAS
free -h
```

**Solution:** Reduce `FRAMES_PER_VIDEO` or add more memory.

### Old Frames Still Present

Check if migration actually ran:
```bash
# Check if videos were created
ls -lh /mnt/bigData/tank/time-lapse/timelapse_migrated_*.mp4
```

If videos exist but PNGs remain:
- Migration didn't complete successfully
- Check logs for errors
- Manually delete: `rm /mnt/bigData/tank/time-lapse/*.png`

---

## 📊 Before & After

**Before Upgrade:**
- 5,000 PNG files @ 3-5 MB each = **~15-25 GB**
- Hard to manage and browse
- Slow file operations

**After Upgrade:**
- 4-5 MP4 files @ 80-100 MB each = **~400 MB**
- **98% space saved!**
- Easy to play and share
- Continuous recording

---

## 🎬 Next Steps

After successful migration:

1. **Test playback** of migrated videos
2. **Monitor disk space** (should drop significantly)
3. **Set up auto-cleanup** for old videos (optional)
4. **Backup videos** to another location
5. **Enjoy your time-lapse!** 🎉

---

## 📞 Need Help?

Check container logs first:
```bash
docker logs -f timelapse-capture
```

Common issues and solutions in the main README.md.
