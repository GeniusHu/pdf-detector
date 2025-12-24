# 🚀 Quick Start Guide

Get your PDF Similarity Detection System running in minutes!

## Prerequisites

- **Docker** and **Docker Compose** installed
- **8GB+ RAM** recommended for optimal performance
- **10GB+ free disk space**

## One-Command Deployment

### Development Environment
```bash
# Clone and deploy
git clone <repository-url>
cd pdf_duplicate_detector/web_app
./deploy.sh
```

### Production Environment
```bash
# Deploy with production settings
./deploy.sh --environment production
```

## What's Included?

This system provides:

✅ **Advanced PDF Analysis** - AI-powered content extraction and filtering
✅ **Real-time Processing** - Live progress updates via WebSocket
✅ **Beautiful UI** - Modern, responsive interface with Tailwind CSS
✅ **High Performance** - Optimized algorithms for large files (200k+ chars)
✅ **Multiple Export Formats** - Text, JSON, CSV, PDF reports
✅ **World-class UX** - Drag & drop uploads, interactive results

## Access Points

After deployment, access your system at:

- **🌐 Web Application**: http://localhost:3000
- **📡 API Endpoint**: http://localhost:8000
- **📚 API Documentation**: http://localhost:8000/docs
- **🗃️ Redis Cache**: localhost:6379

## Usage Guide

### 1. Upload Your PDFs
- Drag & drop PDF files into the upload zone
- Maximum file size: 100MB per file
- Supported format: PDF documents

### 2. Configure Analysis
- **Processing Mode**: Choose Fast (recommended) or Ultra Fast for quicker results
- **Content Filter**: Focus on main content by filtering references
- **Similarity Threshold**: Set minimum similarity (75% default works well)

### 3. Get Results
- Watch real-time processing progress
- Review detailed similarity analysis
- Export results in your preferred format

## Troubleshooting

### Issues Getting Started?

**Port Already in Use?**
```bash
# Check what's using port 3000/8000
lsof -i :3000
lsof -i :8000

# Stop existing services
./deploy.sh stop
```

**Build Fails?**
```bash
# Clean up and rebuild
./deploy.sh cleanup
./deploy.sh --skip-build false
```

**Services Not Starting?**
```bash
# Check logs
./deploy.sh logs
```

### Performance Issues?

**Processing Too Slow?**
- Try "Ultra Fast" mode for quicker results
- Reduce file size if possible
- Check system resources (RAM/CPU)

**Memory Usage High?**
- Monitor with `docker stats`
- Limit concurrent processing tasks
- Consider system upgrade for production use

## Need Help?

### Documentation
- 📖 **Full Documentation**: [README.md](README.md)
- 🔧 **API Reference**: http://localhost:8000/docs

### Common Questions

**Q: Can I process other file formats?**
A: Currently PDF only. DOCX and TXT support planned for v1.2.

**Q: Is my data secure?**
A: Files are processed temporarily and deleted automatically. No long-term storage.

**Q: What's the maximum file size?**
A: 100MB per file in default configuration. Can be increased in settings.

**Q: How accurate is the similarity detection?**
A: Uses advanced 8-character sequence analysis with configurable thresholds (75-100%).

## Configuration

### Environment Variables

Edit configuration files:

```bash
# Backend settings
nano backend/.env

# Frontend settings
nano frontend/.env.local
```

### Key Settings

- `MAX_FILE_SIZE`: Maximum upload size (bytes)
- `PROCESSING_MODE`: Default processing speed
- `MIN_SIMILARITY`: Default similarity threshold
- `CORS_ORIGINS`: Allowed frontend origins

## Production Deployment

For production use:

1. **Configure Environment**
   ```bash
   # Edit production settings
   nano backend/.env
   ```

2. **Deploy with SSL** (recommended)
   ```bash
   # Configure Nginx reverse proxy
   # Set up SSL certificates
   ./deploy.sh --environment production
   ```

3. **Monitor Performance**
   - Check system resources
   - Monitor API response times
   - Set up logging and alerts

## Advanced Usage

### Custom Configuration
- Adjust similarity algorithms in backend
- Modify UI components in frontend
- Add custom export formats
- Integrate with cloud storage

### API Integration
- Use REST API for programmatic access
- WebSocket for real-time updates
- Batch processing capabilities

## Development

### Local Development Setup
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements_web.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Contributing
- Fork the repository
- Create feature branches
- Submit pull requests
- Follow coding standards

## Support

### Get Help
- 📧 **Email**: support@example.com
- 🐛 **Issues**: GitHub Issues
- 📖 **Documentation**: Full README

### System Requirements

**Minimum:**
- 4GB RAM
- 2 CPU cores
- 10GB storage

**Recommended:**
- 8GB+ RAM
- 4+ CPU cores
- 20GB+ storage

---

🎉 **Congratulations!** Your PDF Similarity Detection System is ready to use.

**Next Steps:**
1. Upload your first PDF files
2. Experiment with different settings
3. Explore the detailed results
4. Export and share your findings

**Need more features?** Check our [Roadmap](README.md#-roadmap) for upcoming enhancements!