# Skills Directory Structure Guide

**Document Version**: 1.0
**Last Updated**: 11/02/2025 16:00:00 EST
**Audience**: PromptStash developers, framework integrators

## Overview

PromptStash Skills have a **required subdirectory structure** that distinguishes them from other Claude resources like agents and commands. This guide explains why skills need special handling, the required structure, and validation rules.

---

## Why Skills Need Subdirectories

Skills in PromptStash are fundamentally different from flat-file resources:

### Key Differences from Other Resources

| Resource Type | Structure | Supports Resources | Use Case |
|---|---|---|---|
| **Agents** | Flat `.md` files | No | Simple prompts, patterns |
| **Commands** | Flat `.md` files | No | CLI shortcuts, aliases |
| **Skills** | Subdirectories | Yes | Complex capabilities, bundled tools |

### Benefits of Subdirectory Structure

1. **Modularity**: Skills can include supporting files (scripts, data, references) alongside the main definition
2. **Scalability**: Easier to manage as skills grow in complexity
3. **Organization**: Clear separation between skill definition and supporting materials
4. **Reusability**: Scripts and resources can be packaged alongside skill documentation
5. **Versioning**: Each skill is self-contained and independently maintainable

---

## Required Directory Structure

### Mandatory Components

```
.claude/skills/
└── skill-name/                 # Directory name in kebab-case
    ├── SKILL.md                # Required - ALL CAPS (case-sensitive)
    └── ...                      # Additional optional files
```

### Critical Requirements

1. **Directory Name** (kebab-case)
   - Use lowercase with hyphens
   - Becomes the skill identifier in PromptStash
   - Examples: `code-reviewer`, `security-scanner`, `documentation-writer`
   - Invalid: `CodeReviewer`, `code_reviewer`, `codereviewer`

2. **SKILL.md File** (ALL CAPS - Case Sensitive)
   - **Must be named exactly `SKILL.md`** (not `Skill.md`, `skill.md`, or `skill.MD`)
   - Contains the complete skill definition
   - Located directly in the skill subdirectory
   - This is the main entry point that PromptStash loads

3. **Placement**
   - All skills must be in `.claude/skills/` directory
   - No flat `.md` files directly in `.claude/skills/` directory
   - Each skill is its own subdirectory

---

## Optional Components

Skills can include additional supporting materials organized in the skill subdirectory:

### Reference Documentation

```
.claude/skills/code-reviewer/
├── SKILL.md
├── reference.md                # Additional documentation
├── examples.md                 # Usage examples
└── TROUBLESHOOTING.md          # Common issues and solutions
```

### Supporting Scripts

```
.claude/skills/security-scanner/
├── SKILL.md
├── reference.md
└── scripts/
    ├── scan.py                 # Python helper script
    ├── analyze.sh              # Bash helper script
    └── config.json             # Configuration template
```

### Data Files and Templates

```
.claude/skills/documentation-writer/
├── SKILL.md
├── reference.md
└── templates/
    ├── api-docs-template.md    # Template for API documentation
    ├── user-guide-template.md  # Template for user guides
    └── README-template.md      # Template for project README
```

### Complete Example Structure

```
.claude/skills/
├── code-reviewer/
│   ├── SKILL.md                # Main skill definition
│   ├── reference.md            # Detailed review guidelines
│   ├── examples.md             # Review examples
│   └── scripts/
│       ├── check-complexity.py # Cyclomatic complexity analyzer
│       └── lint-rules.json     # Custom linting rules
│
├── security-scanner/
│   ├── SKILL.md                # Main skill definition
│   ├── CHANGELOG.md            # Version history
│   ├── reference.md            # Security patterns reference
│   └── scripts/
│       ├── scan.py             # Main scanning logic
│       ├── reports.sh          # Report generation
│       └── config/
│           └── rules.yaml      # Security rules
│
└── documentation-writer/
    ├── SKILL.md                # Main skill definition
    ├── reference.md            # Writing guidelines
    ├── templates/
    │   ├── api-template.md
    │   ├── guide-template.md
    │   └── example-template.md
    └── examples/
        ├── good-documentation.md
        └── bad-documentation.md
```

