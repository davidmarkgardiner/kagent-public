// Exact names and read actions reviewed against @azure-devops/mcp 2.10.0.
export const READ_TOOLS = Object.freeze({
  core_list_projects: null,
  repo_repository: ['get', 'list'],
  repo_pull_request: ['get', 'list', 'list_by_commits'],
  pipelines_build: ['list', 'get_status', 'get_changes'],
  pipelines_build_log: ['list', 'get_content'],
  pipelines_run: ['get', 'list'],
  wit_work_item: ['get', 'get_batch', 'list_comments', 'list_revisions', 'get_type'],
  wiki: ['list_wikis', 'get_wiki', 'list_pages', 'get_page'],
});

const CODE_TOOLS = Object.freeze({
  repo_branch: ['get'],
  repo_file: ['get_content', 'list_directory'],
  repo_create_branch: null,
});

export const PUSH_TOOL = Object.freeze({
  name: 'repo_file_push',
  description: 'Commit one UTF-8 file and push it to the configured source branch. Supply the branch head commit ID just read from repo_branch; a moved branch is rejected.',
  inputSchema: {
    type: 'object', additionalProperties: false,
    properties: {
      path: { type: 'string', description: 'Absolute repository path within the configured allowed path prefix.' },
      branchName: { type: 'string', description: 'Existing source branch within the configured agent branch prefix.' },
      content: { type: 'string', description: 'Complete replacement UTF-8 file content, at most 32 KiB.' },
      changeType: { type: 'string', enum: ['add', 'edit'] },
      commitMessage: { type: 'string', description: 'Single-line commit message, at most 200 characters.' },
      expectedOldObjectId: { type: 'string', pattern: '^[0-9a-fA-F]{40}$', description: 'Current source branch head commit ID.' },
    },
    required: ['branchName', 'path', 'content', 'changeType', 'commitMessage', 'expectedOldObjectId'],
  },
  annotations: { readOnlyHint: false, destructiveHint: false },
});

function codeScope(scope) {
  if (!scope?.codeEnabled) return false;
  if (typeof scope.pathPrefix !== 'string' || !scope.pathPrefix.startsWith('/') ||
      scope.pathPrefix.includes('..') || scope.pathPrefix.includes('\\') || scope.pathPrefix.includes('//')) {
    throw new Error('Invalid code path prefix.');
  }
  if (scope.branchPrefix !== undefined &&
      (typeof scope.branchPrefix !== 'string' || !scope.branchPrefix.endsWith('/') ||
       !/^[A-Za-z0-9][A-Za-z0-9._/-]*\/$/.test(scope.branchPrefix) ||
       scope.branchPrefix.includes('//') || scope.branchPrefix.includes('..'))) {
    throw new Error('Invalid agent branch prefix.');
  }
  return true;
}

function allowedBranch(name, scope) {
  if (typeof name !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(name) ||
      name.includes('//') || name.includes('..') || name.endsWith('/') || name.endsWith('.') ||
      name.endsWith('.lock') || name.split('/').some(part => part === '.')) return false;
  return scope.branchPrefix ? name.startsWith(scope.branchPrefix) && name.length > scope.branchPrefix.length :
    name === scope.source.slice(11);
}

