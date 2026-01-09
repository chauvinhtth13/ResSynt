# ==============================================================================
# Cleanup Script: Remove .pyc files and reset migrations
# ==============================================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "STEP 1: DELETE ALL .PYC FILES" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Delete all .pyc files
Get-ChildItem -Path . -Filter "*.pyc" -Recurse -Force | ForEach-Object {
    Write-Host "Deleting: $($_.FullName)" -ForegroundColor Yellow
    Remove-Item $_.FullName -Force
}

Write-Host "`nDone deleting .pyc files!`n" -ForegroundColor Green

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "STEP 2: DELETE ALL __PYCACHE__ FOLDERS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Delete all __pycache__ folders
Get-ChildItem -Path . -Filter "__pycache__" -Recurse -Directory -Force | ForEach-Object {
    Write-Host "Deleting folder: $($_.FullName)" -ForegroundColor Yellow
    Remove-Item $_.FullName -Recurse -Force
}

Write-Host "`nDone deleting __pycache__ folders!`n" -ForegroundColor Green

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "STEP 3: DELETE MIGRATIONS FILES (except __init__.py)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Delete migration files (keep __init__.py)
Get-ChildItem -Path .\backends -Include "0*.py" -Recurse -Force | Where-Object {
    $_.DirectoryName -like "*migrations*"
} | ForEach-Object {
    Write-Host "Deleting migration: $($_.FullName)" -ForegroundColor Yellow
    Remove-Item $_.FullName -Force
}

Write-Host "`nDone deleting migration files!`n" -ForegroundColor Green

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS: Run these commands to reset database" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. python manage.py reset_migrations  # Delete records from DB" -ForegroundColor White
Write-Host "2. python manage.py makemigrations     # Create new migrations" -ForegroundColor White
Write-Host "3. python manage.py migrate            # Apply migrations" -ForegroundColor White
Write-Host ""