---

## SKILL.md File Format

The `SKILL.md` file is the main entry point for a skill and should contain:

### Recommended Structure

```markdown
# Skill Name

**Version**: 1.0
**Category**: [e.g., Development, Documentation, Security]
**Status**: Active

## Description

Clear, concise description of what the skill does and when to use it.

## Capabilities

- Capability 1
- Capability 2
- Capability 3

## Usage

Instructions for how Claude should use this skill.

### Input

Expected input format and parameters.

### Output

Expected output format and examples.

## Instructions

Detailed instructions for Claude on how to apply this skill.

## Example

Show a concrete example of the skill in action.

## Configuration

Any required or optional configuration settings.

## Known Limitations

Document any limitations or constraints.

## Version History

- **1.0** (11/02/2025) - Initial release
```

### Minimal Valid SKILL.md

At minimum, include:

```markdown
# Skill Name

## Description

What this skill does.

## Instructions

How Claude should use this skill.
```

---

## PromptStash UI Requirements

### Skill Creation Wizard

The PromptStash UI must enforce proper directory structure when creating skills:

**Do NOT do this:**
```
- Create file at: .claude/skills/my-skill.md  ❌
- Allow flat files in skills directory          ❌
```

**MUST do this:**
```
- Create directory: .claude/skills/my-skill/         ✓
- Create file: .claude/skills/my-skill/SKILL.md      ✓
- Initialize with template SKILL.md content          ✓
```

### Skill Creation Flow

1. User enters skill name (e.g., "Code Reviewer")
2. UI converts to kebab-case identifier (e.g., "code-reviewer")
3. UI creates directory structure:
   ```
   .claude/skills/code-reviewer/
   ├── SKILL.md (with template content)
   └── reference.md (empty or with template)
   ```
4. UI opens SKILL.md editor for user to add content
5. Skill is immediately available in PromptStash

### Skill Creation Template

The UI should provide a default template when creating new skills:

```markdown
# [Skill Name]

**Version**: 1.0
**Category**: [Replace with appropriate category]
**Status**: Active

## Description

[Brief description of what this skill does]

## Capabilities

- [Capability 1]
- [Capability 2]

## Instructions

[How Claude should use this skill]

## Example

[Concrete example of the skill in action]
```

### Skill Management UI

The UI should allow users to:

- List all skills in `.claude/skills/` with proper structure
- Create new skills (enforcing directory structure)
- Edit SKILL.md content
- Add supporting files (scripts, references)
- Delete skills (removing entire directory)
- Preview skills before activation

---

## Validation Rules

### PromptStash Validation Logic

The framework should validate skills and report errors clearly:

#### Error Conditions

1. **Flat Skill File Detected**
   ```
   ERROR: Invalid skill structure
   File: .claude/skills/code-reviewer.md

   Skills must be in subdirectories, not flat files.
   Expected: .claude/skills/code-reviewer/SKILL.md
   ```

2. **Missing SKILL.md**
   ```
   ERROR: Incomplete skill directory
   Directory: .claude/skills/code-reviewer/

   Required file not found: SKILL.md
   Skills must contain a SKILL.md file (case-sensitive).
   ```

3. **Wrong Case in SKILL.md**
   ```
   ERROR: Invalid filename
   Directory: .claude/skills/code-reviewer/
   Found: skill.md

   File must be named SKILL.md (all capitals).
   Rename: skill.md → SKILL.md
   ```

4. **Empty Skill Directory**
   ```
   WARNING: Empty skill directory
   Directory: .claude/skills/code-reviewer/

   Directory exists but contains no SKILL.md file.
   This skill will not be loaded.
   ```

### Validation Checks

