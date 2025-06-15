"""This script, developed with the help of ChatGPT-4o, identifies
topics (tags) of repositories that a given GitHub user has both
starred and contributed to, across various organizations and user
accounts. It groups the repositories by their topics, only includes
topics with at least two repositories. Each topic is linked to a
GitHub search URL, focused on the organizations and user accounts of
the included repositories for that topic. For forks, topics are
gathered from both the upstream repo and the user fork.

The result are formatted in markdown or HTML. The markdown sorts the
topics by by the number of associated repositories. The HTML generates
an alphabetic word cloud, using CSS classes for the `count_N_` of each
topic and for marking each `programming-language` topic.  The topics
are also prettified by an ad-hoc mapping, or capitalization after each
hyphen by default. The ad-hoc logic is hard-coded into Python data
constants, PROGRAMMING_LANGUAGES and TOPIC_TITLES below.

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
4. Run the script: `python gen.py`

"""

import os
import requests
import requests_cache
requests_cache.install_cache('github_cache')
import urllib.parse

# Get the GitHub token from environment variables
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

# Set up headers for GitHub API requests
HEADERS = {
    'Authorization': f'token {GITHUB_TOKEN}',
    'Accept': 'application/vnd.github.mercy-preview+json'
}

username = os.environ.get('GITHUB_USER', 'namin')

generate_txt = os.environ.get('GITHUB_GEN_TXT', False)

# HTML-specific utilities
generate_html = os.environ.get('GITHUB_GEN_HTML', False)

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
for repo in starred_repos:
    owner = repo['owner']['login']
    repo_name = repo['name']
    if has_contributed_to_repo(owner, repo_name):
        repos_with_stars.append(repo)

# Step 3: Organize repositories by topic
def get_repo_for_user(user_or_org, repo_name):
    url = f'https://api.github.com/repos/{user_or_org}/{repo_name}'
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()  # The repo object
    elif response.status_code == 404:
        return None
    else:
        print(f"Error: {response.status_code}, {response.json()}")
        return None

forked_topics = set()
upstream_topics = set()
userlevel_topics = set()
def get_effective_topics(repo):
    global forked_topics
    global upstream_topics
    global userlevel_topics
    topics = repo.get('topics', [])

    if repo['owner']['login'] != username:
        upstream_topics = upstream_topics.union(set(topics))
        user_repo = get_repo_for_user(username, repo['name'])
        if user_repo:
            if not topics:
                #print(f"info: user has forked starred repo: {repo['full_name']}")
                user_topics = user_repo.get('topics', [])
                if user_topics:
                    #print(f"warning: forked topics {user_topics} for upstream repo {repo['full_name']}")
                    forked_topics = forked_topics.union(set(user_topics))
                    return user_topics
        else:
            # include as user topic if the user writes directly to upstream
            userlevel_topics = userlevel_topics.union(set(topics))
    else:
        userlevel_topics = userlevel_topics.union(set(topics))

    return topics

topic_to_repos = {}
for repo in repos_with_stars:
    topics = get_effective_topics(repo)
    for topic in topics:
        if topic not in topic_to_repos:
            topic_to_repos[topic] = []
        topic_to_repos[topic].append(repo)

# Step 4: Sort topics by repo count
if generate_html:
    sorted_key=lambda item: item[0]
else:
    sorted_key=lambda item: (-len(item[1]), item[0])
sorted_topics = sorted(topic_to_repos.items(), key=sorted_key)

def acronym(prev_topic, topic):
    a = "".join([word[0] for word in topic.split('-')])
    return a == prev_topic

def common_prefix(prev_topic, topic):
    prev = prev_topic.split('-')
    topic = topic.split('-')
    return prev[0] == topic[0]

def within_topics(topic, topics):
    return any(prev_topic in topic or acronym(prev_topic, topic) or common_prefix(prev_topic, topic) for prev_topic in prev_topics)
# Step 5: Generate formatted results (markdown or HTML) with search URLs for each topic with at least two repos
prev_topics = []
if not generate_html and not generate_txt:
    print(f"topics<sup><sub>(with count of selected projects)</sub></sup>:")
for topic, repos in sorted_topics:
    count = len(repos)
    if count == 0:
        continue
    #if count <= 1 and within_topics(topic, prev_topics):
    #    continue
    if count <= 1 and topic in upstream_topics and topic not in userlevel_topics:
        continue
    prev_topics.append(topic)
    if topic in forked_topics:
        is_forked_topic = True
        search_text = " ".join([f"repo:{repo['full_name']}" for repo in repos])
    else:
        is_forked_topic = False
        users = sorted(set([repo['owner']['login'] for repo in repos]))
        org_user_search = " ".join([f"user:{user}" for user in users])
        search_text = f"{org_user_search} topic:{topic} fork:true"
    search_encoded = urllib.parse.quote_plus(search_text)
    search_url = f"https://github.com/search?q={search_encoded}&type=repositories"
    if generate_html:
        topic_class = "programming-language " if topic.lower() in PROGRAMMING_LANGUAGES else ""
        topic_class += "forked-topic " if is_forked_topic else ""
        print(f"""<span class="count{count} {topic_class}"><a href="{search_url}">{pretty_title(topic)}</a></span>""")
    elif generate_txt:
        repo_list = ", ".join(repo['full_name'] for repo in repos)
        print(f"{topic}: {repo_list}")
    else:
        print(f"[{topic}]({search_url})<sup><sub>{count}</sub></sup>")
