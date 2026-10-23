import { authorize } from './policy.mjs';

export class CodePushError extends Error {}

// The pinned Microsoft MCP 2.10.0 has branch creation and file reads but no
// file-commit/push tool. Use the documented Azure DevOps Git Pushes API for one
// reviewed file change. The server, organization and repository come from
// deployment configuration, never from model-supplied URLs.
export async function pushFile(scope, args, { organization, encodedPat, fetchImpl = fetch } = {}) {
  authorize('repo_file_push', args, scope);
  if (typeof organization !== 'string' || !/^[a-zA-Z0-9_-]+$/.test(organization) ||
      typeof encodedPat !== 'string' || !/^[A-Za-z0-9+/]+={0,2}$/.test(encodedPat) ||
      !Buffer.from(encodedPat, 'base64').toString('utf8').includes(':')) {
    throw new Error('Azure DevOps authentication is not configured.');
  }
  const url = new URL(`https://dev.azure.com/${encodeURIComponent(organization)}/${encodeURIComponent(scope.project)}/_apis/git/repositories/${encodeURIComponent(scope.repository)}/pushes`);
  url.searchParams.set('api-version', '7.1');
  const response = await fetchImpl(url, {
    method: 'POST', redirect: 'error', signal: AbortSignal.timeout(15000),
    headers: { Authorization: `Basic ${encodedPat}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      refUpdates: [{ name: `refs/heads/${args.branchName}`, oldObjectId: args.expectedOldObjectId }],
      commits: [{ comment: args.commitMessage, changes: [{
        changeType: args.changeType,
        item: { path: args.path },
        newContent: { content: args.content, contentType: 'rawtext' },
      }] }],
    }),
  });
  if (!response.ok) {
    const reason = response.status === 401 ? 'PAT authentication failed (401).' :
      response.status === 403 ? 'PAT identity lacks permission or a repository policy denied the push (403).' :
      response.status === 404 ? 'Configured project, repository or branch was not found (404).' :
      [409, 412].includes(response.status) ? 'Branch head changed or a concurrent push conflicted.' :
      'Azure DevOps rejected or did not confirm the push.';
    throw new CodePushError(`${reason} Read the branch head before any retry.`);
  }
  const result = await response.json();
  const commitId = result?.commits?.[0]?.commitId;
  if (!/^[0-9a-fA-F]{40}$/.test(commitId ?? '')) {
    throw new CodePushError('Push response lacked a confirmed commit ID. Read the branch head before any retry.');
  }
  return { pushId: result.pushId, commitId, branch: `refs/heads/${args.branchName}`, path: args.path };
}
