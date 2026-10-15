const vscode = require('vscode');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFile } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const repo = path.resolve(root, '../../../../..');
const yaml = path.resolve(root, '../../yaml-walkthrough');
const allowedFiles = new Set(Object.keys(JSON.parse(fs.readFileSync(path.join(root, 'yaml-source-hashes.json'), 'utf8'))));
const sources = new Set(JSON.parse(fs.readFileSync(path.join(root, 'slides.json'), 'utf8')).flatMap(s => s.sources));
let panel;

async function showFile(file) {
  const document = await vscode.workspace.openTextDocument(file);
  await vscode.window.showTextDocument(document, { viewColumn: vscode.ViewColumn.One, preserveFocus: true, preview: false });
}

function report(text) {
  if (panel) panel.webview.postMessage({ type: 'status', text });
}

async function configure(context) {
  for (const app of ['gateway', 'lens']) {
    const value = await vscode.window.showInputBox({
      title: app === 'gateway' ? 'Gateway UI URL' : 'SRE Lens URL',
      prompt: 'Existing application URL. Saved locally in this extension, outside the repository.',
      value: context.globalState.get(app, ''),
      ignoreFocusOut: true,
      validateInput(value) {
        if (!value.trim()) return undefined;
        try {
          const u = new URL(value.trim());
          if (!['http:', 'https:'].includes(u.protocol) || u.username || u.password || u.hash || u.search) throw Error();
        } catch { return 'Enter an http(s) URL without credentials, query parameters or a fragment.'; }
      }
    });
    if (value === undefined) return;
    await context.globalState.update(app, value.trim() || undefined);
  }
  report('Live app URLs saved locally. Open a live app only when ready to present.');
}

async function open(context) {
  if (panel) { panel.dispose(); }
  await vscode.commands.executeCommand('workbench.action.closeSidebar');
  await vscode.commands.executeCommand('vscode.setEditorLayout', { orientation: 0, groups: [{ size: 0.39 }, { size: 0.61 }] });
  await showFile(path.join(yaml, '01-agent.yaml'));
  panel = vscode.window.createWebviewPanel('microsoftMeeting', 'Microsoft meeting · diagrams', vscode.ViewColumn.Two,
    { enableScripts: true, retainContextWhenHidden: true, localResourceRoots: [] });
  const nonce = crypto.randomBytes(16).toString('hex');
  let html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  html = html.replace('<meta charset="utf-8">', `<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">`);
  html = html.replace('<script>', `<script nonce="${nonce}">`);
  panel.webview.html = html;
  panel.onDidDispose(() => { panel = undefined; }, null, context.subscriptions);
  panel.webview.onDidReceiveMessage(async message => {
    try {
      if (message.type === 'file' && allowedFiles.has(message.file)) await showFile(path.join(yaml, message.file));
      else if (message.type === 'source' && sources.has(message.path)) await showFile(path.join(repo, message.path));
      else if (message.type === 'markdown') {
        await vscode.commands.executeCommand('vscode.openWith', vscode.Uri.file(path.join(root, 'PRESENTATION.md')), 'vscode.markdown.preview.editor', vscode.ViewColumn.Two);
      } else if (message.type === 'copy' && typeof message.text === 'string' && message.text.length < 2000) {
        await vscode.env.clipboard.writeText(message.text);
        report('Prompt copied. Fill the approved scope before using it in Lens.');
      } else if (message.type === 'settings') await configure(context);
      else if (message.type === 'chrome' && ['gateway', 'lens'].includes(message.app)) {
        const url = context.globalState.get(message.app);
        if (!url) { report('Set the two live app URLs using the Live app URLs button first.'); return; }
        execFile('/usr/bin/open', ['-a', 'Google Chrome', url], error => {
          if (error) report(`Chrome could not open the app: ${error.message}`);
        });
      }
    } catch (error) { report(`Could not open this item: ${error.message}`); }
  }, null, context.subscriptions);
}

function activate(context) {
  context.subscriptions.push(vscode.commands.registerCommand('microsoftMeeting.open', () => open(context)));
  const isMeeting = vscode.workspace.workspaceFile?.fsPath === path.join(root, 'Microsoft-meeting.code-workspace');
  if (isMeeting) open(context).catch(error => vscode.window.showErrorMessage(`Meeting presenter: ${error.message}`));
}

exports.activate = activate;
