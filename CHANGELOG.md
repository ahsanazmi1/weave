# Changelog

All notable changes to this project will be documented in this file.

## v0.4.0 — Phase 4: Payment Instruction & Visibility

### 🚀 Phase 4 — Payment Instruction & Visibility

This release initiates Phase 4 development, focusing on payment instruction generation, settlement visibility, and comprehensive payment tracking for receipt audit trails.

#### Planned Features
- **Payment Instruction Generation**: Generate standardized payment instructions for audit trails
- **Settlement Visibility**: Real-time tracking and visibility into settlement processes
- **Payment Tracking**: Comprehensive payment tracking across receipt workflows
- **Instruction Validation**: Enhanced validation for payment instructions and settlement confirmations
- **CloudEvents Integration**: New event types for payment instruction and settlement visibility

#### Timeline
- **Status**: Active development on `phase-4-instruction` branch
- **Timeline**: Weeks 12-16 of OCN development roadmap
- **Issue Tracker**: [Phase 4 Issues](https://github.com/ahsanazmi1/weave/issues?q=is%3Aopen+is%3Aissue+label%3Aphase-4)

## v0.3.0 — Phase 3: Negotiation & Live Fee Bidding

### Added
- **Processor Auction System**: Complete auction management for Carat, Adyen, Stripe
- **Bid Request Broadcasting**: Emits `ocn.weave.bid_request.v1` to processor connectors
- **Bid Response Aggregation**: Collects and aggregates `ocn.weave.bid_response.v1` payloads
- **Winner Determination**: Automatic selection with tie-breaker logic (cost, settlement, confidence)
- **CloudEvent Emission**: Comprehensive event logging for audit trails
- **LLM Summaries**: Optional LLM-powered auction result explanations
- **MCP Integration**: `runAuction` verb for Model Context Protocol
- **API Endpoints**: 
  - `POST /auction/run` - Run processor auction for pay-ins
  - `GET /auction/status` - Service status and capabilities
  - `GET /auction/sample-request` - Sample auction request for testing
- **Deterministic Results**: Consistent auction outcomes with configurable seeds
- **Comprehensive Tests**: 30+ test cases covering aggregation, tie-breakers, and CloudEvents

### Features
- Processor connector stubs with realistic pricing models
- Effective cost calculation (bps - rebate_bps) with aggregation
- Tie-breaker logic: cost → settlement days → confidence
- CloudEvent validation and JSON schema
- Integration with existing structured logging and receipt storage

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
