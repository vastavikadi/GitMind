from git import Repo
from collections import defaultdict
from datetime import datetime, timedelta

def hyperlink(text, url):
    return f"\033]{url}\033\\{text}\033]\033\\"

def get_recent_commits(repo_path=".", days=7):
    repo = Repo(repo_path)

    since = datetime.now() - timedelta(days=days)

    commits = []

    for commit in repo.iter_commits():
        commit_time = datetime.fromtimestamp(commit.committed_date)

        if commit_time < since:
            break

        commits.append(
            {
                "hash": commit.hexsha[:7],
                "message": commit.message.strip(),
                "author": str(commit.author),
                "date": commit_time.date(),
            }
        )

    return commits



def file_changes_by_commit(repo_path=".", commit_hash=None, one_per_path=True, include_rename_from=False):
    """
    one_per_path:
      - True  -> one classification per final path per commit (collapses duplicates across parents)
      - False -> one record per (parent diff), i.e. multiple records for the same file across parents

    include_rename_from:
      - True  -> for renames, include old_name in the record
    """
    repo = Repo(repo_path)
    commit = repo.commit(commit_hash) if commit_hash else repo.head.commit

    # Higher number = higher priority when collapsing (one_per_path=True)
    priority = {"deleted": 5, "renamed": 4, "copied": 3, "added": 2, "modified": 1}

    # For one_per_path=True: store (action, priority, old_name_optional)
    collapsed = {}

    # For one_per_path=False: always append records
    records = []

    # Root commit: compare against empty tree (best-effort)
    if not commit.parents:
        parent_diffs = [(None, commit.diff(create_patch=False))]
    else:
        parent_diffs = [(p, commit.diff(p, create_patch=False)) for p in commit.parents]

    def add_record(path, action, rename_from=None):
        if not path:
            return
        if include_rename_from and action == "renamed":
            record = (path, action, rename_from)
        else:
            record = (path, action)

        if one_per_path:
            cur = collapsed.get(path)
            if cur is None or priority[action] > priority[cur[0]]:
                collapsed[path] = (action, priority[action], rename_from)
        else:
            records.append(record)

    for parent, diffs in parent_diffs:
        for diff in diffs:
            change_type = getattr(diff, "change_type", None)

            action = None
            path = None
            rename_from = None

            # Deleted
            if change_type == "D" or diff.deleted_file or (diff.a_path and not diff.b_path):
                action = "deleted"
                path = diff.a_path or diff.b_path

            # Renamed
            elif change_type == "R" or diff.renamed_file:
                action = "renamed"
                path = diff.b_path
                rename_from = diff.a_path

            # Copied
            elif change_type == "C" or diff.copied_file:
                action = "copied"
                path = diff.b_path

            # Added
            elif change_type == "A" or diff.new_file or (not diff.a_path and diff.b_path):
                action = "added"
                path = diff.b_path

            # Modified / fallback
            else:
                if diff.b_path:
                    # If both sides exist, treat as modified; if only b_path exists, treat as added
                    if diff.a_path and diff.b_path:
                        action = "modified"
                        path = diff.b_path
                    elif diff.b_path and not diff.a_path:
                        action = "added"
                        path = diff.b_path
                    elif diff.a_path and not diff.b_path:
                        action = "deleted"
                        path = diff.a_path
                    else:
                        continue
                else:
                    continue

            add_record(path, action, rename_from=rename_from)

    if one_per_path:
        out = []
        for path, (action, _, rename_from) in collapsed.items():
            if include_rename_from and action == "renamed":
                out.append((path, action, rename_from))
            else:
                out.append((path, action))
        return out

    return records