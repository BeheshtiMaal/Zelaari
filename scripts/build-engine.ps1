$ErrorActionPreference = 'Stop'
uv run --project backend pyinstaller --noconfirm --clean --onedir --name watchdog --distpath build/engine --workpath build/work --specpath build/work backend/server/watchdog.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
uv run --project backend pyinstaller --noconfirm --clean --onedir --name engine --distpath build/engine --workpath build/work --specpath build/work --paths backend --collect-all deepagents --collect-all langchain --collect-all langchain_openai --collect-all langchain_anthropic --collect-all langgraph --collect-all tiktoken --copy-metadata langchain-core --add-data 'backend/agent/genui_prompt.txt;agent' backend/server/entrypoint.py
exit $LASTEXITCODE
