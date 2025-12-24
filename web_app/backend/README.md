# PDF Similarity Detection Backend

FastAPI backend for PDF similarity detection with real-time processing and WebSocket updates.

## Features

- **PDF Processing**: Advanced content extraction with configurable filtering
- **Similarity Detection**: Optimized 8-character sequence similarity detection
- **Real-time Updates**: WebSocket progress tracking
- **Multiple Export Formats**: Text, JSON, CSV export options
- **Performance Optimization**: Multi-processing and intelligent algorithms
- **Scalable Architecture**: Async processing with task management

## Quick Start

### Prerequisites

- Python 3.11+
- Redis (optional, for future caching)

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements_web.txt
   ```

3. Create environment file:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Create necessary directories:
   ```bash
   mkdir -p uploads exports logs
   ```

5. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

### Docker

Build and run with Docker:

```bash
docker build -t pdf-similarity-backend .
docker run -p 8000:8000 -v $(pwd)/uploads:/app/uploads -v $(pwd)/exports:/app/exports pdf-similarity-backend
```

## API Endpoints

### Core Endpoints

- `POST /api/v1/compare` - Start PDF comparison task
- `POST /api/v1/upload` - Upload PDF file
- `GET /api/v1/task/{task_id}/status` - Get task status
- `GET /api/v1/task/{task_id}/result` - Get task result
- `DELETE /api/v1/task/{task_id}` - Delete task

### WebSocket

- `WS /ws/{task_id}` - Real-time progress updates

### Utility Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger)

## Configuration

### Environment Variables

Key environment variables:

- `DEBUG` - Enable debug mode
- `MAX_FILE_SIZE` - Maximum upload file size (bytes)
- `MAX_SEQUENCES` - Maximum sequences per file for processing
- `MIN_SIMILARITY` - Default similarity threshold
- `PROCESSING_MODE` - Default processing mode (standard/fast/ultra_fast)
- `CONTEXT_CHARS` - Number of context characters to display

### Content Filtering Options

- `ALL_CONTENT` - Include all content
- `MAIN_CONTENT_ONLY` - Filter out references, citations, headers
- `INCLUDE_REFERENCES` - Include references in main content
- `INCLUDE_CITATIONS` - Include citations in main content

### Processing Modes

- `STANDARD` - Full processing with all features
- `FAST` - Optimized processing with moderate limits
- `ULTRA_FAST` - Maximum speed with strict limits

## Usage Examples

### Start Comparison

```bash
curl -X POST "http://localhost:8000/api/v1/compare" \
  -H "Content-Type: application/json" \
  -d '{
    "pdf1_path": "/uploads/file1.pdf",
    "pdf2_path": "/uploads/file2.pdf",
    "similarity_threshold": 0.8,
    "content_filter": "main_content_only",
    "processing_mode": "fast",
    "export_format": "json"
  }'
```

### Upload File

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@example.pdf"
```

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/your-task-id');
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Progress:', data.progress);
};
```

## Architecture

### Core Services

- **PDFService**: PDF content extraction and filtering
- **SimilarityService**: Similarity detection and result processing
- **WebSocketManager**: Real-time communication

### Processing Pipeline

1. PDF Upload → Validation → Storage
2. Content Extraction → Filtering → Processing
3. Similarity Detection → Result Generation
4. Export Creation → File Delivery

### Performance Features

- Multi-processing parallel computation
- Intelligent sequence pre-filtering
- Memory-efficient algorithms
- Progress tracking and cancellation

## Development

### Running Tests

```bash
pytest tests/
```

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation.

## Production Deployment

### Security Considerations

1. Set secure JWT secret
2. Configure appropriate CORS origins
3. Use HTTPS in production
4. Set appropriate file size limits
5. Implement rate limiting

### Scaling

- Use Redis for distributed task management
- Implement load balancing with multiple instances
- Configure monitoring and logging
- Set up automated backups for user files

## Monitoring

### Health Checks

- `/health` endpoint provides service status
- WebSocket connection statistics
- Task processing metrics
- Error tracking and logging

### Performance Metrics

- File processing time
- Memory usage monitoring
- Task queue length
- WebSocket connection count

## License

This project is part of the PDF Similarity Detection System.