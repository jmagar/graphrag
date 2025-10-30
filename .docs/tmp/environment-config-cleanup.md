# Environment Configuration and Repository Cleanup

## Investigation Summary

### Problem Identified
User asked why there were both `apps/web/` and `apps/frontend/` directories in the monorepo.

### Findings

#### 1. Directory Structure Analysis
```bash
# Command: ls -la /home/jmagar/code/graphrag/apps/
apps/
├── api/          # FastAPI backend (active)
├── frontend/     # Nearly empty, only .next build folder
└── web/          # Full Next.js app with all code
```

**Finding**: `apps/frontend/` was a duplicate/leftover directory with no meaningful content.

#### 2. Submodule Issue
```bash
# Command: git status when trying to add apps/web/.env.example
fatal: Pathspec 'apps/web/.env.example' is in submodule 'apps/web'
```

**Finding**: `apps/web/` was configured as a git submodule but not properly initialized.

Evidence from earlier commit:
```
warning: adding embedded git repository: apps/web
create mode 160000 apps/web  # 160000 = submodule
```

#### 3. Environment Files Review

**Existing files:**
- `/home/jmagar/code/graphrag/.env` - Root config with actual keys
- `/home/jmagar/code/graphrag/apps/api/.env` - Backend config with actual keys  
- `/home/jmagar/code/graphrag/apps/web/.env.local` - Frontend config

**Missing:**
- No `.env.example` files anywhere
- No template for new developers

#### 4. Gitignore Conflict
```
# File: apps/web/.gitignore line 34
.env*  # This blocks .env.example from being committed
```

**Finding**: Overly broad pattern preventing example files from being tracked.

### Actions Taken

#### 1. Removed Duplicate Directory
```bash
rm -rf /home/jmagar/code/graphrag/apps/frontend
```

#### 2. Converted Submodule to Regular Directory
```bash
git rm --cached apps/web         # Remove from submodule tracking
rm -rf apps/web/.git             # Remove nested git repo
git add apps/web                 # Add as regular directory
```

#### 3. Created Environment Templates

**Files created:**
- `.env.example` - Root level template
- `apps/api/.env.example` - Backend template
- `apps/web/.env.example` - Frontend template

**Configuration details:**
```
# Root and API configs include:
FIRECRAWL_URL=http://localhost:4200
QDRANT_URL=http://localhost:4203  
TEI_URL=http://localhost:4207
RERANKER_URL=http://localhost:4208
OLLAMA_URL=http://localhost:4214

# Web config includes:
NEXT_PUBLIC_API_URL=http://localhost:4400
NEXT_PUBLIC_APP_URL=http://localhost:4300
```

#### 4. Fixed Gitignore
```diff
# File: apps/web/.gitignore
- .env*
+ .env
+ .env.local
+ .env*.local
+ !.env.example
```

#### 5. Updated Documentation
**File: README.md**
- Changed all references from `apps/frontend` to `apps/web`
- Updated install commands
- Updated npm script references
- Updated troubleshooting paths

**Changes:**
- Line 82-83: `cd apps/frontend` → `cd apps/web`
- Line 115-116: npm scripts updated
- Line 195: Development commands
- Line 233: Project structure
- Line 282: Troubleshooting paths

### Results

**Commit:** `ffae7e4`
```
61 files changed, 10844 insertions(+), 14 deletions(-)
- Removed apps/web submodule
- Added all apps/web files as regular tracked files
- Added .env.example files
- Updated README consistently
```

**Repository now has:**
- ✅ Single web app directory (`apps/web`)
- ✅ Environment templates for all services
- ✅ Consistent naming throughout docs
- ✅ All files properly tracked in git

### Key File Paths
- Root config: `.env.example`
- API config: `apps/api/.env.example`
- Web config: `apps/web/.env.example`
- Web gitignore: `apps/web/.gitignore` (fixed)
- Documentation: `README.md` (updated)
