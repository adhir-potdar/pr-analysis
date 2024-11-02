# File: pr_analysis.py

from github import Github
import re
import requests
import pytz
from bs4 import BeautifulSoup
from pr_analysis_config import PRAnalysisConfig

class PRAnalysis:
    def __init__(self, properties_file='pr_analysis.properties'):
        self.pr_analysis_config = PRAnalysisConfig(properties_file)
        self.properties = self.pr_analysis_config.read_properties()
        
        if self.properties:
            self.git_provider = self.properties.get('git.provider', '')
            self.git_access_token = self.properties.get('git.access_token', '')
            self.git_domain = self.properties.get('git.domain', '')
            self.github = Github(self.git_access_token)
            self.default_reviewer = self.properties.get('default.reviewer', '')
            self.is_ai_reviewer = False
            self.ai_reviewer = self.properties.get('ai.reviewer', '')
            self.ai_reviewer_regex = self.properties.get('ai.reviewer.regex', '')
            if self.ai_reviewer and self.ai_reviewer_regex:
                self.is_ai_reviewer = True
        else:
            print("Failed to initialize PRAnalysis due to missing or invalid properties.")

    def display_config(self):
        print("=" * 50)
        print("\nPull Request Configuration:")
        print(f"Git Provider: {self.git_provider}")
        print(f"Git Access Token: {self.git_access_token}")
        print(f"Git Domain: {self.git_domain}")
        print(f"Default Reviewer: {self.default_reviewer}")
        print(f"Is AI Reviewer Available?: {self.is_ai_reviewer}")
        print(f"AI Reviewer: {self.ai_reviewer}")
        print(f"AI Reviewer RegEx: {self.ai_reviewer_regex}")
        print("=" * 50)

    def parse_pr_url(self):
        # Escape special characters in domain to handle domains that might contain them
        escaped_domain = re.escape(self.git_domain)
        pattern = fr"https://{escaped_domain}/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, self.url)
        if match:
            return match.groups()
        else:
            raise ValueError("Invalid PR URL format")

    def convert_html_to_plaintext(self):
        # Parse the HTML content
        soup = BeautifulSoup(self.html_description, 'html.parser')

        # Extract text and replace <br> tags with newlines
        for br in soup.find_all("br"):
            br.replace_with("\n")

        # Get the text content
        plain_text = soup.get_text(strip=True)

        # Replace multiple newlines with a single newline
        plain_text = re.sub(r'\n+', '\n', plain_text)

        return plain_text

    def extract_pr_metadata(self):
        self.repo_owner, self.repo_name, self.pr_number = self.parse_pr_url()
        self.repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")

        self.pr = self.repo.get_pull(int(self.pr_number))
        self.creation_time = self.pr.created_at.replace(tzinfo=pytz.UTC)

        # Get source and target branches
        self.source_branch = self.pr.head.ref  # Source/Head branch
        self.target_branch = self.pr.base.ref  # Target/Base branch

        # Get PR description
        self.html_description = self.pr.body
        #self.html_description = 'Sample description'
        self.description = self.convert_html_to_plaintext()

        # Get merge and close timestamps
        self.merge_time = self.pr.merged_at
        self.close_time = self.pr.closed_at
        
        # Convert to UTC if timestamps are not None
        if self.merge_time:
            self.merge_time = self.merge_time.replace(tzinfo=timezone.utc)
        if self.close_time:
            self.close_time = self.close_time.replace(tzinfo=timezone.utc)

    def separate_pr_commits(self):
        self.all_commits = self.pr.get_commits() 
        self.incremental_commits = []

        for commit in self.all_commits:
            commit_time = commit.commit.committer.date.replace(tzinfo=pytz.UTC)
            if commit_time > self.creation_time:
                self.incremental_commits.append(commit)
                #print('Commit after PR Creation: ', str(commit))

    def print_pr_commits(self, commits):
        for commit in commits:
            print(f"Commit SHA: {commit.sha}")
            print(f"Author: {commit.commit.author.name} <{commit.commit.author.email}>")
            print(f"HTML URL: {commit.html_url}")
            print(f"Commit message: {commit.commit.message}")
            print(f"Commit time: {commit.commit.committer.date}")
            # Print detailed stats
            print("\nStats:")
            if commit.stats:
                print(f"Additions: {commit.stats.additions}")
                print(f"Deletions: {commit.stats.deletions}")
                print(f"Total changes: {commit.stats.total}")
            # Print files changed
            print("\nFiles changed:")
            for file in commit.files:
                print(f"- {file.filename} ({file.status})")
                print(f"  Changes: +{file.additions} -{file.deletions}")
            print("---")

    def print_pr_metadata(self):
        print("=" * 50)
        print("\nPull Request Details:")
        print("URL: ", self.url)
        print("Repository Name: ", self.repo_name)
        print("Repository Owner: ", self.repo_owner)
        print("PR Number: ", self.pr_number)
        print("Source Branch: ", self.source_branch)
        print("Target Branch: ", self.target_branch)
        print("Creation Timestamp (UTC): ", self.creation_time)
        print("Description: ", self.description)
        print("Merge Timestamp (UTC): ", self.merge_time)
        print("Close Timestamp (UTC): ", self.close_time)
        print("=" * 50)

    def get_diff_hunk_for_comment(self, comment):
        lines = []
        for file in self.pr.get_files():
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

    def get_review_comments(self):
        self.review_comments = self.pr.get_review_comments()
        #self.review_comments = self.pr.get_comments()
        self.comments_data = []
        self.num_comments = 0
        self.ai_reviewer_num_comments = 0

        for comment in self.review_comments:
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
            }

            #diff_hunk = self.get_diff_hunk_for_comment(comment)
            #comment_data['diff_hunk'] = diff_hunk
            #if diff_hunk:
            #    print(f"Comment ID: {comment.id}")
            #    print(f"Diff Hunk:\n{diff_hunk}")
            #    print("---")
            #else:
            #    print(f"No diff hunk found for comment ID: {comment.id}")

            # Define the pattern
            #pattern = r'<div id="issue"><b>(.*?)</b></div>.*?<div id="fix">(.*?)</div>.*?<div id="code">(.*?)</div>.*?<a href=(.*?)>#(\w+)</a>'
            #if self.is_ai_reviewer and re.search(pattern, comment_data['body'], re.DOTALL):
            if self.is_ai_reviewer and re.search(self.ai_reviewer_regex, comment_data['body'], re.DOTALL):
                comment_data['reviewer'] = self.ai_reviewer
                self.ai_reviewer_num_comments = self.ai_reviewer_num_comments + 1
            else:
                comment_data['reviewer'] = self.default_reviewer
            self.num_comments = self.num_comments + 1

            self.comments_data.append(comment_data)

    def print_review_comments(self):
        print("=" * 50)
        print("\nPull Request Review Comments:")
        for comment in self.comments_data:
            print("-" * 50)
            print("\nComment Details:")
            print(f"ID: {comment['id']}")
            print(f"User: {comment['user']}")
            #print(f"Body: {comment['body'][:100]}...")  # Truncate long comments
            print(f"Body: {comment['body']}")
            print(f"Created at: {comment['created_at']}")
            print(f"Updated at: {comment['updated_at']}")
            print(f"File path: {comment['path']}")
            print(f"Position: {comment['position']}")
            print(f"Commit ID: {comment['commit_id']}")
            print(f"Original position: {comment['original_position']}")
            print(f"Diff hunk len: {len(comment['diff_hunk'])}")
            #print(f"Diff hunk: {comment['diff_hunk']}")
            print(f"Diff hunk: {comment['diff_hunk'][:100]}...")  # Truncate long diff hunks
            print(f"Code Reviewer: {comment['reviewer']}")
            #print(f"Reactions count: {comment['reactions']}")
            print("-" * 50)
        print("=" * 50)

    def build_pr_analysis_data(self, pr_url):
        try:
            self.url = pr_url
            self.extract_pr_metadata()
            self.print_pr_metadata()
            self.separate_pr_commits()
            print("Total commits including PR creation commit: ", self.all_commits.totalCount)
            #self.print_pr_commits(self.all_commits)
            print("Total incremental commits i.e. commits after PR creation: ", len(self.incremental_commits))
            #self.print_pr_commits(self.incremental_commits)

            self.get_review_comments()
            print("=" * 50)
            #print(f"Total review comments: {len(self.comments_data)}")
            print(f"Total review comments: {self.num_comments}")
            print(f"Total AI review comments: {self.ai_reviewer_num_comments}")
            #self.print_review_comments()
            print("=" * 50)

        except ValueError as ve:
            print(f"Error: {ve}")
        except Exception as e:
            print(f"An error occurred: {e}")

def main(): 
    pr_analysis = PRAnalysis()
    pr_analysis.display_config()
    pr_url = input("Enter the GitHub PR URL: ")
    pr_analysis.build_pr_analysis_data(pr_url)

if __name__ == "__main__":
    main()

