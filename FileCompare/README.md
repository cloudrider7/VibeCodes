# Titan File Deduplicator

Titan is a high-performance, modern file deduplication tool designed to identify and manage duplicate files across local and network drives. Built with [Flet](https://flet.dev) and Python, it prioritizes speed, safety, and user experience.

## Features

- **High-Speed Scanning**: Multi-threaded scanning engine with support for 500,000+ files.
- **Smart Hashing**: Adapts hashing strategy (xxHash, MD5, SHA256, Blake3) based on system performance.
- **Safety First**: "Protected Files" mode and read-only safeguards preventing accidental deletion of master copies.
- **Modern UI**: Dark-themed, responsive interface with virtualization for instant rendering of massive result sets.
- **Drive Awareness**: Automatically detects SSD vs HDD to optimize thread count and IO patterns.
- **Flexible Configuration**: 
    - Ignore custom folders/extensions.
    - Set minimum file size filters (KB/MB/GB/TB).
    - Persistent settings.

## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python main.py
```

## Requirements
- Python 3.8+
- Windows (Optimized), macOS, or Linux

## License
Proprietary / Internal Use Only
