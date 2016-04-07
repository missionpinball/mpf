import git

mpf_repo = git.Repo('c:\\projects\\mpf')
mpf_git = git.Git('c:\\projects\\mpf')


# http://stackoverflow.com/questions/25556696/python-get-a-list-of-changed-files-between-two-commits-or-branches
def git_diff(branch1, branch2):
    fmt = '--name-only'
    commits = list()
    differ = mpf_git.diff('%s..%s' % (branch1, branch2), fmt).split("\n")
    for line in differ:
        if len(line):
            commits.append(line)

    return commits

commit_list = list(mpf_repo.iter_commits('dev', max_count=2))

deploy = True
if 'mpf/_version.py' not in git_diff(commit_list[0], commit_list[1]):
    deploy = False

# Environment variables are only available during this Python process, so write
# the result to a batch file which will be run in the next step to set it for
# real.
with open('set_env.bat', 'w') as f:
    if not deploy:
        f.write('set DEPLOY_TO_PYPI=0')
    else:
        pass
