import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { READ_TOOLS, publishedTools, authorize } from '../policy.mjs';
import { createProtocolServer } from '../bridge.mjs';
import { pushFile } from '../code-push.mjs';

const scope = { project: 'sandbox', repository: 'app', source: 'refs/heads/agent/demo',
  target: 'refs/heads/main', pathPrefix: '/src/', branchPrefix: 'agent/', codeEnabled: true, prEnabled: true };
const tools = Object.entries(READ_TOOLS).map(([name, actions]) => ({ name,
  inputSchema: { type: 'object', properties: actions ? { action: { type: 'string', enum: actions } } : {} } }));
tools.push({ name: 'repo_branch', inputSchema: { type: 'object', properties: {
  action: { type: 'string', enum: ['get', 'list'] }, project: { type: 'string' }, repositoryId: { type: 'string' },
  branchName: { type: 'string' }, top: { type: 'number' },
} } });
tools.push({ name: 'repo_file', inputSchema: { type: 'object', properties: {
  action: { type: 'string', enum: ['get_content', 'list_directory'] }, project: { type: 'string' },
  repositoryId: { type: 'string' }, path: { type: 'string' }, version: { type: 'string' },
  versionType: { type: 'string', enum: ['Commit', 'Branch'] }, recursive: { type: 'boolean' },
} } });
tools.push({ name: 'repo_create_branch', inputSchema: { type: 'object', properties: {
  project: { type: 'string' }, repositoryId: { type: 'string' }, branchName: { type: 'string' },
  sourceBranchName: { type: 'string' }, sourceCommitId: { type: 'string' },
} } });
tools.push({ name: 'repo_pull_request_write', inputSchema: { type: 'object', properties: {
  action: { type: 'string', enum: ['create', 'update'] }, project: { type: 'string' },
  repositoryId: { type: 'string' }, sourceRefName: { type: 'string' }, targetRefName: { type: 'string' },
  title: { type: 'string' }, description: { type: 'string' }, isDraft: { type: 'boolean' },
} } });

test('code tools expose only configured branch, repository and PR action', () => {
  const catalog = publishedTools(tools, scope);
  assert.equal(catalog.length, 13);
  const branch = catalog.find(t => t.name === 'repo_create_branch');
  assert.match(branch.inputSchema.properties.branchName.pattern, /agent/);
  assert.equal(branch.inputSchema.properties.sourceCommitId, undefined);
  const push = catalog.find(t => t.name === 'repo_file_push');
  assert.equal(push.annotations.readOnlyHint, false);
  assert.deepEqual(catalog.find(t => t.name === 'repo_pull_request_write').inputSchema.properties.action.enum, ['create']);
  assert.doesNotThrow(() => authorize('repo_create_branch', { project: scope.project,
    repositoryId: scope.repository, branchName: 'agent/second', sourceBranchName: 'main' }, scope));
  assert.throws(() => authorize('repo_create_branch', { project: scope.project,
    repositoryId: scope.repository, branchName: 'feature/second', sourceBranchName: 'main' }, scope));
  assert.doesNotThrow(() => authorize('repo_pull_request_write', { action: 'create',
    project: scope.project, repositoryId: scope.repository,
    sourceRefName: 'refs/heads/agent/second', targetRefName: scope.target,
    title: 'Demo', isDraft: true }, scope));
});

test('protocol forwards only scoped upstream actions and one bounded push', async () => {
  const calls = [], pushes = [];
  const upstream = { tools, client: { close: async () => {}, callTool: async request => {
    calls.push(request); return { content: [{ type: 'text', text: '{}' }] };
  } } };
  const server = createProtocolServer(upstream, scope, { pushFileImpl: async (_scope, args) => {
    pushes.push(args); return { pushId: 1, commitId: 'b'.repeat(40), branch: `refs/heads/${args.branchName}`, path: args.path };
  } });
  const [ct, st] = InMemoryTransport.createLinkedPair();
  await server.connect(st);
  const client = new Client({ name: 'code-test', version: '1' });
  const file = { action: 'get_content', project: scope.project, repositoryId: scope.repository,
    path: '/src/app.ts', version: 'agent/demo', versionType: 'Branch' };
  const branch = { project: scope.project, repositoryId: scope.repository,
    branchName: 'agent/demo', sourceBranchName: 'main' };
  const push = { branchName: 'agent/demo', path: '/src/app.ts', content: 'export const ok = true;\n', changeType: 'edit',
    commitMessage: 'Update app', expectedOldObjectId: 'a'.repeat(40) };
  try {
    await client.connect(ct);
    for (const request of [
      { name: 'repo_create_branch', arguments: branch },
      { name: 'repo_file', arguments: file },
      { name: 'repo_file_push', arguments: push },
    ]) assert.equal((await client.callTool(request)).isError, undefined);
    for (const request of [
      { name: 'repo_create_branch', arguments: { ...branch, branchName: 'main' } },
      { name: 'repo_create_branch', arguments: { ...branch, sourceCommitId: 'a'.repeat(40) } },
      { name: 'repo_file', arguments: { ...file, path: '/other/file.ts' } },
      { name: 'repo_file', arguments: { ...file, version: 'other' } },
      { name: 'repo_file_push', arguments: { ...push, path: '/src/../other/file.ts' } },
      { name: 'repo_file_push', arguments: { ...push, branchName: 'other/demo' } },
      { name: 'repo_file_push', arguments: { ...push, content: 'x'.repeat(32769) } },
      { name: 'repo_file_push', arguments: { ...push, expectedOldObjectId: '0' } },
      { name: 'repo_file_push', arguments: { ...push, unexpected: true } },
    ]) assert.equal((await client.callTool(request)).isError, true);
    assert.equal(calls.length, 2);
    assert.equal(pushes.length, 1);
  } finally { await client.close(); await server.close(); }
});

test('PAT push uses one fixed Azure DevOps endpoint and optimistic branch head', async () => {
  const args = { branchName: 'agent/demo', path: '/src/app.ts', content: 'updated', changeType: 'edit',
    commitMessage: 'Update app', expectedOldObjectId: 'a'.repeat(40) };
  const encodedPat = Buffer.from('mcp@example.invalid:sample').toString('base64');
  const calls = [];
  const fetchImpl = async (url, init) => {
    calls.push({ url: String(url), init });
    return { ok: true, json: async () => ({ pushId: 7, commits: [{ commitId: 'b'.repeat(40) }] }) };
  };
  const result = await pushFile(scope, args, { organization: 'example-org', encodedPat, fetchImpl });
  assert.equal(result.commitId, 'b'.repeat(40));
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, 'https://dev.azure.com/example-org/sandbox/_apis/git/repositories/app/pushes?api-version=7.1');
  assert.equal(calls[0].init.redirect, 'error');
  assert.equal(calls[0].init.headers.Authorization, `Basic ${encodedPat}`);
  const body = JSON.parse(calls[0].init.body);
  assert.deepEqual(body.refUpdates, [{ name: `refs/heads/${args.branchName}`, oldObjectId: args.expectedOldObjectId }]);
  assert.equal(body.commits[0].changes[0].item.path, args.path);
  assert.equal(body.commits[0].changes[0].newContent.content, args.content);
  await assert.rejects(pushFile(scope, args, { organization: 'example-org', encodedPat,
    fetchImpl: async () => ({ ok: false }) }), /Read the branch head/);
});
