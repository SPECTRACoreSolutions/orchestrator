# Fix Orchestrator .env configuration

$envPath = "C:\Users\MarkMaconnachie\OneDrive - SPECTRA Data Solutions\SPECTRA\.env"

# Read current .env
$content = Get-Content $envPath -Raw

# Extract OpenAI API key
$apiKey = ""
if ($content -match "OPENAI_API_KEY=([^\r\n]+)") {
    $apiKey = $matches[1].Trim()
}

# Remove any existing Orchestrator config
$content = $content -replace "(?s)# Orchestrator LLM Configuration.*?ORCHESTRATOR_LLM_MODEL=[^\r\n]+", ""

# Add new Orchestrator config
$orchestratorConfig = @"

# Orchestrator LLM Configuration (OpenAI)
ORCHESTRATOR_LLM_URL=https://api.openai.com/v1/chat/completions
ORCHESTRATOR_LLM_API_KEY=$apiKey
ORCHESTRATOR_LLM_MODEL=gpt-4o-mini
"@

$content = $content.TrimEnd() + $orchestratorConfig

# Write back
$content | Set-Content $envPath -NoNewline

Write-Host "✅ Orchestrator configured to use OpenAI gpt-4o-mini!"
Write-Host "API Key: $($apiKey.Substring(0, 20))..."

