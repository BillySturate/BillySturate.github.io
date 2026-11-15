#!/usr/bin/env python3
"""Create only the explicitly named isolated GitHub preview; never modify production."""
import json
import shutil
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
REPO = 'BillySturate/silas-homepage-preview'

def run(*args, **kwargs):
    return subprocess.run(args, cwd=ROOT, text=True, check=True, **kwargs)

if not shutil.which('gh'):
    raise SystemExit('GitHub CLI is not installed. Install gh and complete gh auth login, or connect the GitHub integration. No repository was changed.')
run('gh', 'auth', 'status')
account = run('gh', 'api', 'user', capture_output=True).stdout
if json.loads(account)['login'].lower() != 'billysturate':
    raise SystemExit('The preview must be created under BillySturate; the authenticated account differs.')
if run('git', 'status', '--porcelain', capture_output=True).stdout.strip():
    raise SystemExit('Commit the source before publishing a reviewable preview.')
existing = subprocess.run(['gh','repo','view',REPO,'--json','nameWithOwner'],cwd=ROOT,capture_output=True,text=True)
if existing.returncode:
    run('gh','repo','create',REPO,'--public','--description','Isolated preview of the Hao Liu academic homepage and preserved blog')
remotes = run('git','remote',capture_output=True).stdout.split()
if 'preview' in remotes:
    actual = run('git','remote','get-url','preview',capture_output=True).stdout.strip()
    if actual not in ('https://github.com/' + REPO + '.git', 'git@github.com:' + REPO + '.git'):
        raise SystemExit('Existing preview remote differs; refusing to replace it.')
else:
    run('git','remote','add','preview','https://github.com/' + REPO + '.git')
run('gh','auth','setup-git')
run('git','push','preview','HEAD:main')
settings = subprocess.run(['gh','api',f'repos/{REPO}/pages'],cwd=ROOT,capture_output=True,text=True)
if settings.returncode:
    run('gh','api','--method','POST',f'repos/{REPO}/pages','-f','build_type=workflow')
else:
    run('gh','api','--method','PUT',f'repos/{REPO}/pages','-f','build_type=workflow')
run('gh','workflow','run','ci-preview.yml','--repo',REPO,'--ref','main')
print('Preview workflow started. The URL is not verified until deployment succeeds: https://billysturate.github.io/silas-homepage-preview/')
