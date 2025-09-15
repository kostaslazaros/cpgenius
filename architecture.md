# CpGenius – Architecture Diagrams

This document provides ready-to-embed Mermaid diagrams for CpGenius. Paste this file into `docs/architecture.md` in your repo to render on GitHub.

## 1) System Overview

```mermaid
graph TD
  %% Users
  U[User]

  %% App boundary
  subgraph APP[cpgenius application]
    FAPI[FastAPI app<br/>`app.start_fastapi:app`]
    CEL[Celery Worker<br/>`app.celery_tasks`]
    TEMPL[Templates]
    STATIC[Static Assets]
  end

  %% Infra / external services
  subgraph INFRA[Infrastructure]
    REDIS[(Redis<br/>Broker + Result Backend)]
    FS[(File Storage)]
    RCMD[Redis Commander]
    TWC[Tailwind CLI]
  end

  %% Flows
  U -->|HTTP requests| FAPI
  FAPI -->|Serve HTML| TEMPL
  FAPI -->|Serve CSS/JS| STATIC

  %% Tasking
  FAPI -->|Enqueue task & query state| REDIS
  CEL -->|Consume tasks & update state| REDIS
  FAPI -->|Write/Read files| FS
  CEL -->|Process files| FS

  %% Dev-time helpers
  TWC -->|Generates| STATIC
  U -.inspect.-> RCMD
```

## 2) Request–Task Flow (Upload & Progress)

```mermaid
sequenceDiagram
  participant C as Client
  participant A as FastAPI (/files/*)
  participant R as Redis (broker+backend)
  participant W as Celery Worker
  participant S as File Storage (uploads/{sha1}/)

  Note over C,A: POST /files/upload (multiple .idat /.csv)
  C->>A: Upload files (multipart form)
  A->>S: Save files in uploads/{sha1}/
  A->>A: Compute SHA1 / detect duplicates
  A->>R: Enqueue process task (task_id)
  A-->>C: 202 Accepted {task_id}

  Note over C,A: Poll GET /files/status/{task_id}
  C->>A: Status request
  A->>R: Fetch task state/progress
  A-->>C: {state, progress, result?}

  Note over W: Asynchronous processing
  R-->>W: Deliver task
  W->>S: Read files from uploads/{sha1}/
  W->>W: Process / parse / compute
  W->>R: Update status / set result
```

## 3) File Management Endpoints (Happy Paths)

```mermaid
sequenceDiagram
  participant C as Client
  participant A as FastAPI
  participant S as File Storage

  rect rgb(50,50,60)
  Note over C,A: List files
  C->>A: GET /files/list
  A->>S: Scan uploads/*
  A-->>C: [{sha1, filenames, sizes, mtime...}]
  end

  rect rgb(30,50,60)
  Note over C,A: Remove by SHA1
  C->>A: DELETE /files/remove/sha1
  A->>S: Delete directory uploads/sha1/
  A-->>C: {ok:true}
  end
```

## 4) Deployment (Local Dev)

```mermaid
graph LR
  subgraph Dev Host
    subgraph Docker
      DREDIS[Container: redis]
      DRCMD[Container: redis-commander]
    end

    UVI[uvicorn<br/>FastAPI server]
    CW[celery worker]
    TW[Tailwind CLI --watch]
  end

  C[Browser] -->|http://localhost:8001| UVI
  UVI <-->|enqueue/query| DREDIS
  CW <-->|consume/update| DREDIS
  C -.optional debug UI.-> DRCMD
```

## 5) Module Interaction (Minimal)

```mermaid
graph TD
  subgraph Server
    SF[app.start_fastapi:app]
    RT[Routes: /files/*]
    ST[Storage Utilities]
  end

  subgraph Workers
    CT[app.celery_tasks]
  end

  subgraph Infra
    RD[(Redis)]
    FS[(uploads/sha1/)]
  end

  SF --> RT
  RT --> ST
  RT --> RD
  CT --> RD
  ST --> FS
  CT --> FS
```

## 6) Data Organization

```mermaid
classDiagram
  class UploadGroup {
    +sha1: string
    +dir: string "uploads/sha1"
    +files: File[]
    +created_at: datetime
  }
  class File {
    +name: string
    +size: int
    +type: string
    +path: string
  }
  UploadGroup "1" o-- "*" File : contains
```
