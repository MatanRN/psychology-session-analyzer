# Psychology Session Analyzer

A distributed microservices system for analyzing psychology therapy sessions. Upload a video recording of a therapy session, and the system automatically extracts audio, transcribes the conversation with speaker diarization, and uses LLM-powered analysis to generate insights about topics, emotions, sentiment, and patient relationships.


### Processing Pipeline

1. **Upload**: Client uploads an MP4 video of a therapy session via REST API
2. **Storage**: Video is stored in MinIO object storage with structured path naming
3. **Audio Extraction**: Worker extracts audio track from video using MoviePy
4. **Transcription**: AssemblyAI transcribes audio with speaker diarization
5. **Analysis**: Gemini LLM analyzes transcript for topics, emotions, sentiment, and relationships
6. **Persistence**: Insights are stored in PostgreSQL for later retrieval
7. **Query**: Clients can retrieve session analysis via REST API

### Event-Driven Communication

Services communicate via RabbitMQ using a topic exchange pattern:

```
video.upload.completed  ──▶  Audio Extractor
audio.extraction.completed  ──▶  Audio Transcriber
audio.transcription.completed  ──▶  Transcript Analyzer
analysis.completed  ──▶  (Pipeline complete)
```

Each service uses quorum queues with dead-letter exchanges for reliable message processing and automatic retry with DLQ routing for failed messages.

## Services

### session-upload

**Purpose**: HTTP entry point for uploading therapy session videos.

**Technology**: FastAPI

**Responsibilities**:
- Accept MP4 video uploads with session metadata (date, patient name)
- Generate unique session ID
- Store video in MinIO with structured path: `{year}/{month}/{day}/{session_id}/video/{name}.mp4`
- Publish `video.upload.completed` event to trigger processing pipeline

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| POST | `/sessions/upload` | Upload session video with metadata |

**Dependencies**: MinIO, RabbitMQ

---

### audio-extractor

**Purpose**: Extract audio tracks from uploaded video files.

**Technology**: Worker process with RabbitMQ consumer

**Responsibilities**:
- Consume `video.upload.completed` events
- Download video from MinIO
- Extract audio using MoviePy, output as WAV
- Upload audio to MinIO at `{year}/{month}/{day}/{session_id}/audio/{name}.wav`
- Publish `audio.extraction.completed` event

**Domain Logic** (`AudioExtractor`):
- Uses MoviePy's `VideoFileClip` to extract audio
- Writes to temporary files for processing
- Handles cleanup of temporary resources

**Dependencies**: MinIO, RabbitMQ

---

### audio-transcriber

**Purpose**: Convert audio to text with speaker identification.

**Technology**: Worker process with RabbitMQ consumer

**Responsibilities**:
- Consume `audio.extraction.completed` events
- Download audio from MinIO
- Transcribe using AssemblyAI with speaker diarization
- Build formatted transcript with speaker labels
- Upload transcript to MinIO at `{year}/{month}/{day}/{session_id}/transcription/{name}.txt`
- Publish `audio.transcription.completed` event

**Domain Logic** (`TranscriptBuilder`):
- Formats utterances as `Speaker A: {text}`
- Preserves speaker separation for downstream analysis

**External Integration**: AssemblyAI API for speech-to-text with speaker diarization

**Dependencies**: MinIO, RabbitMQ, AssemblyAI

---

### transcript-analyzer

**Purpose**: Analyze transcripts using LLM to extract psychological insights.

**Technology**: Worker process with RabbitMQ consumer

**Responsibilities**:
- Consume `audio.transcription.completed` events
- Download transcript from MinIO
- Analyze using Gemini LLM with structured output
- Cache analysis results in Redis
- Extract insights: topics, emotions, sentiment, relationships
- Persist session and insights to PostgreSQL
- Publish `analysis.completed` event

**Domain Logic** (`TranscriptAnalyzer`):
- Identifies therapist vs patient roles from conversation patterns
- Extracts per-utterance metadata: topic, emotion, sentiment score
- Identifies relationships mentioned by patient (family, friends, etc.)
- Separates positive and negative topics for summary

**LLM Analysis Output**:
```json
{
  "speaker_roles": { "speaker_a": "therapist", "speaker_b": "patient" },
  "utterances": [
    {
      "id": 1,
      "speaker": "Speaker A",
      "role": "therapist",
      "text": "How are you feeling today?",
      "topic": ["emotional state"],
      "emotion": ["neutral"],
      "sentiment_score": 0.0
    }
  ],
  "relationships": [
    {
      "name": "Sarah",
      "relationship": "mother",
      "sentiment_score": -0.3,
      "mentions": 5
    }
  ]
}
```

**Dependencies**: MinIO, RabbitMQ, Redis, PostgreSQL, Gemini API

---

### session-api

**Purpose**: REST API for querying analyzed sessions.

**Technology**: FastAPI

**Responsibilities**:
- List all analyzed sessions with patient info
- Retrieve detailed analysis for a specific session

**Endpoints**:
| Method | Path | Description |
|--------|------|-------------|
| GET | `/sessions` | List all sessions with basic info |
| GET | `/sessions/{session_id}` | Get full analysis for a session |

**Response Model** (Session Detail):
```json
{
  "session_id": "uuid",
  "patient_first_name": "John",
  "patient_last_name": "Doe",
  "session_date": "2025-01-15",
  "insights": {
    "positive_topics": ["self-improvement", "relationships"],
    "negative_topics": ["anxiety", "work stress"],
    "sentiment_scores": [0.2, -0.4, 0.1, ...],
    "patient_relationships": [
      { "name": "Sarah", "relationship": "mother", "sentiment_score": -0.3, "mentions": 5 }
    ]
  }
}
```

