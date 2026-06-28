# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email the maintainer at the email associated with the repository.
3. Include a description of the vulnerability and steps to reproduce.
4. Allow reasonable time for a fix before public disclosure.

## Security Measures

### Input Validation
- All file paths are sanitized to prevent path traversal attacks
- File extensions are validated against allowed lists
- Image parsing uses safe Pillow operations

### No External Dependencies
- No network calls or API dependencies
- No external data sources
- All processing is done locally

### Safe File Operations
- Paths are resolved and validated before access
- Directory traversal (`..`) is blocked
- Only files (not directories) are processed

### Dependency Security
- All dependencies are version-pinned to prevent supply chain attacks
- No use of `latest` or wildcard versions
- Dependencies are reviewed for known vulnerabilities

### Data Handling
- No data is collected, stored, or transmitted
- No user data is processed beyond the input files
- No logging of file contents or paths in production
