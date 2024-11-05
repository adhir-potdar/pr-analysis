# File: pr_analysis.py

from datetime import datetime, timezone
from github import Github
import json
import re
import requests
import pytz
from bs4 import BeautifulSoup
from pr_analysis_config import PRAnalysisConfig
import traceback

class PRAnalysis:
    def __init__(self, properties_file='pr_analysis.properties'):
        self.pr_analysis_config = PRAnalysisConfig(properties_file)
        self.properties = self.pr_analysis_config.read_properties()

        #TODO: Validate git access token using API.
        #TODO: Validate the PR URL against the GIT domain.
        
        if self.properties:
            self.git_provider = self.properties.get('git.provider', '')
            self.git_access_token = self.properties.get('git.access_token', '')
            self.git_domain = self.properties.get('git.domain', '')
            if (self.git_provider.endswith("ENTERPRISE")):
                self.base_url = self.git_domain + "/api/v3"
                self.github = Github(base_url=self.base_url, login_or_token=self.git_access_token)
            else:
                self.base_url = self.git_domain
                self.github = Github(self.git_access_token)
            print("Created the github instance.")
            self.default_reviewer = self.properties.get('default.reviewer', '')
            self.is_ai_reviewer = False
            self.ai_reviewer = self.properties.get('ai.reviewer', '')
            self.ai_reviewer_regex = self.properties.get('ai.reviewer.regex', '')
            if self.ai_reviewer and self.ai_reviewer_regex:
                self.is_ai_reviewer = True
            self.is_valid_config = True
        else:
            print("Failed to initialize PRAnalysis due to missing or invalid properties.")
            self.is_valid_config = False

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
        pattern = fr"{escaped_domain}/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, self.url)
        if match:
            print("PR URL is valid.")
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
        print("Repo name: ", self.repo_name)
        self.repo = self.github.get_repo(f"{self.repo_owner}/{self.repo_name}")
        #print("Got the repo.")

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
        else:
            self.merge_time = 'N.A.'
        if self.close_time:
            self.close_time = self.close_time.replace(tzinfo=timezone.utc)
        else:
            self.close_time = 'N.A.'

    def separate_pr_commits(self):
        self.all_commits = self.pr.get_commits() 
        self.incremental_commits = []
        self.pr_creation_commits = []

        for commit in self.all_commits:
            commit_time = commit.commit.committer.date.replace(tzinfo=pytz.UTC)
            if commit_time > self.creation_time:
                self.incremental_commits.append(commit)
            else:
                self.pr_creation_commits.append(commit)

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

            #pattern = r'<div id="issue"><b>(.*?)</b></div>.*?<div id="fix">(.*?)</div>.*?<div id="code">(.*?)</div>.*?<a href=(.*?)>#(\w+)</a>'
            #if self.is_ai_reviewer and re.search(pattern, comment_data['body'], re.DOTALL):
            #ai_reviewer_str_1 = "<div id=\"suggestion\">"
            #ai_reviewer_str_2 = "<div id=\"issue\">"
            #ai_reviewer_str_3 = "<b>Code suggestion</b>"
            #if self.is_ai_reviewer and (ai_reviewer_str_1 in comment_data['body']) and (ai_reviewer_str_2 in comment_data['body']) and (ai_reviewer_str_3 in comment_data['body']):
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

    def extract_first_last_reviews_after_timestamp(self, timestamp):
        first_review = None
        last_review = None

        for comment in self.comments_data:
            if comment['created_at'] >= timestamp:
                if not first_review:
                    first_review = comment
                last_review = comment

        return first_review, last_review
        
    def extract_first_last_reviews_before_timestamp(self, timestamp):
        first_review = None
        last_review = None

        for comment in self.comments_data:
            if comment['created_at'] <= timestamp:
                if not first_review:
                    first_review = comment
                last_review = comment

        return first_review, last_review
        
    def build_pr_analysis_dict(self):
        pr_analysis_dict = {}

        pr_analysis_dict['url'] = self.url
        pr_analysis_dict['repo_name'] = self.repo_name
        pr_analysis_dict['source_branch'] = self.source_branch
        pr_analysis_dict['target_branch'] = self.target_branch
        pr_analysis_dict['repo_owner'] = self.repo_owner
        pr_analysis_dict['creation_timestamp'] = str(self.creation_time)
        pr_analysis_dict['description'] = self.description
        pr_analysis_dict['num_commits_before_pr_creation'] = len(self.pr_creation_commits)
        pr_analysis_dict['num_commits_incremental'] = len(self.incremental_commits)
        pr_analysis_dict['num_comments_made_by_human'] = self.num_comments - self.ai_reviewer_num_comments
        pr_analysis_dict['num_comments_made_by_ai'] = self.ai_reviewer_num_comments
        pr_analysis_dict['merge_timestamp'] = str(self.merge_time)
        pr_analysis_dict['close_timestamp'] = str(self.close_time)

        #build the 1st & last review suggestion data
        first_review, last_review = self.extract_first_last_reviews_after_timestamp(datetime.fromtimestamp(0, tz=timezone.utc))
        if first_review:
           pr_analysis_dict['first_suggestion_review_type'] = first_review['reviewer']
           pr_analysis_dict['first_suggestion_review_timestamp'] = str(first_review['created_at'])
        else:
           pr_analysis_dict['first_suggestion_review_type'] = 'N.A.'
           pr_analysis_dict['first_suggestion_review_timestamp'] = 'N.A.'

        if last_review:
            pr_analysis_dict['last_suggestion_review_type'] = last_review['reviewer']
            pr_analysis_dict['last_suggestion_review_timestamp'] = str(last_review['created_at'])
        else:
            pr_analysis_dict['last_suggestion_review_type'] = 'N.A.'
            pr_analysis_dict['last_suggestion_review_timestamp'] = 'N.A.'

        #build the 1st & last commit and review data for PR creation and before 1st incremental commit ==> for full review
        #TODO: this we will have to correlate with Bito analytics data if available.
        num_pr_creation_commits = len(self.pr_creation_commits)
        if num_pr_creation_commits > 0:
            first_review, last_review = self.extract_first_last_reviews_before_timestamp(self.incremental_commits[0].commit.committer.date)
            if first_review:
                pr_analysis_dict['first_full_review_type'] = first_review['reviewer']
                pr_analysis_dict['first_full_review_timestamp'] = str(first_review['created_at'])
            else:
                pr_analysis_dict['first_full_review_type'] = 'N.A.'
                pr_analysis_dict['first_full_review_timestamp'] = 'N.A.'

            if last_review:
                pr_analysis_dict['last_full_review_type'] = last_review['reviewer']
                pr_analysis_dict['last_full_review_timestamp'] = str(last_review['created_at'])
            else:
                pr_analysis_dict['last_full_review_type'] = 'N.A.'
                pr_analysis_dict['last_full_review_timestamp'] = 'N.A.'

        else:
            pr_analysis_dict['first_full_review_type'] = 'N.A.'
            pr_analysis_dict['first_full_review_timestamp'] = 'N.A.'
            pr_analysis_dict['last_full_review_type'] = 'N.A.'
            pr_analysis_dict['last_full_review_timestamp'] = 'N.A.'
                
        #build the 1st & last incremental commit and review data.
        #TODO: this we will have to correlate with Bito analytics data if available.
        num_incremental_commits = len(self.incremental_commits)
        if num_incremental_commits > 0:
            pr_analysis_dict['first_incremental_commit_timestamp'] = str(self.incremental_commits[0].commit.committer.date)
            first_review, last_review = self.extract_first_last_reviews_after_timestamp(self.incremental_commits[0].commit.committer.date)
            if first_review:
                pr_analysis_dict['first_incremental_review_type'] = first_review['reviewer']
                pr_analysis_dict['first_incremental_review_timestamp'] = str(first_review['created_at'])
            else:
                pr_analysis_dict['first_incremental_review_type'] = 'N.A.'
                pr_analysis_dict['first_incremental_review_timestamp'] = 'N.A.'

            pr_analysis_dict['last_incremental_commit_timestamp'] = str(self.incremental_commits[num_incremental_commits - 1].commit.committer.date)
            first_review, last_review = self.extract_first_last_reviews_after_timestamp(self.incremental_commits[num_incremental_commits - 1].commit.committer.date)
            if last_review:
                pr_analysis_dict['last_incremental_review_type'] = last_review['reviewer']
                pr_analysis_dict['last_incremental_review_timestamp'] = str(last_review['created_at'])
            else:
                pr_analysis_dict['last_incremental_review_type'] = 'N.A.'
                pr_analysis_dict['last_incremental_review_timestamp'] = 'N.A.'
                
        else:
            pr_analysis_dict['first_incremental_commit_timestamp'] = 'N.A.'
            pr_analysis_dict['first_incremental_review_type'] = 'N.A.'
            pr_analysis_dict['first_incremental_review_timestamp'] = 'N.A.'
            pr_analysis_dict['last_incremental_commit_timestamp'] = 'N.A.'
            pr_analysis_dict['last_incremental_review_type'] = 'N.A.'
            pr_analysis_dict['last_incremental_review_timestamp'] = 'N.A.'

        return pr_analysis_dict

    def build_pr_analysis_data(self, pr_url):
        if not pr_url:
            print("Failed to get PR analysis due to invalid PR URL.")
            return {}

        try:
            self.url = pr_url
            self.extract_pr_metadata()
            self.print_pr_metadata()
            self.separate_pr_commits()
            print("Total commits including PR creation commit: ", self.all_commits.totalCount)
            #self.print_pr_commits(self.all_commits)
            print("Total PR creation commits i.e. commits before PR creation: ", len(self.pr_creation_commits))
            #self.print_pr_commits(self.pr_creation_commits)
            print("Total incremental commits i.e. commits after PR creation: ", len(self.incremental_commits))
            #self.print_pr_commits(self.incremental_commits)

            self.get_review_comments()
            print("=" * 50)
            #print(f"Total review comments: {len(self.comments_data)}")
            print(f"Total review comments: {self.num_comments}")
            print(f"Total Human review comments: {self.num_comments - self.ai_reviewer_num_comments}")
            print(f"Total AI review comments: {self.ai_reviewer_num_comments}")
            #self.print_review_comments()
            print("=" * 50)

            pr_analysis_dict = self.build_pr_analysis_dict()
            return pr_analysis_dict

        except ValueError as ve:
            print(f"Error: {ve}")
            print("Failed to get PR analysis.")
            #traceback.print_exc()
            return {}

        except Exception as e:
            print(f"An error occurred: {e}")
            print("Failed to get PR analysis.")
            #traceback.print_exc()
            return {}

def main(): 
    pr_analysis = PRAnalysis()
    if pr_analysis.is_valid_config:
        pr_analysis.display_config()
        pr_url = input("Enter the GitHub PR URL: ")
        pr_analysis_dict = pr_analysis.build_pr_analysis_data(pr_url)
        print(json.dumps(pr_analysis_dict, indent=2))

        try:
            # Write PR analysis dictionary to JSON file
            with open('pr_analysis_data.json', 'w') as json_file:
                json.dump(pr_analysis_dict, json_file, indent=4)
                print('Wrote the PR Analysis data in file pr_analysis_data.json')
        except Exception as e:
            print('Failed to write PR analysis dictionary to JSON file.')
    else:
        print("PR Analysis cannot be retrieved beause it has reiceived invalid configuration.")

if __name__ == "__main__":
    main()

