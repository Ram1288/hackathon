# Changelog

All notable changes to DevDebug AI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1-prerelease] - 2025-11-08

### Added
- Initial release of DevDebug AI
- 7-agent architecture (DocumentAgent, ExecutionAgent, LLMAgent, InvestigationAgent, InvestigatorAgent, KnowledgeAgent, SecurityPolicyAgent)
- Dual-mode operation (Action vs Diagnostic)
- Intent detection with diagnostic-first priority
- Action mode: Executes delete/create/scale commands
- Diagnostic mode: Investigates and troubleshoots without executing destructive commands
- Iterative investigation system (up to 5 iterations)
- Pattern recognition for common K8s errors (CrashLoopBackOff, OOMKilled, ImagePullBackOff, etc.)
- AI-powered command generation using Ollama/Llama 3.1:8b
- Security validation before command execution
- CLI interface with health check, single query, and interactive modes
- REST API with Swagger documentation
- Configuration via YAML
- Knowledge discovery system (discovers kubectl commands and K8s resources dynamically)

### Fixed
- JSON parsing errors in action command generation (removed jsonpath to avoid nested quotes)
- Intent detection priority (diagnostic keywords checked before action keywords)
- Token limit increased to 1500 to prevent truncation
- Security agent prompt enhanced to allow safe read operations

### Security
- Command validation before execution
- Configurable permissions (read-only, allow_delete, allow_create, allow_update)
- AI-driven security evaluation via SecurityPolicyAgent
- Shell injection prevention

### Known Issues
- Resource discovery returns 0 K8s resources (needs kubectl api-resources access)
- No persistent session storage (in-memory only)
- Single LLM backend support (Ollama only)

---

## Versioning Guide

- **MAJOR** version: Incompatible API changes
- **MINOR** version: New functionality (backwards compatible)
- **PATCH** version: Bug fixes (backwards compatible)
- **Prerelease** tags: alpha, beta, rc, prerelease
