#!/bin/zsh
set -eu
presentation_dir="${0:A:h}"
profile_dir="$HOME/Library/Application Support/Microsoft-meeting-preview"
for app_dir in '/Applications/Visual Studio Code.app' "$HOME/Applications/Visual Studio Code.app" "$HOME/Downloads/Visual Studio Code.app"; do
  if [[ -x "$app_dir/Contents/Resources/app/bin/code" ]]; then
    exec "$app_dir/Contents/Resources/app/bin/code" --new-window \
      --user-data-dir="$profile_dir" --extensions-dir="$profile_dir/extensions" \
      --extensionDevelopmentPath="$presentation_dir/extension" \
      "$presentation_dir/Microsoft-meeting.code-workspace"
  fi
done
print -u2 'Microsoft Visual Studio Code was not found. Open PRESENTATION.md in your editor and use Markdown: Open Preview to the Side.'
exit 1
