#!/bin/bash
# Local code quality check script
# Runs the same checks as CI/CD locally

set -e  # Exit on first error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   GraphRAG Code Quality Checker       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Track failures
BACKEND_FAILED=0
FRONTEND_FAILED=0

# ==========================================
# Backend Checks
# ==========================================
echo -e "${YELLOW}┌─────────────────────────────────────┐${NC}"
echo -e "${YELLOW}│  Backend Quality Checks             │${NC}"
echo -e "${YELLOW}└─────────────────────────────────────┘${NC}"
echo ""

cd "$ROOT_DIR/apps/api"

# Ruff Format (replaces Black)
echo -e "${BLUE}→ Running Ruff Format (formatter check)...${NC}"
if ruff format --check app/; then
    echo -e "${GREEN}✓ Ruff Format passed${NC}"
else
    echo -e "${RED}✗ Ruff Format failed - run 'ruff format app/' to fix${NC}"
    BACKEND_FAILED=1
fi
echo ""

# Ruff Check (linter)
echo -e "${BLUE}→ Running Ruff Check (linter)...${NC}"
if ruff check app/; then
    echo -e "${GREEN}✓ Ruff Check passed${NC}"
else
    echo -e "${RED}✗ Ruff Check failed - run 'ruff check app/ --fix' to auto-fix${NC}"
    BACKEND_FAILED=1
fi
echo ""

# ==========================================
# Frontend Checks
# ==========================================
echo -e "${YELLOW}┌─────────────────────────────────────┐${NC}"
echo -e "${YELLOW}│  Frontend Quality Checks            │${NC}"
echo -e "${YELLOW}└─────────────────────────────────────┘${NC}"
echo ""

cd "$ROOT_DIR/apps/web"

# ESLint
echo -e "${BLUE}→ Running ESLint...${NC}"
if npm run lint; then
    echo -e "${GREEN}✓ ESLint passed${NC}"
else
    echo -e "${RED}✗ ESLint failed - run 'npm run lint -- --fix' to auto-fix${NC}"
    FRONTEND_FAILED=1
fi
echo ""

# TypeScript
echo -e "${BLUE}→ Running TypeScript compiler check...${NC}"
if npx tsc --noEmit; then
    echo -e "${GREEN}✓ TypeScript passed${NC}"
else
    echo -e "${RED}✗ TypeScript failed - fix type errors${NC}"
    FRONTEND_FAILED=1
fi
echo ""

# ==========================================
# Summary
# ==========================================
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Quality Check Summary                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

if [ $BACKEND_FAILED -eq 0 ]; then
    echo -e "Backend:  ${GREEN}✓ All checks passed${NC}"
else
    echo -e "Backend:  ${RED}✗ Some checks failed${NC}"
fi

if [ $FRONTEND_FAILED -eq 0 ]; then
    echo -e "Frontend: ${GREEN}✓ All checks passed${NC}"
else
    echo -e "Frontend: ${RED}✗ Some checks failed${NC}"
fi

echo ""

if [ $BACKEND_FAILED -eq 0 ] && [ $FRONTEND_FAILED -eq 0 ]; then
    echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   ✓ ALL QUALITY CHECKS PASSED!         ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
    exit 0
else
    echo -e "${RED}╔════════════════════════════════════════╗${NC}"
    echo -e "${RED}║   ✗ SOME QUALITY CHECKS FAILED         ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════╝${NC}"
    exit 1
fi
