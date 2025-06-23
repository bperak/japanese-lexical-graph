# CHANGELOG

All notable changes to the Japanese Lexical Graph project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2025-06-24

### Added
- **Production Deployment Infrastructure**
  - Added `gunicorn==21.2.0` to requirements.txt for production WSGI server
  - Created `start_production.sh` script for launching production server on port 5000
  - Created `stop_production.sh` script for graceful server shutdown
  - Created `production_status.sh` script for comprehensive server monitoring
  - Added `japanese-lexical-graph.service` systemd service file for auto-start capability
  - Implemented 4-worker Gunicorn configuration with optimized settings
  - Added comprehensive logging with separate access and error logs
  - Implemented PID file management for process control
  - Added daemon mode for background operation independent of terminal sessions

## [Previous - 2024-12-23]

### Added
- **Japanese Readability Analysis Integration**
  - Added `jreadability` library (v1.1.4) for Japanese text difficulty assessment
  - Created `readability_helper.py` with comprehensive readability analysis functionality
  - Added `/analyze-readability` and `/analyze-exercise-readability` API endpoints
  - Implemented 6-level proficiency scale (Lower-elementary to Upper-advanced)
  - Added color-coded readability badges in the exercise UI
  - Integrated automatic readability analysis with AI-generated exercise content

- **Enhanced User Interface**
  - Added readability display components in exercise controls
  - Implemented color-coded difficulty indicators with smooth animations
  - Added cache-busting for CSS files to prevent browser caching issues
  - Enhanced exercise workflow with automatic difficulty assessment

- **Comprehensive Testing**
  - Created 27 unit tests for readability functionality (`tests/unit/test_readability_helper.py`)
  - Added API endpoint tests for readability analysis
  - Created interactive demo script (`demo_readability.py`)
  - All tests passing with comprehensive coverage

- **Documentation Updates**
  - Created `JREADABILITY_INTEGRATION_SUMMARY.md` with detailed implementation overview
  - Updated `README.md` with readability analysis features
  - Enhanced `PLANNING.md` with readability API endpoints and dependencies
  - Updated `GETTING_STARTED.md` with readability feature usage instructions
  - Created this CHANGELOG.md for tracking project changes

### Changed
- Updated `requirements.txt` to include `jreadability==1.1.4`
- Modified `app.py` to include readability analysis endpoints
- Enhanced exercise generation workflow to include automatic readability assessment
- Updated HTML templates with readability display components
- Added CSS styling for readability badges and difficulty indicators
- Enhanced JavaScript with readability analysis functions

### Fixed
- Implemented cache-busting for CSS files to resolve UI update issues
- Improved error handling for readability analysis when library is unavailable
- Enhanced graceful degradation for systems without Japanese text analysis capabilities

### Documentation
- **Academic Paper**: Updated `documents/paper.md` with readability assessment methodology
- **Technical Architecture**: Enhanced system documentation with readability components
- **User Guides**: Updated getting started and troubleshooting sections
- **API Documentation**: Documented new readability analysis endpoints

### Testing
- **Unit Tests**: 27 comprehensive test cases for readability functionality
- **Integration Tests**: API endpoint testing for readability analysis
- **Demo Scripts**: Interactive demonstration of readability features
- **Error Handling**: Testing for library availability and edge cases

## [Previous Versions]

### Completed Features (Historical)
- **Task FEAT-003**: Selectable LLM model for Gemini API calls (Completed 2025-05-18)
- **Task ATTR-001**: Renamed JLPT attribute to old_JLPT across all nodes (Completed 2025-06-24)
- **Task BUGFIX-004**: Normalized edge 'weight' attribute after graph load (Completed 2025-05-18)
- **Task BUGFIX-005**: Keep in-memory graph in sync after AI generation (Completed 2025-05-18)
- **Task BUGFIX-006**: Fixed hamburger menu not opening (Completed 2025-05-19)
- **Task UI-004**: Removed 'Show Raw API Response' accordion from Gemini panel (Completed 2025-05-18)

### Core System Features
- Interactive 3D graph visualization with Three.js
- Wikidata integration for enriched term information
- AI-powered analysis using Google Gemini API
- Term comparison and semantic analysis
- Interactive learning exercises generation
- Caching system for performance optimization
- Comprehensive search functionality

---

**Note**: This changelog was created on 2024-12-23 to document the readability integration. Previous changes were reconstructed from project documentation and task management files. 