```python
def validate_skills_directory():
    """
    Validate all skills in .claude/skills/
    Returns: (valid_skills, errors, warnings)
    """

    # 1. Check for flat files in .claude/skills/
    flat_files = glob(".claude/skills/*.md")
    if flat_files:
        errors.append(f"Flat skill files found: {flat_files}")

    # 2. Check each skill subdirectory
    for skill_dir in glob(".claude/skills/*/"):
        # Must contain SKILL.md (exact case)
        if not os.path.exists(f"{skill_dir}/SKILL.md"):
            # Check for wrong case
            lower = glob(f"{skill_dir}/skill.md")
            if lower:
                errors.append(f"{skill_dir}: Found skill.md, must be SKILL.md")
            else:
                errors.append(f"{skill_dir}: Missing required SKILL.md file")
        else:
            valid_skills.append(skill_dir)

    return valid_skills, errors, warnings
```

### Auto-repair Suggestions

When validation detects issues, provide clear fix instructions:

```
ISSUE: .claude/skills/my-skill/skill.md

SUGGESTED FIX:
  mv .claude/skills/my-skill/skill.md \
     .claude/skills/my-skill/SKILL.md
```

---

## Examples

### Good Examples (Correct Structure)

#### Minimal Skill
```
.claude/skills/code-reviewer/
└── SKILL.md                    ✓ Correct
```

#### Skill with Reference
```
.claude/skills/security-scanner/
├── SKILL.md                    ✓ Correct file name
├── reference.md                ✓ Optional reference
└── scripts/
    └── scan.py                 ✓ Optional supporting script
```

#### Full-Featured Skill
```
.claude/skills/documentation-writer/
├── SKILL.md                                    ✓ Main definition
├── reference.md                                ✓ Writing guidelines
├── examples.md                                 ✓ Example usage
├── CHANGELOG.md                                ✓ Version history
└── templates/
    ├── api-documentation-template.md           ✓ Reusable template
    ├── user-guide-template.md                  ✓ Reusable template
    └── configuration.json                      ✓ Configuration file
```

### Bad Examples (Incorrect Structure)

#### Flat File in Skills Directory
```
.claude/skills/code-reviewer.md                ❌ WRONG
```
**Issue**: File should be in subdirectory
**Fix**: Move to `.claude/skills/code-reviewer/SKILL.md`

#### Wrong Filename Case
```
.claude/skills/code-reviewer/skill.md          ❌ WRONG
.claude/skills/code-reviewer/Skill.md          ❌ WRONG
.claude/skills/code-reviewer/skill.MD          ❌ WRONG
```
**Issue**: Filename must be exactly `SKILL.md`
**Fix**: Rename to `SKILL.md`

#### Empty Directory
```
.claude/skills/code-reviewer/                  ❌ WRONG (empty)
```
**Issue**: Directory exists but has no SKILL.md
**Fix**: Create `SKILL.md` or remove directory

#### Wrong Directory Level
```
.claude/skills/team-a/code-reviewer/SKILL.md   ❌ WRONG
```
**Issue**: Skills should not be nested more than one level
**Fix**: Move to `.claude/skills/code-reviewer/SKILL.md`

---

## Migration Guide

### Converting Flat Files to Proper Structure

If you have legacy flat skill files, follow this process:

#### Step 1: Create Directory
```bash
mkdir -p .claude/skills/skill-name
```

#### Step 2: Move Content
```bash
mv .claude/skills/skill-name.md \
   .claude/skills/skill-name/SKILL.md
```

#### Step 3: Validate
```bash
# Check that SKILL.md exists and is readable
cat .claude/skills/skill-name/SKILL.md
```

#### Step 4: Test
Load the skill in PromptStash and verify it works correctly.

---

## Best Practices

### File Organization

1. **Keep SKILL.md focused on skill definition**
   - Put detailed reference material in `reference.md`
   - Put examples in separate `examples.md` file
   - Keep main file under 500 lines

