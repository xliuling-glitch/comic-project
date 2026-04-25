# Convert agency-agents to OpenClaw skill format
$sourceRoot = "C:\Users\Administrator\.openclaw\workspace\agency-agents"
$destRoot = "C:\Users\Administrator\.openclaw\extensions\agency-agents"

# Get all .md files excluding README, CONTRIBUTING, etc.
$files = Get-ChildItem -Recurse -Filter *.md -Path $sourceRoot | 
         Where-Object { $_.Name -notmatch 'README|CONTRIBUTING|LICENSE|_zh-CN' }

Write-Host "Found $($files.Count) agent files to convert..."

$count = 0
foreach ($file in $files) {
    $category = $file.Directory.Name
    $originalName = $file.BaseName
    
    # Create skill name: category-original-name (lowercase with hyphens)
    $skillName = "$category-$originalName".ToLower()
    $skillDir = Join-Path $destRoot $skillName
    
    # Create directory
    New-Item -ItemType Directory -Force -Path $skillDir | Out-Null
    
    # Read original content
    $content = Get-Content $file.FullName -Raw
    
    # Check if it already has frontmatter (Claude Code format)
    if ($content -match '^---\s*$([\s\S]*?)^---\s*$') {
        # Already has frontmatter, extract it
        $frontmatterMatch = $matches[1]
        $body = $content.Substring($matches[0].Length).Trim()
        
        # Parse existing frontmatter to get name and description
        $name = $originalName
        $description = "Specialized $category agent: $originalName"
        
        if ($frontmatterMatch -match 'name:\s*(.+)') {
            $name = $matches[1].Trim()
        }
        if ($frontmatterMatch -match 'description:\s*(.+)') {
            $description = $matches[1].Trim()
        }
        if ($frontmatterMatch -match 'emoji:\s*(\S+)') {
            $emoji = $matches[1].Trim()
        } else {
            $emoji = "🤖"
        }
        
        # Create new frontmatter for OpenClaw
        $newFrontmatter = @"
---
name: $skillName
description: $description
metadata:
  openclaw:
    emoji: $emoji
---
"@
        
        $newContent = $newFrontmatter + "`n`n" + $body
    } else {
        # No frontmatter, create basic one
        $name = $originalName
        $description = "Specialized $category agent: $name"
        $emoji = "🤖"
        
        $newFrontmatter = @"
---
name: $skillName
description: $description
metadata:
  openclaw:
    emoji: $emoji
---
"@
        
        $newContent = $newFrontmatter + "`n`n" + $content
    }
    
    # Write SKILL.md
    $skillPath = Join-Path $skillDir "SKILL.md"
    $newContent | Out-File $skillPath -Encoding utf8
    
    $count++
    Write-Host "[$count/$($files.Count)] Created $skillName"
}

Write-Host "`nConversion complete! Created $count skills in $destRoot"
