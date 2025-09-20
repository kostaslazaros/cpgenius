# File Upload API Documentation

This API provides endpoints for uploading and processing large .idat and .csv files using Celery for asynchronous processing.

## Features

- **File Upload**: Upload multiple .idat and .csv files simultaneously
- **SHA1 Identification**: Files are stored using SHA1 hash as unique identifier
- **Asynchronous Processing**: Large files are processed using Celery tasks
- **Progress Monitoring**: Track the progress of file processing
- **File Management**: List and remove uploaded files
- **Duplicate Detection**: Prevents duplicate uploads based on file content

## API Endpoints

### 1. Upload Files
**POST** `/idat/upload`

Upload multiple .idat and .csv files for processing.

**Request:**
- Content-Type: `multipart/form-data`
- Files: Multiple files with extensions `.idat` or `.csv`

**Response:**
```json
{
  "task_id": "celery-task-id",
  "sha1_hash": "unique-sha1-hash",
  "message": "Files uploaded successfully. Processing started.",
  "file_count": 2
}
```

### 2. Check Processing Status
**GET** `/idat/status/{task_id}`

Get the current status of a file processing task.

**Response:**
```json
{
  "task_id": "celery-task-id",
  "status": "SUCCESS",
  "result": {
    "sha1_hash": "unique-hash",
    "files_processed": [...],
    "processing_summary": {
      "total_files": 2,
      "successful_files": 2,
      "total_size_mb": 15.2
    }
  }
}
```

### 3. List Uploaded Files
**GET** `/idat/list`

List all uploaded file directories.

**Response:**
```json
{
  "directories": [
    {
      "sha1_hash": "unique-hash",
      "file_count": 2,
      "files": ["data.csv", "array.idat"],
      "created_time": 1692876543.123
    }
  ]
}
```

### 4. Remove Files
**DELETE** `/idat/remove/{sha1_hash}`

Remove files associated with a specific SHA1 hash.

**Response:**
```json
{
  "message": "Files with SHA1 hash {hash} removed successfully"
}
```

## Setup and Usage

### 1. Install Dependencies
```bash
uv sync
```

### 2. Start Redis (required for Celery)
```bash
cd docker/docker-redis-commander
docker compose up -d
```

### 3. Start Celery Worker
```bash
uv run celery -A app.celery_tasks worker -l INFO
```

### 4. Start FastAPI Server
```bash
uv run uvicorn app.start_fastapi:app --reload
```

### 5. Test the API
```bash
python test_file_upload.py
```

## File Storage Structure

Files are stored in the following structure:
```
uploads/
├── {sha1_hash_1}/
│   ├── file1.csv
│   └── file2.idat
├── {sha1_hash_2}/
│   ├── data.csv
│   └── array.idat
```

## Celery Task Configuration

The Celery configuration includes:
- **Task Time Limit**: 30 minutes
- **Soft Time Limit**: 25 minutes
- **Task Tracking**: Enabled for progress monitoring
- **JSON Serialization**: For better compatibility

## File Processing

The system performs the following processing on uploaded files:

1. **File Validation**: Checks file extensions (.idat, .csv only)
2. **SHA1 Calculation**: Generates unique identifier from all files
3. **Storage**: Saves files to local directory structure
4. **Analysis**: Performs basic file analysis (size, format, content preview)
5. **Progress Tracking**: Updates task status during processing

## Error Handling

The API handles various error scenarios:
- Invalid file extensions
- Duplicate file uploads
- Processing failures
- Storage errors
- Task monitoring errors

## Extending File Processing

To add custom processing logic, modify the functions in `app/celery_tasks/file_tasks.py`:

- `process_csv_file()`: Add CSV-specific processing
- `process_idat_file()`: Add IDAT-specific processing
- `process_individual_file()`: Add general file processing logic

## Cleanup

A cleanup task is available to remove old files:

```python
from app.celery_tasks.file_tasks import cleanup_old_files

# Remove files older than 30 days
cleanup_old_files.delay(days_old=30)
```

## Example Usage with cURL

```bash
# Upload files
curl -X POST "http://localhost:8000/files/upload" \
  -F "files=@sample.csv" \
  -F "files=@data.idat"

# Check status
curl "http://localhost:8000/files/status/task-id-here"

# List files
curl "http://localhost:8000/files/list"

# Remove files
curl -X DELETE "http://localhost:8000/files/remove/sha1-hash-here"
```

## WebUI

Access the interactive API documentation at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
