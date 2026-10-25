$ErrorActionPreference = 'Stop'
$engineSourceRoot = (Resolve-Path -LiteralPath 'backend').Path
$enginePromptFile = Join-Path $engineSourceRoot 'agent/genui_prompt.txt'
$providerPresetFile = Join-Path $engineSourceRoot 'providers/presets.json'
$providerContextFile = Join-Path $engineSourceRoot 'providers/context_table.json'
$workspaceRoot = (Resolve-Path -LiteralPath '.').Path
$engineOutputRoot = [IO.Path]::GetFullPath((Join-Path $workspaceRoot 'build/engine'))
if (-not $engineOutputRoot.StartsWith($workspaceRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Build output must remain in the workspace' }
$runningBundles = Get-Process -Name watchdog,engine -ErrorAction SilentlyContinue | Where-Object { $_.Path -and $_.Path.StartsWith($engineOutputRoot + [IO.Path]::DirectorySeparatorChar) }
if ($runningBundles) { throw 'Close the running bundled CodeHarness engine before rebuilding it.' }
uv run --offline --no-sync --project backend pyinstaller --noconfirm --onedir --name watchdog --distpath build/engine --workpath build/work --specpath build/work backend/server/watchdog.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run --offline --no-sync --project backend pyinstaller --noconfirm --onedir --name engine --distpath build/engine --workpath build/work --specpath build/work --paths $engineSourceRoot --collect-all deepagents --collect-all langchain --collect-all langchain_openai --collect-all langchain_anthropic --collect-all langgraph --collect-all tiktoken --copy-metadata langchain-core --add-data "$enginePromptFile;agent" --add-data "$providerPresetFile;providers" --add-data "$providerContextFile;providers" backend/server/entrypoint.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
$sampleSourceRoot = Join-Path $workspaceRoot 'examples'
$sampleTargetRoot = Join-Path $engineOutputRoot 'engine/examples'
if (-not (Test-Path -LiteralPath (Join-Path $sampleSourceRoot 'sample-project/README.md'))) { throw 'examples/sample-project/README.md is missing from the checkout; the bundle would ship without the sample it advertises.' }
if (Test-Path -LiteralPath $sampleTargetRoot) { Remove-Item -LiteralPath $sampleTargetRoot -Recurse -Force }
New-Item -ItemType Directory -Path $sampleTargetRoot | Out-Null
Get-ChildItem -LiteralPath $sampleSourceRoot -Force | Copy-Item -Destination $sampleTargetRoot -Recurse -Force
if (-not (Test-Path -LiteralPath (Join-Path $sampleTargetRoot 'sample-project/README.md'))) { throw "The engine bundle has no examples/sample-project/README.md under $sampleTargetRoot; a packaged app would answer 404 on the sample project." }
exit 0
