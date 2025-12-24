# PDF Similarity Detection System - Web Application

A world-class, AI-powered PDF similarity detection system built with React/Next.js frontend and Python FastAPI backend. This application provides advanced document analysis with real-time processing and beautiful UI/UX.

## 🚀 Features

### Core Functionality
- **Advanced PDF Processing**: Extract and filter content from PDF documents
- **Intelligent Similarity Detection**: 8-character sequence similarity analysis with configurable thresholds
- **Real-time Progress Tracking**: WebSocket-powered live updates during processing
- **Content Filtering**: Focus on main content by filtering references, citations, and metadata
- **Multiple Export Formats**: Text, JSON, CSV, and PDF report exports
- **High Performance**: Optimized algorithms for processing large files (200k+ characters)

### User Experience
- **World-class UI**: Beautiful, responsive interface with Tailwind CSS
- **Drag & Drop Upload**: Intuitive file upload with progress tracking
- **Interactive Results**: Expandable similarity cards with context display
- **Mobile Responsive**: Works seamlessly on all devices
- **Dark Mode Support**: Comfortable viewing in any lighting (future feature)
- **Accessibility**: WCAG 2.1 AA compliant interface

### Technical Features
- **Scalable Architecture**: Microservices design with FastAPI and Next.js
- **Real-time Communication**: WebSocket for live progress updates
- **Performance Optimized**: Multi-processing and intelligent caching
- **Type Safety**: Full TypeScript implementation
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- **Docker Support**: Containerized deployment with Docker Compose

## 🏗️ Architecture

### Frontend (Next.js 15 + React 18)
- **UI Framework**: Tailwind CSS with custom design system
- **State Management**: React Query for server state, Zustand for client state
- **Form Handling**: React Hook Form with Zod validation
- **File Upload**: React Dropzone with progress tracking
- **Animations**: Framer Motion for smooth transitions
- **Icons**: Lucide React for consistent iconography
- **Notifications**: React Hot Toast for user feedback

### Backend (Python FastAPI)
- **Web Framework**: FastAPI with async/await support
- **PDF Processing**: pdfplumber for text extraction
- **Similarity Detection**: Custom optimized algorithms
- **Real-time Updates**: WebSocket connections
- **File Storage**: Configurable local or cloud storage
- **Error Handling**: Comprehensive error management
- **Logging**: Structured logging with monitoring

### Processing Pipeline
1. **File Upload** → Validation → Storage
2. **Content Extraction** → Filtering → Processing
3. **Similarity Detection** → Result Generation
4. **Export Creation** → File Delivery

## 📋 System Requirements

### Development Environment
- **Node.js**: 18.0.0 or higher
- **Python**: 3.11 or higher
- **Redis**: 5.2 or higher (optional, for caching)
- **Memory**: 8GB+ RAM recommended for large files
- **Storage**: 10GB+ available space

### Production Environment
- **Docker**: 20.10+ and Docker Compose 2.0+
- **Memory**: 16GB+ RAM for production workloads
- **CPU**: 4+ cores for optimal performance
- **Storage**: 50GB+ SSD for file storage
- **Load Balancer**: Nginx or similar (recommended)

## 🛠️ Installation

### Quick Start with Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd pdf_duplicate_detector/web_app
   ```

2. **Environment setup**:
   ```bash
   # Backend environment
   cp backend/.env.example backend/.env

   # Frontend environment (if needed)
   cp frontend/.env.example frontend/.env.local
   ```

3. **Start development services**:
   ```bash
   docker-compose -f docker-compose.dev.yml up --build
   ```

4. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Deployment

1. **Configure production environment**:
   ```bash
   # Update backend/.env with production settings
   cp backend/.env.example backend/.env
   # Edit the file with your production configuration
   ```

2. **Start production services**:
   ```bash
   docker-compose up --build -d
   ```

3. **Access the production application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - (Configure your domain and SSL in production)

### Local Development Setup

#### Backend Setup

1. **Create virtual environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements_web.txt
   ```

3. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the backend server**:
   ```bash
   uvicorn main:app --reload
   ```

#### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env.local
   # Edit with your configuration
   ```

3. **Start the development server**:
   ```bash
   npm run dev
   ```

## ⚙️ Configuration

### Backend Environment Variables

```bash
# Application
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Security
JWT_SECRET=your-super-secret-jwt-key
JWT_EXPIRE_HOURS=24

# File Processing
MAX_FILE_SIZE=104857600          # 100MB
MAX_SEQUENCES=5000
MIN_SIMILARITY=0.75
PROCESSING_MODE=fast
CONTEXT_CHARS=100

