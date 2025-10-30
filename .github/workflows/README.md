# GitHub Actions Workflows

## Overview

This directory contains GitHub Actions workflows for the GraphRAG project.

## Workflows

### `code-quality.yml`

**Purpose**: Ensures code quality standards are met before merging.

**Triggers**:
- Push to `main`, `develop`, or `feat/*` branches
- Pull requests to `main` or `develop`

**Jobs**:

#### 1. Backend Quality (`backend-quality`)
- **Ruff Format**: Code formatting check
  - Command: `ruff format --check app/`
  - Ensures Python code follows PEP 8 formatting (replaces Black)
- **Ruff Check**: Fast Python linter
  - Command: `ruff check app/`
  - Checks for code style issues, unused imports, etc.

#### 2. Frontend Quality (`frontend-quality`)
- **ESLint**: JavaScript/TypeScript linter
  - Command: `npm run lint`
  - Checks React/Next.js code for issues
- **TypeScript**: Type checker
  - Command: `npx tsc --noEmit`
  - Validates TypeScript types without emitting files

#### 3. Summary (`summary`)
- Aggregates results from both jobs
- Provides clear pass/fail status

## Local Development

Run these checks locally before pushing:

### Backend
```bash
cd apps/api

# Format code
ruff format app/

# Lint code
ruff check app/ --fix
```

### Frontend
```bash
cd apps/web

# Lint code
npm run lint

# Type check
npx tsc --noEmit
```

### All at once (from root)
```bash
npm run lint
```

## Fixing Issues

### Backend

**Ruff formatting**:
```bash
cd apps/api
ruff format app/  # Auto-formats files
```

**Ruff linting issues**:
```bash
cd apps/api
ruff check app/ --fix  # Auto-fix when possible
```

### Frontend

**ESLint issues**:
```bash
cd apps/web
npm run lint -- --fix  # Auto-fix when possible
```

**TypeScript errors**:
- Fix type mismatches
- Add proper type annotations
- Check `tsconfig.json` settings

## CI/CD Status Badges

Add to your README.md:

```markdown
[![Code Quality](https://github.com/YOUR_USERNAME/graphrag/actions/workflows/code-quality.yml/badge.svg)](https://github.com/YOUR_USERNAME/graphrag/actions/workflows/code-quality.yml)
```

## Notes

- All checks must pass for CI to succeed
- `continue-on-error: false` ensures failures block merges
- Checks run in parallel for faster feedback
- Summary job provides aggregated status

## Future Enhancements

Potential additions (not implemented yet):
- Test running (currently tests run locally only)
- Coverage reporting
- Deployment workflows
- Security scanning
- Dependency updates (Dependabot)
