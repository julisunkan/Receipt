# Smart Receipt Generator

## Overview

Smart Receipt Generator is a Flask-based web application that allows users to create professional receipts with business and client details, itemized billing, and various payment options. The application features a responsive dark-themed interface, supports multiple currencies, and generates receipts in both web and PDF formats with QR code integration for enhanced functionality.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Vanilla JavaScript with Bootstrap 5 dark theme
- **Responsive Design**: Mobile-first approach using Bootstrap's grid system
- **Interactive Features**: Dynamic item management, signature pad integration, and real-time calculations
- **File Upload**: Client-side file handling for business logos with validation
- **Form Validation**: Bootstrap's built-in validation with custom feedback

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **File Structure**: Modular design with separate files for routes, models, and configuration
- **Session Management**: Flask's built-in session handling with configurable secret keys
- **File Processing**: Werkzeug utilities for secure file uploads and handling
- **Template Engine**: Jinja2 for dynamic HTML generation

### Data Storage Solutions
- **File-based Storage**: Local file system for uploaded images and generated assets
- **JSON Configuration**: Currency data stored in static JSON file
- **No Database**: Application operates without persistent database storage
- **Static Assets**: Organized folder structure for uploads, QR codes, and static files

### Core Features
- **Receipt Generation**: UUID-based receipt ID generation with customizable business details
- **PDF Export**: Server-side PDF generation using pdfkit with cross-platform wkhtmltopdf detection
- **QR Code Integration**: Dynamic QR code generation for receipts
- **Currency Support**: Comprehensive ISO 4217 currency codes with symbols
- **Business Settings**: Import/export functionality for business configuration persistence
- **Auto-Cleanup**: Automatic deletion of generated files after 1 minute for security

### Security and File Handling
- **Upload Restrictions**: File type validation and size limits (16MB max)
- **Secure Filenames**: Werkzeug's secure_filename for safe file handling
- **Environment Configuration**: Environment variable support for production secrets
- **Proxy Support**: ProxyFix middleware for deployment behind reverse proxies

## External Dependencies

### Python Libraries
- **Flask**: Core web framework for request handling and routing
- **Werkzeug**: WSGI utilities for file uploads and security
- **qrcode**: QR code generation library
- **pdfkit**: PDF generation from HTML templates

### Frontend Libraries
- **Bootstrap 5**: CSS framework with dark theme support
- **Font Awesome 6**: Icon library for UI elements
- **SignaturePad**: JavaScript library for digital signature capture

### System Dependencies
- **wkhtmltopdf**: Required by pdfkit for PDF generation (automatically detected across platforms)

### File System Requirements
- **Static Directories**: Automated creation of upload and QR code directories
- **Image Support**: PNG, JPG, JPEG, GIF, SVG file format support
- **Template System**: Jinja2 templates for receipt generation and PDF export