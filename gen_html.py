"""This script, developed with the help of ChatGPT-4o, identifies topics (tags) of repositories
that a given GitHub user has both starred and contributed to, across various organizations 
and user accounts. It groups the repositories by their topics, sorts the topics by the number 
of associated repositories, and only includes topics with at least two repositories. Each topic 
is linked to a GitHub search URL, focused on the organizations and user accounts of the included 
repositories for that topic.

Compared to `gen.py`, this variant generates HTML, to create a word cloud, using CSS classes for
the `count_N_` of each topic and for marking each `programming-language` topic.
The topics are also prettified by an ad-hoc mapping, or capitalization after each hyphen by default.

How to run:
1. Ensure that you have Python installed:
   - `conda create -n requests python=3.10`
   - `conda activate requests`
2. Install the `requests` and `requests-cache` libraries if you don't have them:
   - `pip install requests`
   - `pip install request`
3. Set the following environment variables:
   - `GITHUB_TOKEN`: Your GitHub personal access token with the necessary permissions (e.g., `public_repo` scope).
   - `GITHUB_USER`: The GitHub username for which you want to fetch starred and contributed repositories.
4. Run the script: `python gen_html.py`

"""

# Predefined list of programming languages
PROGRAMMING_LANGUAGES = {
    'minikanren', 'racket', 'common-lisp', 'coq', 'dafny',
    'python', 'java', 'javascript', 'typescript', 'ruby', 'go', 'rust', 'scala',
    'haskell', 'perl', 'php', 'c', 'c++', 'c#', 'r', 'swift', 'kotlin',
    'objective-c', 'shell', 'bash', 'lua', 'dart', 'elixir', 'clojure', 'erlang',
    'fsharp', 'fortran', 'scheme', 'lisp', 'ocaml', 'prolog', 'matlab', 'julia'
}

# Predefined list of ad-hoc topic titles
TOPIC_TITLES = {
    'ai': 'AI',
    'llm': 'LLMs',
    'minikanren' : 'miniKanren',
    'multi-stage-programming': 'Staging',
    'ncats-translator': 'NCATS',
    'oop': 'OOP',
}    

def capitalize(text):
    # capitalize first letter, and after each hyphen
    words = text.split('-')
    capitalized_words = ['-'.join([word.capitalize() for word in words])]
    return ''.join(capitalized_words)

def pretty_title(topic):
    return TOPIC_TITLES.get(topic, capitalize(topic))

import os
import requests
import requests_cache
requests_cache.install_cache('github_cache')

# Get the GitHub token from environment variables
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

# Set up headers for GitHub API requests
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.mercy-preview+json'
}

username = os.environ.get('GITHUB_USER', 'namin')

# Function to check if the user has contributed to the repository
def has_contributed_to_repo(owner, repo):
    contributors_url = f'https://api.github.com/repos/{owner}/{repo}/contributors'
    response = requests.get(contributors_url, headers=HEADERS)
    if response.status_code == 200:
        contributors = response.json()
        for contributor in contributors:
            if contributor['login'] == username:
                return True
    return False

# Step 1: Get ALL starred repositories (handle pagination)
def get_all_starred_repos():
    all_starred_repos = []
    starred_repos_url = f'https://api.github.com/users/{username}/starred'
    
    while starred_repos_url:
        response = requests.get(starred_repos_url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.json()}")
            break
        
        all_starred_repos.extend(response.json())
        
        # Check if there's a next page
        starred_repos_url = response.links.get('next', {}).get('url')
    
    return all_starred_repos

starred_repos = get_all_starred_repos()

# Step 2: Filter repositories where the user has contributed
repos_with_stars = []
repos_with_topics = []
for repo in starred_repos:
    owner = repo['owner']['login']
    repo_name = repo['name']
    if has_contributed_to_repo(owner, repo_name):
        repos_with_stars.append(repo)
        if 'topics' in repo and repo['topics']:
            repos_with_topics.append(repo)

# Step 3: Organize repositories by topic
topic_to_repos = {}
for repo in repos_with_topics:
    topics = repo.get('topics', [])
    for topic in topics:
        if topic not in topic_to_repos:
            topic_to_repos[topic] = []
        topic_to_repos[topic].append(repo)

# Step 4: Sort topics by topic
sorted_topics = sorted(topic_to_repos.items(), key=lambda item: item[0])

# Step 5: Generate HTML cloud with search URLs for each topic with at least two repos
for topic, repos in sorted_topics:
    if len(repos) <= 1:
        continue
    users = set([repo['owner']['login'] for repo in repos])
    org_user_search = "+".join([f"user%3A{user}" for user in users])
    search_url = f"https://github.com/search?q={org_user_search}+fork%3Atrue+topic%3A{topic}"
    count = len(repos)
    topic_class = "programming-language" if topic.lower() in PROGRAMMING_LANGUAGES else ""
    print(f"""<span class="count{count} {topic_class}"><a href="{search_url}">{pretty_title(topic)}</a></span>""")