# Storage
UPLOAD_DIR=uploads
EXPORT_DIR=exports

# CORS
CORS_ORIGINS=http://localhost:3000

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### Frontend Environment Variables

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Analytics (optional)
NEXT_PUBLIC_GA_ID=your-google-analytics-id
```

## 📖 Usage Guide

### 1. Upload Files
- Drag and drop PDF files into the upload zone
- Or click to browse and select files
- Maximum file size: 100MB per file
- Supported format: PDF only

### 2. Configure Processing Options
- **Processing Mode**: Choose between Standard, Fast, or Ultra Fast
- **Content Filter**: Select which content to analyze
- **Similarity Threshold**: Set minimum similarity (50-100%)
- **Export Format**: Choose preferred output format

### 3. Start Analysis
- Click "Start Comparison" after selecting 2 files
- Monitor real-time progress with detailed status updates
- Processing time varies based on file size and complexity

### 4. Review Results
- View similarity statistics and overview
- Examine individual similar sequences with context
- Filter and sort results as needed
- Export results in your preferred format

### 5. Export Results
- Download results in Text, JSON, CSV, or PDF format
- Include detailed analysis and context information
- Share results with colleagues or save for later reference

## 🔧 API Documentation

### Core Endpoints

- `POST /api/v1/upload` - Upload PDF files
- `POST /api/v1/compare` - Start similarity comparison
- `GET /api/v1/task/{task_id}/status` - Get task status
- `GET /api/v1/task/{task_id}/result` - Get comparison results
- `GET /health` - Health check

### WebSocket
- `WS /ws/{task_id}` - Real-time progress updates

### Interactive Documentation
Visit http://localhost:8000/docs for interactive API documentation.

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

### End-to-End Tests
```bash
# From project root
npm run test:e2e
```

## 📊 Performance

### Processing Speed
- **Fast Mode**: 200k character files in 2-5 minutes
- **Standard Mode**: 200k character files in 5-15 minutes
- **Ultra Fast Mode**: 200k character files in 1-3 minutes

### Scalability
- Supports concurrent processing of multiple file pairs
- Horizontal scaling with multiple backend instances
- Redis-based caching for improved performance (future feature)

### Resource Usage
- **Memory**: 500MB - 2GB per processing task
- **CPU**: Moderate usage during processing
- **Storage**: Temporary files cleaned up automatically

## 🔒 Security

### Data Protection
- Files are processed temporarily and deleted after processing
- No long-term storage of uploaded documents
- Secure file handling with validation

### API Security
- JWT-based authentication (future feature)
- CORS configuration for cross-origin protection
- Request rate limiting (future feature)
- Input validation and sanitization

### Production Security
- SSL/TLS encryption for all communications
- Environment-based configuration
- Regular security updates
- Security headers and policies

## 🐛 Troubleshooting

### Common Issues

#### Files Won't Upload
- Check file format (PDF only supported)
- Verify file size under 100MB limit
- Ensure sufficient disk space

#### Processing Takes Too Long
- Try Fast or Ultra Fast processing modes
- Check system resources (CPU, RAM)
- Consider reducing file size or complexity

#### No Results Found
- Lower similarity threshold
- Check if files contain comparable content
- Verify content filter settings

#### Connection Errors
- Confirm backend service is running
- Check API configuration in environment variables
- Verify network connectivity

### Support
For additional support:
1. Check the application logs
2. Review API documentation
3. Create an issue in the repository
4. Contact the development team

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Roadmap

### Version 1.1 (Planned)
- [ ] User authentication and accounts
- [ ] Batch file processing
- [ ] Advanced filtering options
- [ ] Export to Microsoft Word
- [ ] Integration with cloud storage

### Version 1.2 (Future)
- [ ] Support for additional file formats (DOCX, TXT)
- [ ] Machine learning similarity improvements
- [ ] Collaborative analysis features
- [ ] API rate limiting and usage analytics
- [ ] Mobile applications

### Version 2.0 (Long-term)
- [ ] Multi-language support
- [ ] Advanced visualization dashboards
- [ ] Integration with document management systems
- [ ] Enterprise features and SSO
- [ ] AI-powered content analysis

## 📞 Contact

For questions, support, or feature requests:
- Email: support@example.com
- Documentation: https://docs.example.com
- Issues: https://github.com/example/pdf-similarity/issues

---

**Built with ❤️ using Next.js, FastAPI, and modern web technologies**