# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-09-23

### Added
- Initial project scaffolding for Weave.
- FastAPI application with receipt ledger operations.
- Basic MCP (Model Context Protocol) stubs.
- Structured JSON logging with automatic redaction.
- Receipt storage and retrieval functionality.
- Initial test suite with fixtures.
- Basic CI workflow.

### Security
- Automatic redaction of sensitive data (PAN, CVV, expiry, email) in logs.
- Enterprise-grade structured logging implementation.
