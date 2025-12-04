# ===============================================================
# Enterprise-Grade Repository Dump Generator
# Outputs:
#   - audit_backend.txt
#   - audit_frontend.txt
#   - audit_manifest.json
#   - audit_manifest_backend.json
#   - audit_manifest_frontend.json
# Notes:
#   - UTF-8, LF-only, deterministic ordering
#   - Excludes build/temp/virtualenv noise
#   - Suitable for AI ingestion (lightweight manifests, clean blocks)
# ===============================================================

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Get-Location

# -------------------------
# Output locations
# -------------------------
$backendDumpFile     = Join-Path $root "audit_backend.txt"
$frontendDumpFile    = Join-Path $root "audit_frontend.txt"
$manifestAllFile     = Join-Path $root "audit_manifest.json"
$manifestBackendFile = Join-Path $root "audit_manifest_backend.json"
$manifestFrontFile   = Join-Path $root "audit_manifest_frontend.json"

# -------------------------
# Exclusions
# -------------------------
$excludeDirs = @(
    'venv', '.venv', '.vnv',
    '__pycache__', '.git', 'node_modules',
    'dist', 'build', 'coverage',
    'migrations', 'media', 'staticfiles',
    'System Volume Information', '$RECYCLE.BIN',
    '.pytest_cache', '.sass-cache', 'site-packages', '.egg-info'
)

$excludeFilesByName = @(
    'manage.py', 'wsgi.py', 'asgi.py',
    'audit_manifest.json',
    'audit_manifest_backend.json',
    'audit_manifest_frontend.json',
    'audit_backend.txt',
    'audit_frontend.txt',
    'package.json',
    'package-lock.json'
)

$excludePathPattern = '\\(venv|\.venv|\.vnv|__pycache__|\.git|node_modules|dist|build|coverage|migrations|media|staticfiles|site-packages|\.pytest_cache|\.sass-cache|\.egg-info)\\'

# -------------------------
# Categories
# -------------------------
$backendExtensions  = @('.py')
$frontendExtensions = @('.html', '.css', '.js', '.json', '.md')

# -------------------------
# Helpers
# -------------------------
function Get-AuditableFiles {
    param(
        [string[]] $extensions
    )
    Get-ChildItem -Recurse -File | Where-Object {
        ($extensions -contains $_.Extension) -and
        ($excludeDirs -notcontains $_.Directory.Name) -and
        ($excludeFilesByName -notcontains $_.Name) -and
        ($_.FullName -notmatch $excludePathPattern)
    }
}

function Normalize-LF {
    param([string] $text)
    return ($text -replace "`r`n", "`n")
}

# -------------------------
# Collect files
# -------------------------
$backendFiles  = Get-AuditableFiles -extensions $backendExtensions  | Sort-Object FullName
$frontendFiles = Get-AuditableFiles -extensions $frontendExtensions | Sort-Object FullName
$backendCount  = $backendFiles.Count
$frontendCount = $frontendFiles.Count

# -------------------------
# Manifests
# -------------------------
$manifestAll      = New-Object System.Collections.Generic.List[Object]
$manifestBackend  = New-Object System.Collections.Generic.List[Object]
$manifestFrontend = New-Object System.Collections.Generic.List[Object]

# -------------------------
# Dump routine
# -------------------------
function Dump-Files {
    param(
        [array] $files,
        [string] $category,
        [System.IO.StreamWriter] $stream,
        $manifestTarget
    )

    foreach ($file in $files) {
        $relPath = $file.FullName.Substring($root.Path.Length + 1)
        $hash = (Get-FileHash $file.FullName -Algorithm SHA256).Hash
        $content = Get-Content $file.FullName -Raw -Encoding UTF8
        $content = Normalize-LF $content
        $lineCount = ($content.Split("`n")).Count

        $entry = [PSCustomObject]@{
            file       = $relPath
            size       = $file.Length
            hash       = $hash
            category   = $category
            line_count = $lineCount
        }
        $manifestTarget.Add($entry)
        $manifestAll.Add($entry)

        $stream.WriteLine("============================================")
        $stream.WriteLine("# FILE: $relPath")
        $stream.WriteLine("# SIZE: $($file.Length)")
        $stream.WriteLine("# HASH: $hash")
        $stream.WriteLine("# LINES: $lineCount")
        $stream.WriteLine("============================================")
        $stream.WriteLine("")
        $stream.WriteLine($content)
        $stream.WriteLine("")
    }
}

# -------------------------
# Create writers and dump
# -------------------------
$backendWriter  = New-Object System.IO.StreamWriter($backendDumpFile,  $false, [System.Text.Encoding]::UTF8)
$frontendWriter = New-Object System.IO.StreamWriter($frontendDumpFile, $false, [System.Text.Encoding]::UTF8)

Dump-Files -files $backendFiles  -category "backend"  -stream $backendWriter  -manifestTarget $manifestBackend
Dump-Files -files $frontendFiles -category "frontend" -stream $frontendWriter -manifestTarget $manifestFrontend

$backendWriter.Close()
$frontendWriter.Close()

# -------------------------
# Write manifests
# -------------------------
$manifestAll      | ConvertTo-Json -Depth 10 | Out-File $manifestAllFile      -Encoding UTF8
$manifestBackend  | ConvertTo-Json -Depth 10 | Out-File $manifestBackendFile  -Encoding UTF8
$manifestFrontend | ConvertTo-Json -Depth 10 | Out-File $manifestFrontFile    -Encoding UTF8

Write-Host ""
Write-Host "=======================================================" -ForegroundColor Green
Write-Host "  ✔ Backend dump written to:   $backendDumpFile" -ForegroundColor Yellow
Write-Host "  ✔ Frontend dump written to:  $frontendDumpFile" -ForegroundColor Yellow
Write-Host "  ✔ Combined manifest:         $manifestAllFile" -ForegroundColor Yellow
Write-Host "  ✔ Backend manifest:          $manifestBackendFile" -ForegroundColor Yellow
Write-Host "  ✔ Frontend manifest:         $manifestFrontFile" -ForegroundColor Yellow
Write-Host "  ✔ Files processed: backend=$backendCount, frontend=$frontendCount (noise excluded)" -ForegroundColor Yellow
Write-Host "=======================================================" -ForegroundColor Green
