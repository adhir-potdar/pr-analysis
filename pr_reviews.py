from github import Github
import re

# Replace with your GitHub personal access token
TOKEN = "YOUR_GITHUB_TOKEN"

def parse_pr_url(url):
    pattern = r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, url)
    if match:
        return match.groups()
    else:
        raise ValueError("Invalid PR URL format")

def get_review_comments(pr):
    review_comments = pr.get_review_comments()
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
            "diff_hunk": comment.diff_hunk,
            "reactions": comment.reactions.total_count
        }
        comments_data.append(comment_data)

    return comments_data

def main():
    try:
        pr_url = input("Enter the GitHub PR URL: ")
        repo_owner, repo_name, pr_number = parse_pr_url(pr_url)

        g = Github(TOKEN)
        repo = g.get_repo(f"{repo_owner}/{repo_name}")
        pr = repo.get_pull(int(pr_number))

        review_comments = get_review_comments(pr)

        print(f"Total review comments: {len(review_comments)}")
        for comment in review_comments:
            print("\nComment Details:")
            print(f"ID: {comment['id']}")
            print(f"User: {comment['user']}")
            print(f"Body: {comment['body'][:100]}...")  # Truncate long comments
            print(f"Created at: {comment['created_at']}")
            print(f"Updated at: {comment['updated_at']}")
            print(f"File path: {comment['path']}")
            print(f"Position: {comment['position']}")
            print(f"Commit ID: {comment['commit_id']}")
            print(f"Original position: {comment['original_position']}")
            print(f"Diff hunk: {comment['diff_hunk'][:100]}...")  # Truncate long diff hunks
            print(f"Reactions count: {comment['reactions']}")
            print("-" * 50)

    except ValueError as ve:
        print(f"Error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
