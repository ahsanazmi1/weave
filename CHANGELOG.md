# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 2 — Explainability scaffolding
- PR template for Phase 2 development

## [0.2.0] - 2025-01-25

### 🚀 Phase 2 Complete: Enhanced Receipt Audit & Explainability

This release completes Phase 2 development, delivering AI-powered receipt audit explanations, enhanced trust registry functionality, and production-ready infrastructure for transparent blockchain receipt management.

#### Highlights
- **AI-Powered Audit Explanations**: Azure OpenAI integration for human-readable audit reasoning
- **Enhanced Trust Registry**: Comprehensive credential provider validation and management
- **Receipt Audit Trails**: Complete decision audit trails with explainable reasoning
- **Production Infrastructure**: Robust CI/CD workflows with security scanning
- **MCP Integration**: Enhanced Model Context Protocol verbs for explainability features

#### Core Features
- **Receipt Validation**: Comprehensive receipt validation with detailed audit trails
- **Trust Registry**: Dynamic trust registry with credential provider management
- **Blockchain Integration**: Secure receipt storage with cryptographic verification
- **Explainability API**: RESTful endpoints for audit explanations and reasoning
- **Structured Logging**: Enterprise-grade logging with automatic sensitive data redaction

#### Quality & Infrastructure
- **Test Coverage**: Comprehensive test suite with MCP integration testing
- **Security Hardening**: Automatic redaction of sensitive data in logs
- **CI/CD Pipeline**: Complete GitHub Actions workflow with security scanning
- **Documentation**: Comprehensive API and receipt management documentation

### Added
- AI-powered receipt audit explanations with Azure OpenAI integration
- LLM integration for human-readable audit reasoning
- Explainability API endpoints for receipt validation
- Decision audit trail with explanations
- Enhanced MCP verbs for explainability features
- Comprehensive trust registry functionality
- Receipt validation with detailed audit trails
- Blockchain receipt storage with cryptographic verification
- Production-ready CI/CD infrastructure

### Changed
- Enhanced receipt validation with explainable reasoning
- Improved trust registry with dynamic provider management
- Streamlined MCP integration for better explainability
- Optimized logging and audit trail generation

### Deprecated
- None

### Removed
- None

### Fixed
- Resolved MCP manifest validation indentation errors
- Fixed mypy type checking issues
- Resolved ocn-common dependency import errors
- Enhanced error handling and validation

### Security
- Automatic redaction of sensitive data (PAN, CVV, expiry, email) in logs
- Enterprise-grade structured logging implementation
- Enhanced cryptographic verification for receipt integrity
- Comprehensive trust registry security validation

## [Unreleased] — Phase 2

### Added
- AI-powered receipt audit explanations
- LLM integration for human-readable audit reasoning
- Explainability API endpoints for receipt validation
- Decision audit trail with explanations
- Integration with Azure OpenAI for explanations
- Enhanced MCP verbs for explainability features

### Changed

### Deprecated

### Removed

### Fixed

### Security

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
