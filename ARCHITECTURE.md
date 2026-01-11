# retroMaid Architecture

## Overview

retroMaid is designed as a modular system with clear separation of concerns. Each component has a specific responsibility and communicates through well-defined interfaces.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                            │
│                       (retromaid.py)                             │
│  Commands: list-systems, scrape, duplicates, status, clear      │
└────────────┬────────────────────────────────────────────────────┘
             │
             ├─────────────────────────────────────────────┐
             │                                             │
             ▼                                             ▼
┌────────────────────────┐                    ┌───────────────────┐
│   Configuration        │                    │   State Manager   │
│   (utils/config.py)    │                    │  (core/state_*.py)│
│                        │                    │                   │
│ - YAML config          │                    │ - Checkpoints     │
│ - .env credentials     │                    │ - Progress track  │
│ - Setting management   │                    │ - Error handling  │
└────────────────────────┘                    └───────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Components                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ ROM Scanner  │  │ XML Manager  │  │ Duplicate Detector │   │
│  │              │  │              │  │                    │   │
│  │ - Find ROMs  │  │ - Parse XML  │  │ - Find dupes      │   │
│  │ - Check meta │  │ - Update XML │  │ - Resolve dupes   │   │
│  │ - Statistics │  │ - Backup     │  │ - Multi-disc      │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
│                                                                  │
│  ┌──────────────┐                                               │
│  │ ROM Hasher   │                                               │
│  │              │                                               │
│  │ - MD5/SHA1   │                                               │
│  │ - CRC32      │                                               │
│  │ - ZIP support│                                               │
│  └──────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Scraper Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────┐      ┌───────────┐  ┌──────────┐       │
│  │ Base Scraper       │◄─────│ScreenScrap│  │TheGamesDB│       │
│  │ (Interface)        │      │           │  │ (planned)│       │
│  │                    │      │- Auth     │  └──────────┘       │
│  │ - search_by_name   │      │- Rate lmt │                     │
│  │ - search_by_hash   │      │- Metadata │  ┌──────────┐       │
│  │ - get_by_id        │      │- Media URL│  │   IGDB   │       │
│  └────────────────────┘      └───────────┘  │ (planned)│       │
│                                              └──────────┘       │
└─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Media Layer                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────┐      ┌───────────────────┐             │
│  │ Media Downloader   │      │ Game Media Manager│             │
│  │                    │      │                   │             │
│  │ - Download images  │◄─────│ - Coordinate DLs │             │
│  │ - Download videos  │      │ - File naming    │             │
│  │ - Error handling   │      │ - Path mgmt      │             │
│  └────────────────────┘      └───────────────────┘             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Utilities                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐            │
│  │  Logger  │  │ Filename │  │   Configuration    │            │
│  │          │  │ Utils    │  │                    │            │
│  │ - Rich   │  │          │  │ - YAML parser      │            │
│  │ - File   │  │ - Sanitiz│  │ - Env vars         │            │
│  │ - Levels │  │ - Extract│  │ - Dot notation     │            │
│  └──────────┘  │ - Similar│  └────────────────────┘            │
│                └──────────┘                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Scraping Workflow

```
User runs: retromaid.py scrape psx
              │
              ▼
      Load Configuration
      (config.yaml, .env)
              │
              ▼
      Initialize Components
      - Scanner
      - Scraper (ScreenScraper)
      - State Manager
              │
              ▼
      Scan ROMs Directory
      - Find all .cue files
      - Load gamelist.xml
      - Identify missing metadata
              │
              ▼
      Check Checkpoint
      - Load previous state
      - Filter processed ROMs
              │
              ▼
   ┌──────────────────────┐
   │  For each ROM file:  │
   └──────────────────────┘
              │
              ├─► Compute ROM Hash (MD5/SHA1)
              │              │
              │              ▼
              ├─► Search by Hash (ScreenScraper)
              │              │
              │              ├─► Match found? ───► Download Media
              │              │                           │
              │              └─► No match               ▼
              │                      │            Update gamelist.xml
              │                      ▼                   │
              ├─► Sanitize Filename                     │
              │              │                           │
              │              ▼                           │
              ├─► Search by Name                        │
              │              │                           │
              │              ├─► Matches found          │
              │              │   │                       │
              │              │   ├─► High confidence    │
              │              │   │   └─► Use result     │
              │              │   │                       │
              │              │   └─► Low confidence     │
              │              │       └─► Ask user       │
              │              │                           │
              │              └─► No matches             │
              │                  └─► Mark as failed     │
              │                                          │
              └─► Update Checkpoint ◄────────────────────┘
                      │
                      ▼
              Save gamelist.xml
              (with backup)
                      │
                      ▼
              Show Summary
              - Successful
              - Failed
              - Skipped
```

## Component Details

### Core Components

#### ROMScanner
- **Purpose**: Discover and analyze ROM files
- **Key Methods**:
  - `scan_system()`: Scan all ROMs in a system directory
  - `get_missing_metadata_games()`: Find ROMs without metadata
  - `find_duplicates()`: Detect duplicate files
  - `get_statistics()`: Generate statistics

#### GameListXML
- **Purpose**: Parse and write Batocera gamelist.xml files
- **Key Methods**:
  - `load()`: Parse existing XML
  - `add_or_update_game()`: Add/update game metadata
  - `save()`: Write XML with optional backup
  - `get_games_missing_metadata()`: Find incomplete entries

