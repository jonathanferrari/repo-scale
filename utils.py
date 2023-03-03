import os, json, re, requests, dotenv, base64, pandas as pd, numpy as np
import streamlit as st

def rget(*args, **kwargs):
    header = {
    "Accept": "application/vnd.github+json",
    "Authorization" : f"Bearer {st.secrets['TOKEN']}"
}
    return requests.get(headers = header, *args, **kwargs).json()

def convert_bytes(num, type = "decimal"):
    """
    Convert bytes to a more human-readable format
    """
    if type == "decimal":
        base = 1000
    elif type == "binary":
        base = 1024
    else:
        raise ValueError("type must be either 'decimal' or 'binary'")    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num) < base:
            return f"{num:.2f} {unit}"
        num /= base
    return f"{num:.2f} PB"
    
def valid_repo_url(url):
    pat = r"https?:\/\/github\.com\/[a-zA-Z0-9\-\_]+\/[a-zA-Z0-9\-\_]+\/?$" # regex pattern
    structure = bool(re.match(pat, url))
    resp = requests.get(url).status_code == 200
    return structure and resp
    
def get_repo_name(url):
    return url.split('/')[-1]

def get_repo_owner(url):
    return url.split('/')[-2]

def get_repo_path(url):
    return get_repo_owner(url) + '/' + get_repo_name(url)

def get_repo_info(url = None, owner = None, name = None):
    if not (owner and name) and not valid_repo_url(url):
        err_msgs = [f"Repo url: {url} is not valid", 
                    "Please check the url and try again", 
                    "Please ensure the repo exists and is public"]
        for msg in err_msgs: print(msg)
    else:
        if owner and name:
            return get_repo(owner = owner, name = name)
        else:
            return get_repo(path = get_repo_path(url))

def get_user_repos(user):
    repo_count = rget("https://api.github.com/users/ds-modules")['public_repos']
    repo_list, repo_set = [], set()
    page = 1
    while repo_count > 0:
        repos = rget(f"https://api.github.com/users/{user}/repos?per_page=100&page={page}")
        for repo in repos:
            if not (repo["id"] in repo_set):
                repo_set.add(repo["id"])
                repo_list.append(repo)
        repo_count -= 100
        page += 1
    return repo_list

def get_user_repo_names(user):
    return [repo['name'] for repo in get_user_repos(user)]

def get_repo(url = None, path = None, owner = None, name = None):
    if url:
        path = get_repo_path(url)
    elif name and owner:
        path = f"{owner}/{name}"
    return rget(f"https://api.github.com/repos/{path}")

def get_branch_names(path):
    branches = rget(f"https://api.github.com/repos/{path}/branches")
    branch_names = [branch['name'] for branch in branches]
    return branch_names

def get_main_sha(path):
    branch_names = get_branch_names(path)
    if 'main' in branch_names:
        main_name = 'main'
    else:
        main_name = 'master'
    return rget(f"https://api.github.com/repos/{path}/branches/{main_name}")['commit']['commit']['tree']['sha']

def get_repo_content(url = None, owner = None, name = None, recursive = True):
    if url:
        owner, name = get_repo_owner(url), get_repo_name(url)
    path = f"{owner}/{name}"
    sha = get_main_sha(path)
    if recursive:
        recursive = "recursive=1"
    else:
        recursive = ""
    contents = rget(f"https://api.github.com/repos/{path}/git/trees/{sha}?{recursive}")
    if contents['truncated']:
        print("Warning: Contents contains more than 100,000 files, truncated to 100,000 files")
    return contents['tree']

def get_repo_files(url = None, owner = None, name = None, recursive = True):
    contents = get_repo_content(url = url, owner = owner, name = name, recursive = recursive)
    return [content['path'] for content in contents if content['type'] == 'blob']

def get_repo_folders(url = None, owner = None, name = None, recursive = True):
    contents = get_repo_content(url = url, owner = owner, name = name, recursive = recursive)
    return [content['path'] for content in contents if content['type'] == 'tree']

def get_repo_size(url = None, owner = None, name = None):
    contents = get_repo_files(url = url, owner = owner, name = name, recursive = True)
    return convert_bytes(sum([content['size'] for content in contents]))

def search_user(q):
    return [user["login"] for user in rget(f"https://api.github.com/search/users?q={q}&per_page=100")["items"]]

def valid_user(user):
    return requests.get(f"https://api.github.com/users/{user}").status_code == 200

def find_user(search):
    if valid_user(search):
        return search
    return search_user(search)

def get_readme(path):
    return base64.decodebytes(rget(f"https://api.github.com/repos/{path}/readme")['content'].encode('utf-8')).decode('utf-8').replace("#", "##")

def file_type(path):
    if path[0] == ".":
        return "hidden"
    else:
        return path.split(".")[-1]
    
    
def analyze(path):
    content = get_repo_content(path)
    files, dirs = [item for item in content if item['type'] == 'blob'], [item for item in content if item['type'] == 'tree']
    files = pd.DataFrame(files)[['path', 'size']]
    dirs = pd.DataFrame(dirs)
    files["type"] = files["path"].apply(file_type)
    files = files.groupby("type").agg({"size": "sum", "path": "count"})
    total = convert_bytes((byte_sum := files["size"].sum()))
    paths = files["path"].sum()
    files["Size"] = files["size"].apply(convert_bytes)
    files = files.append(pd.DataFrame({"Size": [total], "path": [paths], "size" : byte_sum}, index = ["Total"])).rename(columns = {"size": "Bytes", "path": "Files"})
    return files[['Files', 'Size', "Bytes"]].sort_values("Bytes", ascending = False)
