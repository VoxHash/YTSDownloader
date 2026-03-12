# 🎬 YTSDownloader v0.0.1

> **YTSDownloader** - A powerful desktop tool for downloading short-form videos from YouTube, Instagram, Facebook, and TikTok with automatic watermarking support. Built with PyQt6 and designed for content creators who need bulk downloads with brand protection.

[![Version](https://img.shields.io/badge/version-0.0.1-blue.svg)](https://github.com/VoxHash/YTSDownloader)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://python.org/)
[![PyQt6](https://img.shields.io/badge/pyqt6-6.0+-blue.svg)](https://pypi.org/project/PyQt6/)

## ✨ Features

### 🎥 **Multi-Platform Support**
- **YouTube**: Download Shorts, videos, and entire channel content
- **Instagram**: Extract Reels, posts, and profile videos
- **Facebook**: Download videos from pages and posts
- **TikTok**: Download videos from profiles and individual posts
- **Bulk Download**: Extract and download multiple videos in one operation

### 🎨 **Watermark & Branding**
- **Custom Watermark**: Add your unique PNG watermark to all downloaded videos
- **Automatic Processing**: Watermark is automatically applied during download
- **Content Protection**: Protect your content with branded watermarks
- **Position Control**: Watermark positioning and sizing options

### 🚀 **Professional Features**
- **Authentication Support**: Browser cookies or cookie file authentication
- **JavaScript Runtime**: Node.js runtime support for enhanced extraction
- **Progress Tracking**: Real-time progress bars for downloads and processing
- **Metadata Caching**: Smart caching system for faster repeated downloads
- **Format Selection**: Choose between WebM and MP4 output formats
- **Theme Support**: Customizable dark themes via `themes/` directory

### 🎯 **User Experience**
- **Modern GUI**: Clean PyQt6 interface with custom title bar
- **Tab-Based Interface**: Separate tabs for each platform
- **Logging System**: Detailed logs for troubleshooting
- **Error Handling**: Graceful error handling with informative messages
- **Original Names Tracking**: Saves original video titles for reference

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ (for development)
- FFmpeg installed and available in PATH
- PyQt6 and dependencies

### Installation

#### Method 1: Python Installation (Recommended)

1. **Clone Repository**
   ```bash
   git clone https://github.com/VoxHash/YTSDownloader.git
   cd YTSDownloader
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg**
   - **Windows**: Download from [FFmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` (Debian/Ubuntu) or `sudo dnf install ffmpeg` (Fedora)

5. **Configure Settings**
   - Copy `config.ini` and update settings:
     - `THEME`: Choose theme from `themes/` directory
     - `COOKIES_FROM_BROWSER`: Browser name (e.g., `chrome`, `firefox`) for authentication
     - `COOKIES_FILE`: Path to cookies file (alternative to browser cookies)
     - `JS_RUNTIME`: JavaScript runtime (e.g., `node`)
     - `JS_RUNTIME_PATH`: Path to JavaScript runtime executable

6. **Run YTSDownloader**
   ```bash
   python main.py
   ```

## 🎯 Usage

### Basic Workflow

1. **Launch Application**
   ```bash
   python main.py
   ```

2. **Select Platform Tab**
   - Choose the appropriate tab: YouTube, Instagram, Facebook, or TikTok

3. **Configure Settings**
   - **Output Folder**: Click "Browse" to select where videos will be saved
   - **Platform URL**: Enter channel/profile URL or individual video URL
   - **Watermark (Optional)**: Browse and select PNG watermark image
   - **Output Format**: Choose WebM or MP4

4. **Start Download**
   - Click "Start Download" button
   - Monitor progress via progress bar
   - Check logs tab for detailed information

### Platform-Specific Usage

#### YouTube
- **Channel URL**: `https://www.youtube.com/@channelname` or `https://www.youtube.com/c/channelname`
- **Video URL**: `https://www.youtube.com/watch?v=VIDEO_ID`
- **Shorts URL**: `https://www.youtube.com/shorts/VIDEO_ID`
- Downloads from both `/videos` and `/shorts` tabs automatically

#### Instagram
- **Profile URL**: `https://www.instagram.com/username/`
- **Post URL**: `https://www.instagram.com/p/POST_ID/`
- **Reel URL**: `https://www.instagram.com/reel/REEL_ID/`

#### Facebook
- **Page URL**: `https://www.facebook.com/pagename`
- **Post URL**: `https://www.facebook.com/pagename/posts/POST_ID`
- **Video URL**: `https://www.facebook.com/watch/?v=VIDEO_ID`

#### TikTok
- **Profile URL**: `https://www.tiktok.com/@username`
- **Video URL**: `https://www.tiktok.com/@username/video/VIDEO_ID`

### Authentication Setup

#### Method 1: Browser Cookies (Recommended)
1. Open `config.ini`
2. Set `COOKIES_FROM_BROWSER` to your browser:
   ```
   COOKIES_FROM_BROWSER = chrome
   ```
   Supported: `chrome`, `firefox`, `edge`, `opera`, `brave`

#### Method 2: Cookie File
1. Export cookies from your browser (use browser extension)
2. Save as `cookies.txt` or `cookies.json`
3. Set `COOKIES_FILE` in `config.ini`:
   ```
   COOKIES_FILE = /path/to/cookies.txt
   ```

#### Method 3: JavaScript Runtime
1. Install Node.js
2. Set `JS_RUNTIME` and `JS_RUNTIME_PATH` in `config.ini`:
   ```
   JS_RUNTIME = node
   JS_RUNTIME_PATH = /path/to/node
   ```

### Watermark Configuration

1. **Prepare Watermark**
   - Use PNG format with transparency
   - Recommended size: 200-400px width
   - Keep file size reasonable (< 500KB)

2. **Apply Watermark**
   - Click "Browse" next to "Watermark (PNG)"
   - Select your watermark image
   - Watermark will be automatically applied to all downloaded videos

## 🔧 Configuration

### Config.ini Settings

| Setting | Description | Default | Example |
|---------|-------------|---------|---------|
| `THEME` | Theme directory name | `DarkFreeze` | `DarkFreeze` |
| `COUNT_TIMER_ONGOING` | Timer count for ongoing operations | `2` | `2` |
| `COOKIES_FROM_BROWSER` | Browser name for cookie extraction | (empty) | `chrome` |
| `COOKIES_FILE` | Path to cookies file | (empty) | `/path/to/cookies.txt` |
| `JS_RUNTIME` | JavaScript runtime name | `node` | `node` |
| `JS_RUNTIME_PATH` | Path to JavaScript runtime | (empty) | `/usr/bin/node` |

### Theme Customization

1. **Create Theme Directory**
   ```bash
   mkdir themes/MyTheme
   ```

2. **Add Style File**
   - Copy `themes/DarkFreeze/style.qss` as reference
   - Customize colors, fonts, and styles
   - Update `config.ini` to use your theme

3. **Add Theme Assets**
   - Place images in `themes/MyTheme/images/`
   - Update paths in `style.qss` if needed

## 📁 Supported Formats

### Input Formats
- **YouTube**: All formats supported by yt-dlp
- **Instagram**: Reels, posts, IGTV videos
- **Facebook**: Page videos, post videos
- **TikTok**: Profile videos, individual videos

### Output Formats
- **WebM**: Web-optimized format (default)
- **MP4**: Universal compatibility format

## 🛠️ Development

### Building from Source

1. **Clone Repository**
   ```bash
   git clone https://github.com/VoxHash/YTSDownloader.git
   cd YTSDownloader
   ```

2. **Setup Development Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

3. **Run Development Version**
   ```bash
   python main.py
   ```

### Project Structure
```
YTSDownloader/
├── main.py                    # Main application (670 lines)
├── requirements.txt           # Python dependencies
├── config.ini                # Configuration file
├── LICENSE                    # MIT License
├── README.md                  # Project overview
├── CHANGELOG.md              # Version history
├── CONTRIBUTING.md           # Contribution guidelines
├── ROADMAP.md                # Development roadmap
├── DEVELOPMENT_GOALS.md      # Development goals
├── GITHUB_TOPICS.md          # GitHub topics
├── themes/                    # Theme directory
│   └── DarkFreeze/           # Default theme
│       ├── style.qss        # Stylesheet
│       └── images/          # Theme assets
└── docs/                     # Documentation
    ├── index.md             # Documentation index
    ├── getting-started.md   # Getting started guide
    ├── configuration.md     # Configuration guide
    ├── usage.md             # Usage guide
    └── troubleshooting.md  # Troubleshooting guide
```

## 🔧 Troubleshooting

### Common Issues

**"Sign in to confirm you're not a bot" error:**
- Set up authentication via `COOKIES_FROM_BROWSER` or `COOKIES_FILE` in `config.ini`
- Ensure cookies are valid and not expired
- Try using JavaScript runtime (`JS_RUNTIME`)

**"No supported JavaScript runtime" warning:**
- Install Node.js and set `JS_RUNTIME_PATH` in `config.ini`
- Or ignore if downloads work without it (some formats may be missing)

**FFmpeg not found:**
- Install FFmpeg and ensure it's in your system PATH
- Verify installation: `ffmpeg -version`

**Watermark not appearing:**
- Ensure watermark is PNG format with transparency
- Check file path is correct
- Verify watermark file is readable

**Downloads failing:**
- Check internet connection
- Verify URL format is correct
- Check authentication settings
- Review logs tab for detailed error messages

**Theme not loading:**
- Verify theme directory exists in `themes/`
- Check `style.qss` file exists in theme directory
- Ensure `THEME` setting in `config.ini` matches directory name

### Getting Help

- **Issues**: [GitHub Issues](https://github.com/VoxHash/YTSDownloader/issues)
- **Discussions**: [GitHub Discussions](https://github.com/VoxHash/YTSDownloader/discussions)
- **Documentation**: See `docs/` folder for detailed guides
- **Creator**: VoxHash LLC

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for detailed version history and upcoming features.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📚 Documentation

- **[Changelog](CHANGELOG.md)** - Version history and upcoming features
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute to YTSDownloader
- **[Roadmap](ROADMAP.md)** - Development roadmap and future plans
- **[Development Goals](DEVELOPMENT_GOALS.md)** - Detailed development objectives
- **[GitHub Topics](GITHUB_TOPICS.md)** - Repository topics and tags
- **[Getting Started](docs/getting-started.md)** - Detailed getting started guide
- **[Configuration](docs/configuration.md)** - Configuration options
- **[Usage Guide](docs/usage.md)** - Detailed usage instructions
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎉 Acknowledgments

- **yt-dlp** - Powerful video downloader backend
- **PyQt6** - Cross-platform GUI framework
- **moviepy** - Video processing and watermarking
- **FFmpeg** - Media processing backend
- **Community** - Feedback and contributions

---

**Made with ❤️ by VoxHash LLC**

*YTSDownloader - Download and protect your content with ease!* 🎬✨
