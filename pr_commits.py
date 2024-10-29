from github import Github
from datetime import datetime
import pytz
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

def get_pr_and_commits(repo, pr_number):
    pr = repo.get_pull(pr_number)
    creation_time = pr.created_at.replace(tzinfo=pytz.UTC)
    commits = pr.get_commits()
    return pr, creation_time, commits

def get_commits_after_creation(commits, creation_time):
    commits_after_creation = []
    for commit in commits:
        commit_time = commit.commit.committer.date.replace(tzinfo=pytz.UTC)
        if commit_time > creation_time:
            commits_after_creation.append(commit)
    return commits_after_creation

def main():
    try:
        pr_url = input("Enter the GitHub PR URL: ")
        repo_owner, repo_name, pr_number = parse_pr_url(pr_url)
        
        g = Github(TOKEN)
        repo = g.get_repo(f"{repo_owner}/{repo_name}")
        
        pr, creation_time, commits = get_pr_and_commits(repo, int(pr_number))
        print(f"PR #{pr_number} was created at: {creation_time}")
        
        commits_after_creation = get_commits_after_creation(commits, creation_time)
        print(f"Number of commits after PR creation: {len(commits_after_creation)}")
        
        for commit in commits_after_creation:
            print(f"Commit SHA: {commit.sha}")
            print(f"Commit message: {commit.commit.message}")
            print(f"Commit time: {commit.commit.committer.date}")
            print("---")
    
    except ValueError as ve:
        print(f"Error: {ve}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
