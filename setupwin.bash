#!/usr/bin/env bash
set -euo pipefail

cat <<'EOF'
This repository uses Windows-native execution for visible browser login.
Run this from Command Prompt, PowerShell, or Windows Terminal instead:

  setup_windows.bat
  run_windows.bat --force

If you are inside WSL, do not use this script for the Windows headed browser flow.
EOF

if command -v cmd.exe >/dev/null 2>&1; then
  script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  win_dir="$(wslpath -w "$script_dir" 2>/dev/null || true)"
  if [[ -n "$win_dir" ]]; then
    echo
    echo "Detected WSL. You can run Windows setup through cmd.exe:"
    echo "  cmd.exe /c \"cd /d $win_dir && setup_windows.bat\""
  fi
fi