2. **Name supporting scripts clearly**
   - Use descriptive names: `analyze.py`, `validate.sh`
   - Avoid generic names: `script.py`, `helper.sh`
   - Include purpose in filename or docstring

3. **Use consistent naming patterns**
   - If skill does code review: `SKILL.md`, not `skill-definition.md`
   - Supporting scripts: `scripts/` directory, not `tools/` or `utilities/`
   - Templates: `templates/` directory for reusable templates

4. **Include version information in SKILL.md**
   ```markdown
   # Skill Name

   **Version**: 1.0
   **Last Updated**: 11/02/2025 16:00:00 EST
   ```

### Documentation Quality

1. **Clear descriptions**: Explain what the skill does in plain language
2. **Usage examples**: Show concrete examples of the skill in action
3. **Input/output specification**: Document expected formats
4. **Limitations**: Be transparent about what the skill cannot do
5. **Related skills**: Link to complementary skills

### Maintainability

1. **Version your skills** in semantic versioning (1.0, 1.1, 2.0)
2. **Maintain CHANGELOG.md** for significant changes
3. **Keep dependencies minimal** - avoid requiring external tools
4. **Make scripts self-contained** - they should work independently
5. **Document configuration** if the skill needs setup

---

## Troubleshooting

### Skill Not Loading

**Symptom**: Skill appears in file system but not in PromptStash UI

**Checklist**:
- [ ] Skill is in `.claude/skills/skill-name/` directory
- [ ] File is named exactly `SKILL.md` (all caps)
- [ ] File is readable and valid markdown
- [ ] No syntax errors in SKILL.md
- [ ] Directory name is kebab-case (no spaces, underscores)

### Case Sensitivity Issues

**Symptom**: Error about file not found, or file exists but won't load

**Solution**: macOS and Windows are case-insensitive but PromptStash expects exact case.
- Use `SKILL.md` exactly (not `skill.md`)
- Verify with: `ls -la .claude/skills/skill-name/`
- Rename if needed: `mv skill.md SKILL.md`

### Special Characters in Directory Names

**Problem**: Some characters cause issues in file systems

**Solution**: Use only alphanumeric and hyphens
- Good: `code-reviewer`, `security-scanner`
- Bad: `code reviewer`, `code_reviewer`, `code-reviewer_v2`

---

## Future Enhancements

### Planned Features

1. **Skill Inheritance**: Skills that extend other skills
2. **Skill Dependencies**: One skill requiring another
3. **Skill Versioning**: Multiple versions of same skill co-existing
4. **Skill Marketplace**: Share and download community skills
5. **Automated Testing**: Test skills against sample inputs/outputs

### Extension Points

Skills directory structure is designed to support:
- Additional resource types (images, data files)
- Configuration files (.yaml, .json)
- Helper utilities and scripts
- Documentation and examples

---

## Summary Table

| Aspect | Requirement | Example | Invalid |
|---|---|---|---|
| **Location** | `.claude/skills/name/` | `.claude/skills/code-reviewer/` | `.claude/skills/code-reviewer.md` |
| **Filename** | `SKILL.md` (exact case) | `SKILL.md` | `skill.md`, `Skill.md` |
| **Directory Name** | kebab-case | `code-reviewer` | `CodeReviewer`, `code_reviewer` |
| **Content** | Markdown skill definition | See SKILL.md format | Binary files, no extension |
| **Supporting Files** | Optional, in subdirs | `scripts/`, `templates/` | Flat in skill dir |

---

## Related Documentation

- [PromptStash Agents Directory Structure](./AGENTS_DIRECTORY_STRUCTURE.md)
- [PromptStash Commands Directory Structure](./COMMANDS_DIRECTORY_STRUCTURE.md)
- [PromptStash Configuration Guide](./CONFIGURATION.md)
- [PromptStash API Reference](./API_REFERENCE.md)

---

## Questions or Issues?

For questions about skills directory structure:
1. Check this guide first
2. Review examples in this document
3. See troubleshooting section
4. Check related documentation
5. File an issue with details about your use case