#### ROMHasher
- **Purpose**: Compute file hashes for accurate matching
- **Supported Algorithms**: MD5, SHA1, CRC32
- **Features**:
  - Large file support (chunked reading)
  - ZIP file handling (extracts and hashes ROM inside)
  - Multiple hash types simultaneously

#### DuplicateDetector
- **Purpose**: Find and resolve duplicate ROMs
- **Strategies**:
  - `ask`: Interactive user selection
  - `keep_first`: Automatically keep first found
  - `keep_most_complete`: Keep ROM with best metadata
  - `keep_all`: Don't remove any
- **Special Handling**: Multi-disc games (preserves all discs)

### Scraper Layer

#### ScreenScraper
- **API Endpoint**: https://www.screenscraper.fr/api2
- **Authentication**: User credentials + optional dev credentials
- **Rate Limiting**: Built-in throttling to respect API limits
- **Search Methods**:
  - Hash-based (most accurate, requires MD5/SHA1)
  - Name-based (fuzzy matching)
  - ID-based (direct lookup)
- **Media Support**: Box art, screenshots, marquees, videos, logos

### Media Layer

#### MediaDownloader
- **Purpose**: Download images and videos
- **Features**:
  - Streaming downloads for large files
  - Content-type verification
  - Size limits for videos
  - Error recovery

#### GameMediaManager
- **Purpose**: Coordinate media downloads for a game
- **Responsibilities**:
  - File naming (follows Batocera conventions)
  - Directory management (./images/)
  - Batch downloads
  - Path generation (relative paths for XML)

### State Management

#### StateManager
- **Purpose**: Track progress and enable resume
- **Features**:
  - JSON-based checkpoints
  - Per-system state tracking
  - Error logging
  - Auto-save on frequency
- **State Includes**:
  - Processed ROM paths
  - Success/failure counts
  - Error messages
  - Timestamps

## Configuration

### config.yaml Structure

```yaml
roms_path: "/path/to/roms"

scrapers:
  primary: "screenscraper"
  screenscraper:
    username: "..."
    password: "..."
    rate_limit: 20

matching:
  region_priority: ["us", "eu", "jp"]
  language: "en"

duplicates:
  strategy: "ask"

backup:
  enabled: true

resume:
  enabled: true
  checkpoint_file: ".retromaid_checkpoint.json"
```

### Environment Variables (.env)

```env
SCREENSCRAPER_USERNAME=...
SCREENSCRAPER_PASSWORD=...
```

## Error Handling

### Hierarchical Error Management

1. **Component Level**: Each component catches its own errors
2. **State Manager**: Records errors for later review
3. **CLI Level**: Displays user-friendly error messages
4. **Logging**: All errors logged to file for debugging

### Recovery Mechanisms

- **Checkpoints**: Resume from last successful point
- **Backups**: Automatic XML backups before changes
- **Retry Logic**: Rate limit handling with exponential backoff
- **Graceful Degradation**: Continue on individual failures

## Extension Points

### Adding New Scrapers

1. Inherit from `BaseScraper`
2. Implement required methods:
   - `search_by_name()`
   - `search_by_hash()`
   - `get_game_by_id()`
3. Register in configuration

### Adding New Systems

1. Update `SYSTEM_EXTENSIONS` in `core/scanner.py`
2. Update `SYSTEM_ID_MAP` in scraper implementations
3. Test with sample ROMs

### Custom Workflows

The modular design allows creating custom workflows by:
- Using components independently
- Creating new CLI commands
- Building web interfaces
- Integrating with other tools

## Performance Considerations

### Optimization Strategies

1. **Hash Computation**:
   - Chunked reading for large files
   - Cached results in ROMFile objects

2. **Network Requests**:
   - Rate limiting prevents throttling
   - Session reuse for connections
   - Streaming downloads for media

3. **State Management**:
   - Batch saves (configurable frequency)
   - In-memory state with periodic persistence

4. **XML Processing**:
   - lxml for fast parsing
   - Pretty-print only on save

## Security

### Credential Management

- Environment variables for sensitive data
- No credentials in version control (.gitignore)
- Optional credential encryption (future)

### File System Safety

- Automatic backups before modifications
- Relative paths for portability
- Directory creation with error handling
- Path validation

## Future Enhancements

### Planned Features

1. **Web UI**: Browser-based interface
2. **Multiple Scrapers**: Fallback chain
3. **Batocera Integration**: Native script support
4. **Docker**: Containerized deployment
5. **Scheduling**: Automated updates
6. **Statistics Dashboard**: Visual progress tracking
7. **Bulk Operations**: Multi-system processing
8. **Testing**: Comprehensive test suite

### Scalability

Current design supports:
- Thousands of ROMs per system
- Dozens of systems
- Multiple concurrent users (with separate configs)

For larger deployments, consider:
- Database backend (vs. XML)
- Distributed processing
- Caching layer
- Queue-based scraping

## Development Guidelines

### Code Organization

- **Separation of Concerns**: Each module has one responsibility
- **Dependency Injection**: Components receive dependencies
- **Interface Contracts**: Base classes define interfaces
- **Type Hints**: Python typing for clarity
- **Documentation**: Docstrings for all public methods

### Testing Strategy

- Unit tests for utilities and core logic
- Integration tests for scrapers
- End-to-end tests for workflows
- Mock external APIs

### Contributing

See [README.md](README.md) for contribution guidelines.