**Dependencies**: PostgreSQL

---

### common

**Purpose**: Shared library for cross-cutting concerns.

**Contents**:
- `config.py`: Configuration models (MinIO, RabbitMQ, Queue settings)
- `db_models.py`: SQLModel entities (Patient, Session, SessionInsights)
- `exceptions.py`: Custom exception hierarchy
- `logging.py`: Structured logging setup
- `infrastructure/interfaces/`: Abstract interfaces for storage and messaging

**Usage**: Installed as a local dependency in all services via PDM workspace.

## Infrastructure

| Service | Image | Purpose | Ports |
|---------|-------|---------|-------|
| RabbitMQ | `rabbitmq:4.2.1-management-alpine` | Message broker | 5672 (AMQP), 15672 (Management UI) |
| MinIO | `minio/minio:latest` | Object storage | 9000 (API), 9001 (Console) |
| Redis | `redis/redis-stack:latest` | Caching layer | 6379 (Redis), 8001 (RedisInsight) |
| PostgreSQL | `postgres:17-alpine` | Relational database | 5432 |
| Datadog Agent | `gcr.io/datadoghq/agent:7` | Observability | - |

## Data Model

```
┌─────────────┐       ┌─────────────┐       ┌──────────────────┐
│   Patient   │       │   Session   │       │ SessionInsights  │
├─────────────┤       ├─────────────┤       ├──────────────────┤
│ id (PK)     │◀──────│ patient_id  │       │ session_id (PK)  │
│ first_name  │       │ id (PK)     │──────▶│ positive_topics  │
│ last_name   │       │ session_date│       │ negative_topics  │
└─────────────┘       └─────────────┘       │ sentiment_scores │
                                            │ patient_relations│
                                            └──────────────────┘
```

## Object Storage Structure

```
sessions/
└── {year}/
    └── {month}/
        └── {day}/
            └── {session_id}/
                ├── video/
                │   └── {firstname}-{lastname}-{date}.mp4
                ├── audio/
                │   └── {firstname}-{lastname}-{date}.wav
                └── transcription/
                    └── {firstname}-{lastname}-{date}.txt
```

## Configuration

All services are configured via environment variables:

### Common Variables
| Variable | Description |
|----------|-------------|
| `MINIO_USER` | MinIO access key |
| `MINIO_PASSWORD` | MinIO secret key |
| `MINIO_ENDPOINT` | MinIO server address |
| `RABBITMQ_HOST` | RabbitMQ server address |
| `RABBITMQ_USER` | RabbitMQ username |
| `RABBITMQ_PASSWORD` | RabbitMQ password |

### Service-Specific Variables
| Variable | Service | Description |
|----------|---------|-------------|
| `ASSEMBLYAI_API_KEY` | audio-transcriber | AssemblyAI API key |
| `GEMINI_API_KEY` | transcript-analyzer | Google Gemini API key |
| `REDIS_HOST` | transcript-analyzer | Redis server address |
| `POSTGRES_HOST` | transcript-analyzer, session-api | PostgreSQL host |
| `POSTGRES_PORT` | transcript-analyzer, session-api | PostgreSQL port |
| `POSTGRES_USER` | transcript-analyzer, session-api | PostgreSQL username |
| `POSTGRES_PASSWORD` | transcript-analyzer, session-api | PostgreSQL password |
| `POSTGRES_DB` | transcript-analyzer, session-api | PostgreSQL database name |

### Datadog Integration
| Variable | Description |
|----------|-------------|
| `DD_API_KEY` | Datadog API key |
| `DD_AGENT_HOST` | Datadog agent hostname |
| `DD_SERVICE` | Service name for Datadog |
| `DD_LOGS_INJECTION` | Enable log injection |

## Running the System

### Prerequisites
- Docker and Docker Compose
- API keys for AssemblyAI and Google Gemini
- (Optional) Datadog API key for observability

### Setup

1. Create a `.env` file with required variables:
```bash
MINIO_USER=minioadmin
MINIO_PASSWORD=minioadmin
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
ASSEMBLYAI_API_KEY=your_key
GEMINI_API_KEY=your_key
DD_API_KEY=your_key  # optional
```

2. Start all services:
```bash
docker-compose up --build
```

3. Upload a session:
```bash
curl -X POST http://localhost:8000/sessions/upload \
  -F "file=@session.mp4" \
  -F "date_of_session=2025-01-15" \
  -F "patient_first_name=John" \
  -F "patient_last_name=Doe"
```

4. Query results:
```bash
# List all sessions
curl http://localhost:8080/sessions

# Get specific session
curl http://localhost:8080/sessions/{session_id}
```

## Development

This project uses PDM for dependency management with a workspace configuration.

```bash
# Install dependencies for all services
pdm install

# Run a specific service locally
cd services/session-upload
pdm run python main.py
```

## Error Handling

- **Message Retries**: Failed messages are retried up to 3 times (configurable via `max_delivery_count`)
- **Dead Letter Queues**: Messages that exceed retry limit are routed to service-specific DLQs
- **Caching**: LLM analysis results are cached in Redis to avoid redundant API calls
- **Structured Logging**: All services use JSON-formatted logs with Datadog integration

## License

MIT

