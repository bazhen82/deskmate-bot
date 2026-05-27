"""
Setup script for the Personal Assistant Bot.
"""

from pathlib import Path
import os
import sys


def create_env_file():
    """Create .env file from template if it doesn't exist."""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if env_file.exists():
        print("✓ .env file already exists")
        return
    
    if not env_example.exists():
        print("⚠ .env.example not found")
        return
    
    # Copy example to .env
    content = env_example.read_text()
    env_file.write_text(content)
    print("✓ Created .env file from template")
    print("⚠ Don't forget to add your API keys!")


def create_directories():
    """Create necessary directories."""
    directories = [
        "data",
        "data/documents",
        "data/chroma_db"
    ]
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")


def check_dependencies():
    """Check if required dependencies are installed."""
    print("\nChecking dependencies...")
    
    required = [
        "aiogram",
        "openai",
        "langchain",
        "chromadb",
        "pydub",
        "aiofiles"
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package}")
            missing.append(package)
    
    if missing:
        print(f"\n⚠ Missing packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True


def check_ffmpeg():
    """Check if FFmpeg is installed."""
    print("\nChecking FFmpeg...")
    import subprocess
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ FFmpeg is installed")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("✗ FFmpeg not found")
    print("Please install FFmpeg for audio processing:")
    print("  Windows: https://ffmpeg.org/download.html")
    print("  Linux: sudo apt-get install ffmpeg")
    print("  Mac: brew install ffmpeg")
    return False


def main():
    """Main setup function."""
    print("=" * 60)
    print("Personal Assistant Bot - Setup")
    print("=" * 60)
    
    # Create directories
    print("\n1. Creating directories...")
    create_directories()
    
    # Create .env file
    print("\n2. Setting up environment...")
    create_env_file()
    
    # Check dependencies
    print("\n3. Checking Python dependencies...")
    deps_ok = check_dependencies()
    
    # Check FFmpeg
    print("\n4. Checking FFmpeg...")
    ffmpeg_ok = check_ffmpeg()
    
    # Summary
    print("\n" + "=" * 60)
    print("Setup Summary")
    print("=" * 60)
    
    if deps_ok and ffmpeg_ok:
        print("✓ Setup complete!")
        print("\nNext steps:")
        print("1. Edit .env file and add your API keys")
        print("2. Place documents in data/documents/ (optional)")
        print("3. Run: python main.py")
    else:
        print("⚠ Setup incomplete. Please fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()

