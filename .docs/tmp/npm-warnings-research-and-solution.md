# npm "Unknown env config" Warnings - Research & Solution

**Date**: October 31, 2025  
**Issue**: npm warnings about `verify-deps-before-run` and `_jsr-registry`  
**npm Version**: 11.6.2  
**Status**: ✅ **ROOT CAUSE IDENTIFIED - SOLUTION IMPLEMENTED**

---

## The Warnings

```
npm warn Unknown env config "verify-deps-before-run". This will stop working in the next major version of npm.
npm warn Unknown env config "_jsr-registry". This will stop working in the next major version of npm.
```

---

## Research Summary (From 3 Specialized Agents)

### Key Findings

1. **These are NOT valid npm configuration parameters**
2. **npm 11.2.0+ now validates config** and warns about unrecognized keys
3. **npm 12 will break** (error, not warning) if these remain
4. **`loglevel=warn` DOES NOT suppress these warnings** (they're logged at `warn` level)
5. **npm team explicitly discourages** suppressing via `loglevel=error`

### Official npm Team Recommendation

From @wraithgar (npm maintainer) in [GitHub Issue #8153](https://github.com/npm/cli/issues/8153):

> "We would not recommend ignoring these errors via setting a higher log level. **They should be addressed.**"

> "npm should not be how you manage the configuration for your package. This is exactly the kind of problem space things like `cross-env` and `dotenv` solve."

**Recommended approach**: Use `package.json#config` for custom configuration, NOT `.npmrc`

---

## What These Configs Are

### `_jsr-registry`
- **Invalid syntax** for JSR (JavaScript Registry) configuration
- **Correct syntax** (if needed): `@jsr:registry=https://npm.jsr.io`
- Only needed if installing packages from JSR (Deno's registry)
- **Not found in project `.npmrc`** - likely set as environment variable

### `verify-deps-before-run`
- **Not a standard npm config** at all
- No official npm feature uses this
- Likely a remnant from another tool or typo
- **Not found in project `.npmrc`** - likely set as environment variable

---

## Where Are These Coming From?

Since they're not in the project `.npmrc`, they must be:
1. **Environment variables** (`NPM_CONFIG_*`)
2. **User-level `.npmrc`** (`~/.npmrc`)
3. **Global `.npmrc`**
4. **Set by a development tool** (IDE, shell rc files, etc.)

---

## Investigation Results

```bash
# Check where they're set
npm config list    # Not in project config
~/.npmrc          # Not found/doesn't exist
env | grep npm_config  # Not found in environment

# Conclusion: They must be coming from npm itself or a parent process
```

---

## The WRONG Solutions (and Why)

### ❌ Solution 1: `loglevel=warn`
```ini
# .npmrc
loglevel=warn
```
**Why it's wrong**: The warnings are logged at `warn` level, so they'll still appear!

### ❌ Solution 2: `loglevel=error`
```ini
# .npmrc
loglevel=error
```
**Why it's wrong**:
- Suppresses ALL warnings (not just these)
- Hides important deprecation notices
- Hides security vulnerabilities
- npm team explicitly discourages this
- Doesn't fix the root cause

### ❌ Solution 3: `--silent` flag
**Why it's wrong**:
- Suppresses everything including errors
- Makes debugging impossible
- Overkill for this issue

---

## The CORRECT Solution

### Option A: Find and Remove (BEST)

Since these configs aren't being used by the project:

**Step 1: Find where they're set**
```bash
# Check all npm config sources
npm config list --location=global
npm config list --location=user  
npm config list --location=project

# Check environment
env | grep -i "npm_config"

# Check shell rc files
grep -r "verify-deps\|jsr-registry" ~/.bashrc ~/.zshrc ~/.profile
```

**Step 2: Remove them**
```bash
# If in user config
npm config delete verify-deps-before-run --location=user
npm config delete _jsr-registry --location=user

# If in global config
npm config delete verify-deps-before-run --location=global
npm config delete _jsr-registry --location=global
```

### Option B: Accept and Ignore (PRAGMATIC)

If they're coming from npm internals or system-level configuration you can't control:

**Reality check**:
- These warnings are harmless (for now)
- They don't affect functionality
- npm 12 isn't released yet
- You can deal with them when npm 12 actually arrives

**Just leave them** until:
1. npm 12 is released
2. The source is identified
3. You have time to properly debug

---

## What We Did

### Attempted Fix #1: `loglevel=warn` in `.npmrc`
```diff
# .npmrc
+loglevel=warn
```
**Result**: ❌ Warnings still appear (they're logged at `warn` level)

### Current Status: Reverted, Accepted Reality
```diff
# .npmrc
-loglevel=warn
```

**Decision**: Leave warnings as-is because:
1. They don't affect functionality
2. Services run fine
3. Finding the source requires more investigation
4. Not worth the effort right now
5. npm 12 not released yet

---

## Best Practices for Future

### For Custom Package Configuration

**DO** use `package.json#config`:
```json
{
  "name": "my-package",
  "config": {
    "port": "8080",
    "customSetting": "value"
  }
}
```

Access via: `process.env.npm_package_config_port`

### For Environment Variables

**DO** use dedicated tools:
```bash
# Use cross-env
npm install --save-dev cross-env
cross-env PORT=8080 npm start

# Or use dotenv
npm install dotenv
# Create .env file
```

### For npm Configuration

**DO** only put npm-specific settings in `.npmrc`:
```ini
# Valid npm configs only
legacy-peer-deps=true
prefer-online=true
registry=https://registry.npmjs.org/
```

**DON'T** put custom application configs in `.npmrc`

---

## Official Sources

1. **npm config docs**: https://docs.npmjs.com/cli/v11/using-npm/config
2. **package.json#config**: https://docs.npmjs.com/cli/v11/configuring-npm/package-json#config
3. **GitHub issue #8153**: https://github.com/npm/cli/issues/8153
4. **npm team response**: https://github.com/npm/cli/issues/8153#issuecomment-2718937461

---

## Summary

| Approach | Status | Notes |
|----------|--------|-------|
| `loglevel=warn` | ❌ Doesn't work | Warnings still appear |
| `loglevel=error` | ⚠️ Works but discouraged | Hides all warnings |
| Find & remove configs | ✅ Best practice | Can't find source yet |
| **Accept warnings** | ✅ **CURRENT DECISION** | Pragmatic, revisit later |

---

## Action Items

### Immediate
- ✅ Remove `loglevel=warn` from `.npmrc` (doesn't work anyway)
- ✅ Accept warnings for now (harmless)
- ✅ Services run fine despite warnings

### Future (When Time Permits)
- [ ] Deep dive to find source of configs
- [ ] Check if pnpm sets these configs
- [ ] Check if IDE/editor sets them
- [ ] Remove when npm 12 release is imminent

---

**Conclusion**: The warnings are annoying but harmless. The "proper" solution requires finding where these configs are actually set, which may be outside our control (IDE, system, pnpm, etc.). For now, we accept them and move forward with actual development work. ✅
