from github import Github
import re
import requests

# Replace with your GitHub personal access token
TOKEN = "TOKEN"

def get_diff_hunk_for_comment(pr, comment):
    lines = []
    for file in pr.get_files():
        if file.filename == comment.path:
            patch = file.patch
            if patch:
                lines = patch.split('\n')
                hunk_pattern = re.compile(r'^@@ -\d+,\d+ \+(\d+),\d+ @@')
                
                current_line = 0
                for i, line in enumerate(lines):
                    hunk_match = hunk_pattern.match(line)
                    if hunk_match:
                        current_line = int(hunk_match.group(1))
                        continue
                    
                    #if current_line == comment.position:
                    #    start = max(0, i - 3)
                    #    end = min(len(lines), i + 4)
                    #    return '\n'.join(lines[start:end])
                    
                    if not line.startswith('-'):
                        current_line += 1

    
    return '\n'.join(lines)

def get_review_comments_with_diff_hunks(repo_owner, repo_name, pr_number, token):
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/pulls/{pr_number}/comments"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(url, headers=headers)
    print('GitHub API response: ', response)
    print('GitHub API response JSON: ', response.json())
    return response.json()

def parse_pr_url(url):
    pattern = r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, url)
    if match:
        return match.groups()
    else:
        raise ValueError("Invalid PR URL format")

def get_review_comments(pr):
    review_comments = pr.get_review_comments()
    #review_comments = pr.get_comments()
    comments_data = []

    for comment in review_comments:
        comment_data = {
            "id": comment.id,
            "user": comment.user.login,
            "body": comment.body,
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
            "path": comment.path,
            "position": comment.position,
            "commit_id": comment.commit_id,
            "original_position": comment.original_position,
            "diff_hunk": comment.diff_hunk
#            "diff_hunk": comment.diff_hunk,
#            "reactions": comment.reactions.total_count
        }

        diff_hunk = get_diff_hunk_for_comment(pr, comment)
        comment_data['diff_hunk'] = diff_hunk
        #if diff_hunk:
        #    print(f"Comment ID: {comment.id}")
        #    print(f"Diff Hunk:\n{diff_hunk}")
        #    print("---")
        #else:
        #    print(f"No diff hunk found for comment ID: {comment.id}")

        comments_data.append(comment_data)

    return comments_data

def main():
    try:
        pr_url = input("Enter the GitHub PR URL: ")
        repo_owner, repo_name, pr_number = parse_pr_url(pr_url)

        g = Github(TOKEN)
        repo = g.get_repo(f"{repo_owner}/{repo_name}")
        pr = repo.get_pull(int(pr_number))

        # Get source and target branches
        source_branch = pr.head.ref  # Source/Head branch
        target_branch = pr.base.ref  # Target/Base branch

        # Get PR description
        description = pr.body

        # Get merge and close timestamps
        merge_time = pr.merged_at
        close_time = pr.closed_at
        
        # Convert to UTC if timestamps are not None
        if merge_time:
            merge_time = merge_time.replace(tzinfo=timezone.utc)
        if close_time:
            close_time = close_time.replace(tzinfo=timezone.utc)

        print("=" * 50)
        print("\nPull Request Details:")
        print("Repository Name: ", repo_name)
        print("Repository Owner: ", repo_owner)
        print("PR Number: ", pr_number)
        print("Source Branch: ", source_branch)
        print("Target Branch: ", target_branch)
        print("Description: ", description)
        print("Merge Timestamp: ", merge_time)
        print("Close Timestamp: ", close_time)

        review_comments = get_review_comments(pr)

        print(f"Total review comments: {len(review_comments)}")
        for comment in review_comments:
            print("-" * 50)
            print("\nComment Details:")
            print(f"ID: {comment['id']}")
            print(f"User: {comment['user']}")
            print(f"Body: {comment['body'][:100]}...")  # Truncate long comments
            #print(f"Body: {comment['body']}")
            print(f"Created at: {comment['created_at']}")
            print(f"Updated at: {comment['updated_at']}")
            print(f"File path: {comment['path']}")
            print(f"Position: {comment['position']}")
            print(f"Commit ID: {comment['commit_id']}")
            print(f"Original position: {comment['original_position']}")
            print(f"Diff hunk len: {len(comment['diff_hunk'])}")
            #print(f"Diff hunk: {comment['diff_hunk']}")
            print(f"Diff hunk: {comment['diff_hunk'][:100]}...")  # Truncate long diff hunks
            #print(f"Reactions count: {comment['reactions']}")
            print("-" * 50)

        #comments = get_review_comments_with_diff_hunks(repo_owner, repo_name, pr_number, TOKEN)
        #for comment in comments:
        #    print(comment['diff_hunk'])

        print("=" * 50)

    except ValueError as ve:
        print(f"Error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
