import os
from github import Github, GithubException

class GitHubManager:
    def __init__(self):
        self.token = None
        self.gh = None
    
    def authenticate(self, token):
        self.token = token
        self.gh = Github(token)
        self._configure_git_credentials(token)
    
    def get_repos(self):
        if not self.gh:
            raise Exception("Not authenticated!")
        return [f"{repo.owner.login}/{repo.name}" for repo in self.gh.get_user().get_repos()]
    
    def create_repository(self, repo_name, description="AutoStash Backup Repository", private=True):
        """Create a new GitHub repository"""
        if not self.gh:
            raise Exception("Not authenticated!")
        
        try:
            # Create the repository
            repo = self.gh.get_user().create_repo(
                name=repo_name,
                description=description,
                private=private,
                auto_init=True  # Initialize with README
            )
            
            # Configure the local repository
            repo_path = os.path.expanduser("~/.autostash_repo")
            if os.path.exists(repo_path):
                import shutil
                shutil.rmtree(repo_path)
            
            # Create parent directory
            os.makedirs(os.path.dirname(repo_path), exist_ok=True)
            
            # Clone the repository
            import subprocess
            result = subprocess.run(
                ["git", "clone", repo.clone_url, repo_path],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to clone repository: {result.stderr}")
            
            # Configure git user if not already configured
            subprocess.run(["git", "config", "--global", "user.name", "AutoStash"])
            subprocess.run(["git", "config", "--global", "user.email", "autostash@localhost"])
            
            return f"{repo.owner.login}/{repo.name}"
            
        except GithubException as e:
            if e.status == 422:  # Repository already exists
                raise Exception(f"Repository '{repo_name}' already exists. Please choose a different name.")
            else:
                raise Exception(f"Failed to create repository: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to set up repository: {str(e)}")
    
    def _configure_git_credentials(self, token):
        """Store GitHub token to avoid terminal prompts"""
        import subprocess
        # Store token in git credential helper
        subprocess.run(["git", "config", "--global", "credential.helper", "store"])
        # Create credentials file with token
        with open(os.path.expanduser("~/.git-credentials"), "w") as f:
            f.write(f"https://{token}:x-oauth-basic@github.com\n")
        # Secure the file
        os.chmod(os.path.expanduser("~/.git-credentials"), 0o600)

    