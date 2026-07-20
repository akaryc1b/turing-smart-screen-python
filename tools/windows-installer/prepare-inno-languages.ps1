# SPDX-License-Identifier: GPL-3.0-or-later
# Downloads the maintained Simplified Chinese Inno Setup translation at a
# pinned commit and verifies the exact Git blob before installer compilation.

$ErrorActionPreference = "Stop"

$TranslationRepository = "kira-96/Inno-Setup-Chinese-Simplified-Translation"
$TranslationCommit = "6da09d23e14443d4cf8f07b1c5fd821bfe459788"
$ExpectedBlobSha = "9e26f9c66ffe689d073706f5fc33a0b50064926d"
$TranslationFile = "ChineseSimplified.isl"
$DownloadUrl = "https://raw.githubusercontent.com/$TranslationRepository/$TranslationCommit/$TranslationFile"
$LanguageDirectory = Join-Path $PSScriptRoot "languages"
$Destination = Join-Path $LanguageDirectory $TranslationFile

New-Item -ItemType Directory -Path $LanguageDirectory -Force | Out-Null
Invoke-WebRequest -Uri $DownloadUrl -OutFile $Destination

$ActualBlobSha = (& git hash-object -- $Destination).Trim()
if ($LASTEXITCODE -ne 0) {
    Remove-Item $Destination -Force -ErrorAction SilentlyContinue
    throw "Unable to calculate the Git blob SHA for $Destination"
}

if ($ActualBlobSha -ne $ExpectedBlobSha) {
    Remove-Item $Destination -Force -ErrorAction SilentlyContinue
    throw "Unexpected Simplified Chinese translation blob: $ActualBlobSha; expected $ExpectedBlobSha"
}

$Translation = Get-Content -Path $Destination -Raw -Encoding UTF8
$RequiredMarkers = @(
    "Inno Setup version 6.5.0+ Chinese Simplified messages",
    "LanguageName=简体中文",
    'LanguageID=$0804',
    "SetupAppTitle=安装",
    "TranslatorNote=简体中文翻译由 Kira"
)

foreach ($Marker in $RequiredMarkers) {
    if (-not $Translation.Contains($Marker)) {
        Remove-Item $Destination -Force -ErrorAction SilentlyContinue
        throw "Simplified Chinese translation is missing required marker: $Marker"
    }
}

Write-Host "Prepared pinned Inno Setup Simplified Chinese translation: $Destination"
Write-Host "Source commit: $TranslationCommit"
Write-Host "Verified Git blob: $ActualBlobSha"
