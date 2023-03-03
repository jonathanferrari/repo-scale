import os, json, re, requests, dotenv

def rget(*args, **kwargs):
    header = {
    "Accept": "application/vnd.github+json",
    "Authorization" : f"Bearer {dotenv.get_key('.env', 'TOKEN')}"
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

def get_repo_size(url = None, owner = None, name = None):
    if url:
        size = get_repo_info(url)['size']
        return convert_bytes(size)
    elif owner and name:
        size = get_repo_info(owner = owner, name = name)['size']
        return convert_bytes(size)

def get_repo_content(url = None, owner = None, name = None, dir = "", recursive = False):
    if url:
        path = get_repo_path(url)
    elif name and owner:
        path = f"{owner}/{name}"
    else:
        return "Please provide a valid repo url or owner and name"
    files = rget(f"https://api.github.com/repos/{path}/contents{dir}")
    keys = ['name', 'path', 'size', 'type', 'url']
    directory = {file["path"] : {key : file[key] for key in keys} for file in files}
    if not recursive:
        return directory
    has_subdirs = lambda directory: any([file['type'] == 'dir' for file in directory.values()])
    while has_subdirs(directory):
        for file in directory.values():
            if file['type'] == 'dir':
                dir = file
                subfiles = get_repo_content(url = url, owner = owner, name = name, dir = dir['path'], recursive = True)
                for path, subfile in subfiles.items():
                    #print(subfile)
                    directory[path] = subfile
                directory.pop(dir['path'])
                break
    return directory

#last line