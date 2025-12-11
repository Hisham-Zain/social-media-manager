# 🔧 Troubleshooting

Common issues and solutions for AgencyOS.

---

## Installation Issues

### FFmpeg Not Found

**Error:** `FileNotFoundError: ffmpeg not found`

**Solution:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Verify installation
ffmpeg -version
```

---

### Python Version Error

**Error:** `Python 3.10+ required`

**Solution:**
```bash
# Check version
python3 --version

# Install Python 3.10+
sudo apt install python3.10
```

---

### Dependency Conflicts

**Error:** `pip: conflicting dependencies`

**Solution:**
```bash
# Create fresh virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## API Key Issues

### Gemini API Error

**Error:** `API key not valid`

**Solution:**
1. Get key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Add to `.env`:
   ```
   GEMINI_API_KEY=your_key_here
   ```
3. Restart application

---

### Rate Limiting

**Error:** `429 Too Many Requests`

**Solution:**
- Wait 60 seconds and retry
- Use fallback provider (Groq/Ollama)
- Upgrade API plan for higher limits

---

## GUI Issues

### GUI Won't Launch

**Error:** `qt.qpa.xcb: could not connect to display`

**Solution:**
```bash
# Linux: Ensure display is set
export DISPLAY=:0

# WSL2: Install X server (VcXsrv)
# Then set:
export DISPLAY=$(hostname).local:0
```

---

### Fonts Too Small

**Solution:**
1. Go to **⚙️ Settings** → **Appearance**
2. Increase **Font Size**
3. Restart application

---

### View Not Loading

**Solution:**
1. Check **📋 Job Queue** for errors
2. Look at console for error messages
3. Try restarting the application

---

## Processing Issues

### Video Processing Fails

**Error:** `MoviePy error`

**Solution:**
1. Verify FFmpeg is installed
2. Check input file is not corrupted
3. Ensure sufficient disk space
4. Check console logs for specific error

---

### TTS Generation Fails

**Error:** `VoxCPM model not found`

**Solution:**
```bash
# Models download automatically on first use
# Ensure internet connection

# Check model directory
ls ~/.social_media_manager/assets/voices/
```

---

### Out of Memory

**Error:** `CUDA out of memory` or `MemoryError`

**Solution:**
- Close other GPU applications
- Reduce batch size in settings
- Use CPU-only mode:
  ```env
  CUDA_VISIBLE_DEVICES=-1
  ```

---

## Database Issues

### Database Connection Failed

**Error:** `could not connect to PostgreSQL`

**Solution:**
1. Start PostgreSQL:
   ```bash
   sudo systemctl start postgresql
   ```
2. Verify credentials in `.env`:
   ```
   DATABASE_URL=postgresql://user:pass@localhost:5432/agencyos
   ```
3. Create database:
   ```bash
   createdb agencyos
   ```

---

### Migration Errors

**Solution:**
```bash
# Reset database (WARNING: data loss)
python -c "
from social_media_manager.database import Base, engine
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
"
```

---

## Network Issues

### Platform Upload Fails

**Error:** `Authentication failed`

**Solution:**
1. Re-authenticate in **⚙️ Settings** → **Connections**
2. Check API token hasn't expired
3. Verify platform permissions

---

### Search Not Working

**Error:** `Perplexity/Google search failed`

**Solution:**
- Verify API key is set
- Check internet connection
- Try alternative search provider

---

## Getting More Help

1. **Check Logs**
   ```bash
   # Console shows detailed errors
   python -m social_media_manager.gui.main
   ```

2. **Enable Debug Mode**
   ```env
   DB_ECHO=true
   ```

3. **Report Issue**
   - [GitHub Issues](https://github.com/youruser/social-media-manager/issues)
   - Include error message and steps to reproduce
