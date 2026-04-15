#!/usr/bin/env python3
"""Quick import verification script."""
import sys

try:
    print("Testing imports...")
    from src.infrastructure.youtube.srt_parser import parse_srt
    print("✓ SRT parser imported")

    from src.infrastructure.youtube.fetcher import YouTubeMetadataFetcher
    print("✓ YouTube fetcher imported")

    from src.infrastructure.db.models.youtube import YouTubeVideo, YouTubeSubtitle
    print("✓ YouTube models imported")

    from src.infrastructure.db.repositories.youtube_repo import YouTubeRepository
    print("✓ YouTube repository imported")

    from src.api.schemas.youtube import YouTubePreviewResponse, YouTubeImportResponse
    print("✓ YouTube schemas imported")

    from src.api.routes.youtube import router
    print("✓ YouTube routes imported")

    print("\nAll imports successful!")
    sys.exit(0)
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