function escapeRegex(value) { return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

function withinPath(path, prefix) {
  if (typeof path !== 'string' || !path.startsWith('/') || path.includes('\\') ||
      path.includes('//') || path.split('/').some(part => part === '.' || part === '..' || part === '.git') ||
      /[\u0000-\u001f\u007f]/.test(path)) return false;
  const base = prefix.endsWith('/') ? prefix : `${prefix}/`;
  return path === prefix || path.startsWith(base);
}

function allowedTools(scope) {
  if (!scope) return READ_TOOLS;
  for (const field of ['project', 'repository', 'source', 'target']) {
    if (typeof scope[field] !== 'string' || !scope[field]) throw new Error('Incomplete PR creation scope.');
  }
  if (!scope.source.startsWith('refs/heads/') || !scope.target.startsWith('refs/heads/') || scope.source === scope.target) {
    throw new Error('PR source and target must be distinct branch refs.');
  }
  codeScope(scope);
  return { ...READ_TOOLS,
    ...(scope.codeEnabled ? CODE_TOOLS : {}),
    ...(scope.prEnabled === false ? {} : { repo_pull_request_write: ['create'] }) };
}

export function publishedTools(tools, scope) {
  const allowed = allowedTools(scope);
  const selected = tools.filter(t => Object.hasOwn(allowed, t.name));
  for (const name of Object.keys(allowed)) {
    if (!selected.some(t => t.name === name)) throw new Error(`Required upstream tool missing: ${name}`);
  }
  const exposed = selected.map(tool => {
    const actions = allowed[tool.name];
    if (actions && !Array.isArray(tool.inputSchema?.properties?.action?.enum)) {
      throw new Error(`Unreviewed upstream action schema: ${tool.name}`);
    }
    if (actions && actions.some(a => !tool.inputSchema.properties.action.enum.includes(a))) {
      throw new Error(`Upstream read action missing: ${tool.name}`);
    }
    const copy = structuredClone(tool);
    if (actions) copy.inputSchema.properties.action.enum = [...actions];
    if (copy.inputSchema.properties?.top) {
      copy.inputSchema.properties.top = { ...copy.inputSchema.properties.top, minimum: 1, maximum: 50, default: 50 };
    }
    if (tool.name === 'repo_pull_request_write') {
      const fields = ['action', 'project', 'repositoryId', 'sourceRefName', 'targetRefName', 'title', 'description', 'isDraft'];
      copy.inputSchema.properties = Object.fromEntries(Object.entries(copy.inputSchema.properties).filter(([name]) => fields.includes(name)));
      for (const [name, value] of Object.entries({ project: scope.project, repositoryId: scope.repository,
        targetRefName: scope.target, isDraft: true })) {
        copy.inputSchema.properties[name] = { ...copy.inputSchema.properties[name], enum: [value] };
      }
      copy.inputSchema.properties.sourceRefName = { ...copy.inputSchema.properties.sourceRefName,
        ...(scope.branchPrefix ? { pattern: `^refs/heads/${escapeRegex(scope.branchPrefix)}[A-Za-z0-9._/-]+$` } :
          { enum: [scope.source] }) };
      copy.inputSchema.required = fields.filter(f => f !== 'description');
      copy.inputSchema.additionalProperties = false;
    }
    if (scope?.codeEnabled && ['repo_branch', 'repo_file', 'repo_create_branch'].includes(tool.name)) {
      const fields = tool.name === 'repo_branch' ? ['action', 'project', 'repositoryId', 'branchName'] :
        tool.name === 'repo_file' ? ['action', 'project', 'repositoryId', 'path', 'version', 'versionType'] :
        ['project', 'repositoryId', 'branchName', 'sourceBranchName'];
      copy.inputSchema.properties = Object.fromEntries(Object.entries(copy.inputSchema.properties).filter(([name]) => fields.includes(name)));
      for (const [name, value] of Object.entries({ project: scope.project, repositoryId: scope.repository })) {
        copy.inputSchema.properties[name] = { ...copy.inputSchema.properties[name], enum: [value] };
      }
      if (tool.name === 'repo_branch') {
        copy.inputSchema.properties.branchName = { ...copy.inputSchema.properties.branchName,
          ...(scope.branchPrefix ? { pattern: `^(${escapeRegex(scope.target.slice(11))}|${escapeRegex(scope.branchPrefix)}[A-Za-z0-9._/-]+)$` } :
            { enum: [scope.source.slice(11), scope.target.slice(11)] }) };
      } else if (tool.name === 'repo_file') {
        copy.inputSchema.properties.version = { ...copy.inputSchema.properties.version,
          ...(scope.branchPrefix ? { pattern: `^(${escapeRegex(scope.target.slice(11))}|${escapeRegex(scope.branchPrefix)}[A-Za-z0-9._/-]+)$` } :
            { enum: [scope.source.slice(11), scope.target.slice(11)] }) };
        copy.inputSchema.properties.versionType = { ...copy.inputSchema.properties.versionType, enum: ['Branch'] };
      } else {
        copy.inputSchema.properties.branchName = { ...copy.inputSchema.properties.branchName,
          ...(scope.branchPrefix ? { pattern: `^${escapeRegex(scope.branchPrefix)}[A-Za-z0-9._/-]+$` } :
            { enum: [scope.source.slice(11)] }) };
        copy.inputSchema.properties.sourceBranchName = { ...copy.inputSchema.properties.sourceBranchName, enum: [scope.target.slice(11)] };
      }
      copy.inputSchema.required = fields;
      copy.inputSchema.additionalProperties = false;
    }
    copy.annotations = { ...copy.annotations,
      readOnlyHint: !['repo_pull_request_write', 'repo_create_branch'].includes(tool.name), destructiveHint: false };
    return copy;
  });
  return scope?.codeEnabled ? [...exposed, PUSH_TOOL] : exposed;
}

export function authorize(name, args = {}, scope) {
  if (name === PUSH_TOOL.name) {
    if (!codeScope(scope)) throw new Error('Code push is disabled.');
    if (Object.keys(args).some(k => !Object.hasOwn(PUSH_TOOL.inputSchema.properties, k)) ||
        !allowedBranch(args.branchName, scope) || !withinPath(args.path, scope.pathPrefix) || args.path === '/' ||
        typeof args.content !== 'string' || Buffer.byteLength(args.content, 'utf8') > 32768 ||
        !['add', 'edit'].includes(args.changeType) ||
        typeof args.commitMessage !== 'string' || !args.commitMessage.trim() ||
        args.commitMessage.length > 200 || /[\r\n]/.test(args.commitMessage) ||
        !/^[0-9a-fA-F]{40}$/.test(args.expectedOldObjectId ?? '')) {
      throw new Error('Invalid scoped code push.');
    }
    return;
  }
  const allowed = allowedTools(scope);
  if (!Object.hasOwn(allowed, name)) throw new Error('Tool is not permitted.');
  const actions = allowed[name];
  if (actions && !actions.includes(args.action)) throw new Error('Action is not permitted.');
  if (name === 'repo_pull_request_write') {
    for (const [field, value] of Object.entries({ project: scope.project, repositoryId: scope.repository,
      targetRefName: scope.target, isDraft: true })) {
      if (args[field] !== value) throw new Error('PR creation is outside the configured draft scope.');
    }
    if (!args.sourceRefName?.startsWith('refs/heads/') ||
        !allowedBranch(args.sourceRefName.slice(11), scope)) {
      throw new Error('PR source is outside the configured branch scope.');
    }
    const fields = ['action', 'project', 'repositoryId', 'sourceRefName', 'targetRefName', 'title', 'description', 'isDraft'];
    if (Object.keys(args).some(k => !fields.includes(k))) throw new Error('Additional PR effects are not allowed.');
    if (typeof args.title !== 'string' || !args.title.trim() || args.title.length > 200) throw new Error('Invalid PR title.');
  }
  if (scope?.codeEnabled && ['repo_branch', 'repo_file', 'repo_create_branch'].includes(name)) {
    const fields = name === 'repo_branch' ? ['action', 'project', 'repositoryId', 'branchName'] :
      name === 'repo_file' ? ['action', 'project', 'repositoryId', 'path', 'version', 'versionType'] :
      ['project', 'repositoryId', 'branchName', 'sourceBranchName'];
    if (Object.keys(args).some(k => !fields.includes(k)) ||
        args.project !== scope.project || args.repositoryId !== scope.repository) {
      throw new Error('Repository operation outside configured scope.');
    }
    const target = scope.target.slice(11);
    if (name === 'repo_branch' && (args.action !== 'get' ||
        !(args.branchName === target || allowedBranch(args.branchName, scope)))) {
      throw new Error('Branch read outside configured scope.');
    }
    if (name === 'repo_create_branch' && (!allowedBranch(args.branchName, scope) || args.sourceBranchName !== target)) {
      throw new Error('Branch creation outside configured scope.');
    }
    if (name === 'repo_file' &&
        (!['get_content', 'list_directory'].includes(args.action) ||
         !(args.version === target || allowedBranch(args.version, scope)) || args.versionType !== 'Branch' ||
         !withinPath(args.path, scope.pathPrefix))) {
      throw new Error('File read outside configured scope.');
    }
  }
  if (args.top !== undefined && (!Number.isInteger(args.top) || args.top < 1 || args.top > 50)) {
    throw new Error('top must be an integer between 1 and 50.');
  }
  if (name === 'wit_work_item' && args.action === 'get_batch' &&
      (!Array.isArray(args.ids) || args.ids.length > 50)) throw new Error('Batch must contain at most 50 IDs.');
}

export function boundedResult(result, maxBytes = 32768) {
  // Reject oversized complete envelopes; no invalid JSON or silent partial results.
  if (Buffer.byteLength(JSON.stringify(result), 'utf8') > maxBytes) {
    return { isError: true, content: [{ type: 'text', text:
      'Result exceeded the 32 KiB POC limit and was withheld. Narrow the query; do not reconstruct an export by paging.' }] };
  }
  return result;
}
