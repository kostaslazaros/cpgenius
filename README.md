# CpGenius

## Features

- **File Upload API**: Upload multiple .idat and .csv files
- **SHA1 Identification**: Files stored with unique SHA1 hash identifiers
- **Asynchronous Processing**: Large files processed using Celery tasks
- **Progress Monitoring**: Real-time task status tracking
- **File Management**: List, view, and remove uploaded files
- **Duplicate Detection**: Prevents duplicate uploads based on file content

## Quick Start

### 1. Start Redis

```bash
cd docker/docker-redis-commander
docker compose up -d
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Start Celery Worker

```bash
uv run celery -A app.celery_tasks worker -l INFO
```

### 4. Start FastAPI Server

```bash
uv run uvicorn app.start_fastapi:app --host 0.0.0.0 --port 8001 --reload
```

### 5. Test the API

```bash
# Run the demo script
uv run python demo_api.py

# Or test with curl
curl -X POST "http://localhost:8000/files/upload"
  -F "files=@your_file.csv"
  -F "files=@your_file.idat"
```

## API Endpoints

- **POST** `/files/upload` - Upload .idat and .csv files
- **GET** `/files/status/{task_id}` - Check processing status
- **GET** `/files/list` - List all uploaded files
- **DELETE** `/files/remove/{sha1_hash}` - Remove files by SHA1 hash

## Documentation

- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Detailed Guide**: [FILE_UPLOAD_API.md](FILE_UPLOAD_API.md)

## File Storage

Files are stored in `uploads/{sha1_hash}/` directories, where each directory contains all files that hash to the same SHA1 value.

## Test Legacy Celery

```bash
uv run python -m app.test_celery
```

This will create a file `test.txt` containing "Hello, World!"

## Stop Services

```bash
# Stop Redis
cd docker/docker-redis-commander
docker compose down

# Stop Celery worker: Ctrl+C
# Stop FastAPI server: Ctrl+C
```

## From vscode you can

- ctrl + shift + p simple browser in order to open the simple browser :-)

To stop old celery workers

```bash
pkill -f "celery.*worker"
```

##### To install tailwind cli run

```bash
npm i
```

## Fast Start

### 1. Celery redis backend

```bash
cd docker/docker-redis-commander
docker compose up -d
docker compose down
```

### 2. Celery worker start

```bash
uv run celery -A app.celery_tasks worker -l INFO
```

### 3. Tailwind cli watcher

```bash
npx @tailwindcss/cli -i input.css -o ./static/css/output.css --watch
```

### 4. Fastapi start

```bash
uv run uvicorn app.start_fastapi:app --host 0.0.0.0 --port 8001 --reload
```

### 5. ngrok sharing (Install first with: npm i ngrok -g)

```bash
ngrok http 8001
```

## Developing with vscode

- **ctrl + shift + p > Tasks: Run Task** (select tasks to run)
- **ctrl + shift + p > Tasks: Terminate Task** (to terminate)
