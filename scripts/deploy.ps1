param(
  [ValidateSet("railway","render","vercel")]
  [string]$Platform,
  [string]$BackendUrl,
  [string]$DatabaseUrl,
  [string]$JwtSecret
)

$ErrorActionPreference = "Stop"

function Update-FrontendRewrites {
  param([string]$Url)
  $p = Join-Path $PSScriptRoot "..\frontend\vercel.json"
  if (-not $Url) { return }
  $json = @{ rewrites = @(@{ source = "/api/:match*"; destination = "$Url/api/:match*" }) } | ConvertTo-Json -Depth 4
  Set-Content -LiteralPath $p -Value $json -Encoding UTF8
}

function Init-Database {
  param([string]$Conn)
  if ($Conn) { $env:DATABASE_URL = $Conn }
  if ($JwtSecret) { $env:JWT_SECRET = $JwtSecret }
  & (Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe") -m backend.init_db
}

function Deploy-VercelBackend {
  if ($DatabaseUrl) { $env:DATABASE_URL = $DatabaseUrl }
  if ($JwtSecret) { $env:JWT_SECRET = $JwtSecret }
  pushd (Join-Path $PSScriptRoot "..")
  vercel
  vercel env add DATABASE_URL
  vercel env add JWT_SECRET
  vercel --prod
  popd
}

function Deploy-FrontendVercel {
  pushd (Join-Path $PSScriptRoot "..\frontend")
  vercel --prod
  popd
}

function Deploy-RailwayBackend {
  pushd (Join-Path $PSScriptRoot "..")
  railway login
  railway init
  if ($DatabaseUrl) { railway variables set DATABASE_URL=$DatabaseUrl }
  if ($JwtSecret) { railway variables set JWT_SECRET=$JwtSecret }
  railway variables set UPLOAD_FOLDER=/data/uploads
  railway up
  popd
}

switch ($Platform) {
  "vercel" { Deploy-VercelBackend }
  "railway" { Deploy-RailwayBackend }
  "render" { }
}

if ($BackendUrl) { Update-FrontendRewrites -Url $BackendUrl }
Deploy-FrontendVercel
if ($DatabaseUrl) { Init-Database -Conn $DatabaseUrl }