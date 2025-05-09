import os
import shutil
import requests
import hashlib
import logging
import datetime
import subprocess
import gnupg
import tarfile
import json
from git import Repo, GitCommandError

class BackupManager:
    def __init__(self):
        self.repo_path = os.path.expanduser("~/.autostash_repo")
        self.repo = None
        self.log_path = "/var/log/autostash"
        self.gpg = gnupg.GPG()
        self.incremental = True  # Default to incremental backup
        self._setup_logging()

    def _setup_logging(self):
        """Set up logging to /var/log/autostash"""
        try:
            if not os.path.exists(self.log_path):
                try:
                    os.makedirs(self.log_path, exist_ok=True)
                except PermissionError:
                    subprocess.run(["sudo", "mkdir", "-p", self.log_path])
                    subprocess.run(["sudo", "chown", f"{os.getenv('USER')}:", self.log_path])
            self.logger = logging.getLogger('autostash')
            self.logger.setLevel(logging.INFO)
            handler = logging.FileHandler(os.path.join(self.log_path, "backup.log"))
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        except Exception as e:
            os.makedirs(os.path.expanduser("~/.autostash/logs"), exist_ok=True)
            self.logger = logging.getLogger('autostash')
            self.logger.setLevel(logging.INFO)
            handler = logging.FileHandler(os.path.expanduser("~/.autostash/logs/backup.log"))
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            print(f"Using fallback log location due to: {str(e)}")

    def run(self, folders, repo_name, backup_system=False, encrypt=False, compress=False, incremental=True, progress_callback=None):
        """Run a backup operation with enhanced error handling and validation"""
        try:
            # Validate inputs
            if not folders:
                raise ValueError("No folders specified for backup")
            if not repo_name:
                raise ValueError("No repository specified for backup")
            
            # Validate folder paths
            for folder in folders:
                if not os.path.exists(folder):
                    raise ValueError(f"Folder does not exist: {folder}")
                if not os.access(folder, os.R_OK):
                    raise ValueError(f"No read permission for folder: {folder}")
            
            self.incremental = incremental
            self.logger.info(f"Starting backup to {repo_name}")
            steps = len(folders)
            if backup_system:
                steps += 1
            completed = 0

            # Verify repository access
            if not self._repo_exists(repo_name):
                raise Exception(f"Repository {repo_name} doesn't exist or no access")

            # Prepare repository with error handling
            try:
                self._prepare_repo(repo_name)
            except Exception as e:
                raise Exception(f"Failed to prepare repository: {str(e)}")

            # Create backup timestamp and folder name
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            # Create a descriptive name for the backup
            folder_names = [os.path.basename(f) for f in folders]
            backup_name = "_".join(folder_names[:3])  # Use up to 3 folder names
            if len(folder_names) > 3:
                backup_name += "_etc"
            backup_folder_name = f"Backup_{timestamp}_{backup_name}"
            backup_folder_path = os.path.join(self.repo_path, backup_folder_name)
            
            try:
                os.makedirs(backup_folder_path, exist_ok=True)
            except Exception as e:
                raise Exception(f"Failed to create backup directory: {str(e)}")
            
            # Create backup metadata
            backup_metadata = {
                'timestamp': timestamp,
                'backup_name': backup_folder_name,
                'folders': {},
                'options': {
                    'backup_system': backup_system,
                    'encrypt': encrypt,
                    'compress': compress,
                    'incremental': incremental
                }
            }

            # Initialize counters
            total_size = 0
            file_count = 0
            changed_files = 0

            # Backup each folder with error handling
            for folder in folders:
                if progress_callback:
                    progress_callback(completed / steps * 100, f"Backing up {os.path.basename(folder)}...")
                
                try:
                    # Create a subfolder for each source folder
                    source_folder_name = os.path.basename(folder)
                    source_backup_path = os.path.join(backup_folder_path, source_folder_name)
                    os.makedirs(source_backup_path, exist_ok=True)
                    
                    # Store original path in metadata
                    backup_metadata['folders'][source_folder_name] = folder
                    
                    # Handle incremental backup
                    if incremental:
                        self._incremental_backup(folder, source_backup_path)
                    else:
                        self._full_backup(folder, source_backup_path)
                    
                    # Count files and calculate size
                    for root, dirs, files in os.walk(source_backup_path):
                        for file in files:
                            # Skip temporary and metadata files
                            if file.endswith(('.tmp', 'metadata.json')):
                                continue
                            
                            try:
                                file_path = os.path.join(root, file)
                                file_size = os.path.getsize(file_path)
                                total_size += file_size
                                file_count += 1
                                # Check if file was modified in the last hour
                                if (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(file_path))).total_seconds() < 3600:
                                    changed_files += 1
                            except (OSError, FileNotFoundError) as e:
                                self.logger.warning(f"Could not access file {file_path}: {str(e)}")
                                continue
                    
                    completed += 1
                except Exception as e:
                    raise Exception(f"Failed to backup folder {folder}: {str(e)}")

            # Backup system files if requested
            if backup_system:
                if progress_callback:
                    progress_callback(completed / steps * 100, "Backing up system files...")
                try:
                    system_backup_path = os.path.join(backup_folder_path, "system_config")
                    os.makedirs(system_backup_path, exist_ok=True)
                    self._backup_system_files(system_backup_path)
                    backup_metadata['folders']['system_config'] = '/etc'
                    
                    # Count system files
                    for root, dirs, files in os.walk(system_backup_path):
                        for file in files:
                            # Skip temporary and metadata files
                            if file.endswith(('.tmp', 'metadata.json')):
                                continue
                            
                            try:
                                file_path = os.path.join(root, file)
                                file_size = os.path.getsize(file_path)
                                total_size += file_size
                                file_count += 1
                                if (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(file_path))).total_seconds() < 3600:
                                    changed_files += 1
                            except (OSError, FileNotFoundError) as e:
                                self.logger.warning(f"Could not access file {file_path}: {str(e)}")
                                continue
                    
                    completed += 1
                except Exception as e:
                    raise Exception(f"Failed to backup system files: {str(e)}")

            # Format size to human-readable format
            def format_size(size):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024:
                        return f"{size:.1f} {unit}"
                    size /= 1024
                return f"{size:.1f} TB"

            # Update metadata with file counts
            backup_metadata['total_files'] = file_count
            backup_metadata['changed_files'] = changed_files
            backup_metadata['total_size'] = format_size(total_size)
            backup_metadata['type'] = 'Full' if not incremental else 'Incremental'

            # Save metadata with error handling
            try:
                metadata_path = os.path.join(backup_folder_path, "metadata.json")
                with open(metadata_path, 'w') as f:
                    json.dump(backup_metadata, f, indent=4)
                
                # Verify metadata was saved correctly
                if not os.path.exists(metadata_path):
                    raise Exception("Failed to save metadata file")
                
                # Verify metadata can be read back
                with open(metadata_path, 'r') as f:
                    saved_metadata = json.load(f)
                    if not all(key in saved_metadata for key in ['timestamp', 'backup_name', 'folders', 'total_files', 'total_size']):
                        raise Exception("Metadata file is incomplete")
                
                self.logger.info("Backup metadata saved successfully")
            except Exception as e:
                raise Exception(f"Failed to save backup metadata: {str(e)}")

            # Handle compression and encryption
            if compress or encrypt:
                if progress_callback:
                    progress_callback(95, "Processing backup files...")
                try:
                    self._process_backup_files(backup_folder_path, compress, encrypt)
                except Exception as e:
                    raise Exception(f"Failed to process backup files: {str(e)}")

            # Count files after encryption/compression
            total_size = 0
            file_count = 0
            changed_files = 0

            # Count files in each source folder
            for folder_name, original_path in backup_metadata['folders'].items():
                folder_path = os.path.join(backup_folder_path, folder_name)
                if os.path.exists(folder_path):
                    # Handle compressed/encrypted files
                    if os.path.exists(os.path.join(folder_path, "backup.tar.gz")):
                        tar_path = os.path.join(folder_path, "backup.tar.gz")
                        file_count += 1
                        total_size += os.path.getsize(tar_path)
                        if (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(tar_path))).total_seconds() < 3600:
                            changed_files += 1
                    elif os.path.exists(os.path.join(folder_path, "backup.tar.gz.gpg")):
                        tar_path = os.path.join(folder_path, "backup.tar.gz.gpg")
                        file_count += 1
                        total_size += os.path.getsize(tar_path)
                        if (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(tar_path))).total_seconds() < 3600:
                            changed_files += 1
                    else:
                        # Count individual files
                        for root, dirs, files in os.walk(folder_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # Skip metadata and temporary files, but include .gpg files
                                if not file.endswith(('.tmp', 'metadata.json')):
                                    try:
                                        file_size = os.path.getsize(file_path)
                                        total_size += file_size
                                        file_count += 1
                                        if (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(file_path))).total_seconds() < 3600:
                                            changed_files += 1
                                    except (OSError, FileNotFoundError) as e:
                                        self.logger.warning(f"Could not access file {file_path}: {str(e)}")
                                        continue

            # Update metadata with file counts
            backup_metadata['total_files'] = file_count
            backup_metadata['changed_files'] = changed_files
            backup_metadata['total_size'] = format_size(total_size)
            backup_metadata['type'] = 'Full' if not incremental else 'Incremental'

            # Save metadata with error handling
            try:
                metadata_path = os.path.join(backup_folder_path, "metadata.json")
                with open(metadata_path, 'w') as f:
                    json.dump(backup_metadata, f, indent=4)
                
                # Verify metadata was saved correctly
                if not os.path.exists(metadata_path):
                    raise Exception("Failed to save metadata file")
                
                # Verify metadata can be read back
                with open(metadata_path, 'r') as f:
                    saved_metadata = json.load(f)
                    if not all(key in saved_metadata for key in ['timestamp', 'backup_name', 'folders', 'total_files', 'total_size']):
                        raise Exception("Metadata file is incomplete")
                
                self.logger.info("Backup metadata saved successfully")
            except Exception as e:
                raise Exception(f"Failed to save backup metadata: {str(e)}")

            # Commit and push changes
            try:
                self._git_commit_push()
            except Exception as e:
                raise Exception(f"Failed to commit and push changes: {str(e)}")

            # Record backup time and update history
            try:
                self._record_backup_time()
                self._append_backup_history(backup_metadata)
            except Exception as e:
                self.logger.error(f"Failed to update backup history: {str(e)}")
                # Don't raise here as the backup itself was successful
            
            if progress_callback:
                progress_callback(100, "Backup complete")

            return {
                'status': 'success',
                'backup_name': backup_folder_name,
                'timestamp': timestamp,
                'folders': backup_metadata['folders'],
                'total_files': file_count,
                'total_size': format_size(total_size)
            }

        except Exception as e:
            self.logger.error(f"Backup failed: {str(e)}")
            # Clean up failed backup directory if it exists
            if 'backup_folder_path' in locals() and os.path.exists(backup_folder_path):
                try:
                    shutil.rmtree(backup_folder_path)
                except:
                    pass
            raise

    def _incremental_backup(self, src_folder, dest_dir):
        """Perform incremental backup using rsync"""
        try:
            if not os.path.exists(src_folder):
                raise Exception(f"Source folder does not exist: {src_folder}")
                
            dest = os.path.join(dest_dir, os.path.basename(src_folder))
            os.makedirs(dest, exist_ok=True)
            
            # Use rsync for efficient incremental backup
            rsync_cmd = [
                "rsync",
                "-a",  # Archive mode
                "--delete",  # Delete files in dest that don't exist in src
                "--exclude", ".git",  # Exclude .git directories
                src_folder + "/",
                dest + "/"
            ]
            
            result = subprocess.run(rsync_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"rsync failed: {result.stderr}")
            
            # Verify files were copied
            if not os.path.exists(dest) or len(os.listdir(dest)) == 0:
                raise Exception(f"No files were copied to {dest}")
                
            self.logger.info(f"Incremental backup completed for {src_folder}")
            
        except Exception as e:
            raise Exception(f"Incremental backup failed for {src_folder}: {str(e)}")

    def _full_backup(self, src_folder, dest_dir):
        """Perform full backup"""
        try:
            if not os.path.exists(src_folder):
                raise Exception(f"Source folder does not exist: {src_folder}")
                
            dest = os.path.join(dest_dir, os.path.basename(src_folder))
            if os.path.exists(dest):
                shutil.rmtree(dest)
                
            # Copy the directory tree
            shutil.copytree(src_folder, dest, dirs_exist_ok=True)
            
            # Verify files were copied
            if not os.path.exists(dest) or len(os.listdir(dest)) == 0:
                raise Exception(f"No files were copied to {dest}")
                
            self.logger.info(f"Full backup completed for {src_folder}")
        except Exception as e:
            raise Exception(f"Full backup failed for {src_folder}: {str(e)}")

    def _backup_system_files(self, dest_dir):
        """Backup system files with enhanced coverage"""
        system_backup_path = os.path.join(dest_dir, "system_config")
        os.makedirs(system_backup_path, exist_ok=True)
        
        # Extended list of critical system files
        critical_files = [
            "/etc/fstab",
            "/etc/hosts",
            "/etc/passwd",
            "/etc/group",
            "/etc/shadow",
            "/etc/gshadow",
            "/etc/sudoers",
            "/etc/resolv.conf",
            "/etc/hostname",
            "/etc/network/interfaces",
            "/etc/apt/sources.list",
            "/etc/ssh/sshd_config",
            "/etc/ssh/ssh_config",
            "/etc/ssl/certs/ca-certificates.crt",
            "/etc/environment",
            "/etc/profile",
            "/etc/bash.bashrc"
        ]
        
        for file_path in critical_files:
            if os.path.exists(file_path):
                try:
                    dest_dir = os.path.join(system_backup_path, os.path.dirname(file_path)[1:])
                    os.makedirs(dest_dir, exist_ok=True)
                    shutil.copy2(file_path, os.path.join(dest_dir, os.path.basename(file_path)))
                    self.logger.info(f"Backed up: {file_path}")
                except PermissionError:
                    self.logger.warning(f"Permission denied for: {file_path}")
                except Exception as e:
                    self.logger.error(f"Failed to backup {file_path}: {str(e)}")

    def _process_backup_files(self, temp_dir, compress, encrypt):
        """Process backup files with compression and/or encryption"""
        try:
            # Preserve metadata file
            metadata_path = os.path.join(temp_dir, "metadata.json")
            if os.path.exists(metadata_path):
                # Create a temporary copy of metadata
                temp_metadata = os.path.join(temp_dir, "metadata.json.tmp")
                shutil.copy2(metadata_path, temp_metadata)

            # Process each folder separately
            for folder_name in os.listdir(temp_dir):
                folder_path = os.path.join(temp_dir, folder_name)
                if not os.path.isdir(folder_path) or folder_name == ".git":
                    continue

                # Create a tar archive if compression is enabled
                if compress:
                    tar_path = os.path.join(folder_path, "backup.tar.gz")
                    with tarfile.open(tar_path, "w:gz") as tar:
                        # Add all files except metadata
                        for item in os.listdir(folder_path):
                            if item != "metadata.json" and item != "metadata.json.tmp":
                                path = os.path.join(folder_path, item)
                                if os.path.isfile(path):
                                    tar.add(path, arcname=os.path.basename(path))
                                elif os.path.isdir(path):
                                    tar.add(path, arcname=os.path.basename(path))
                    
                    # Remove original files after compression (except metadata)
                    for item in os.listdir(folder_path):
                        if item not in ["backup.tar.gz", "metadata.json", "metadata.json.tmp"]:
                            path = os.path.join(folder_path, item)
                            if os.path.isfile(path):
                                os.remove(path)
                            elif os.path.isdir(path):
                                shutil.rmtree(path)

                # Encrypt the backup if requested
                if encrypt:
                    # Get the GPG key
                    keys = self.gpg.list_keys()
                    if not keys:
                        raise Exception("No GPG keys found. Please create a key first.")
                    
                    # Use the first available key
                    key = keys[0]['fingerprint']
                    
                    # Encrypt the backup
                    if compress:
                        with open(tar_path, 'rb') as f:
                            encrypted_data = self.gpg.encrypt_file(
                                f,
                                recipients=[key],
                                output=tar_path + ".gpg"
                            )
                        os.remove(tar_path)  # Remove the unencrypted tar
                    else:
                        # Encrypt each file individually (except metadata)
                        for root, dirs, files in os.walk(folder_path):
                            for file in files:
                                if file not in ["metadata.json", "metadata.json.tmp"]:
                                    file_path = os.path.join(root, file)
                                    with open(file_path, 'rb') as f:
                                        encrypted_data = self.gpg.encrypt_file(
                                            f,
                                            recipients=[key],
                                            output=file_path + ".gpg"
                                        )
                                    os.remove(file_path)  # Remove the unencrypted file

            # Restore metadata file
            if os.path.exists(temp_metadata):
                shutil.move(temp_metadata, metadata_path)

            self.logger.info("Backup processing completed successfully")
            
        except Exception as e:
            # Restore metadata file in case of error
            if os.path.exists(temp_metadata):
                shutil.move(temp_metadata, metadata_path)
            raise Exception(f"Failed to process backup files: {str(e)}")

    def _repo_exists(self, repo_name):
        """Check if repository exists and is accessible"""
        try:
            url = f"https://github.com/{repo_name}"
            response = requests.get(url)
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                raise Exception(f"Repository {repo_name} not found")
            else:
                raise Exception(f"Failed to access repository {repo_name}: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to check repository: {str(e)}")

    def _prepare_repo(self, repo_name):
        """Prepare the repository for backup"""
        try:
            # Validate repository name format
            if not repo_name or '/' not in repo_name:
                raise ValueError("Invalid repository name format. Expected format: 'username/repository'")
            
            # Clean up any existing repository
            if os.path.exists(self.repo_path):
                try:
                    shutil.rmtree(self.repo_path)
                except Exception as e:
                    self.logger.error(f"Failed to clean up existing repository: {str(e)}")
                    raise Exception("Failed to clean up existing repository. Please check permissions.")
            
            # Create parent directory if it doesn't exist
            try:
                os.makedirs(os.path.dirname(self.repo_path), exist_ok=True)
            except Exception as e:
                self.logger.error(f"Failed to create repository directory: {str(e)}")
                raise Exception("Failed to create repository directory. Please check permissions.")
            
            # Clone the repository with error handling
            repo_url = f"https://github.com/{repo_name}.git"
            try:
                self.repo = Repo.clone_from(repo_url, self.repo_path)
                self.logger.info(f"Cloned repository: {repo_name}")
            except GitCommandError as e:
                self.logger.error(f"Failed to clone repository: {str(e)}")
                if "Authentication failed" in str(e):
                    raise Exception("GitHub authentication failed. Please check your credentials.")
                elif "Repository not found" in str(e):
                    raise Exception(f"Repository {repo_name} not found. Please check the repository name.")
                else:
                    raise Exception(f"Failed to clone repository: {str(e)}")
            
            # Ensure temp_backup directory exists and is clean
            temp_dir = os.path.join(self.repo_path, "temp_backup")
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                os.makedirs(temp_dir, exist_ok=True)
                self.logger.info("Prepared temp_backup directory")
            except Exception as e:
                self.logger.error(f"Failed to prepare temp_backup directory: {str(e)}")
                raise Exception("Failed to prepare backup directory. Please check permissions.")
            
            # Initialize backup history file if it doesn't exist
            history_path = os.path.join(self.repo_path, "backup_history")
            if not os.path.exists(history_path):
                try:
                    with open(history_path, "w") as f:
                        f.write("")  # Create empty history file
                    self.repo.git.add(history_path)
                    self.repo.git.commit(m="Initialize backup history")
                    self.repo.git.push()
                except Exception as e:
                    self.logger.error(f"Failed to initialize backup history: {str(e)}")
                    raise Exception("Failed to initialize backup history file.")
            
        except Exception as e:
            self.logger.error(f"Failed to prepare repository: {str(e)}")
            raise

    def _git_commit_push(self):
        """Commit and push changes to the repository"""
        try:
            if self.repo.is_dirty() or len(self.repo.untracked_files) > 0:
                self.repo.git.add(A=True)
                self.repo.git.commit(m="AutoStash Backup")
                try:
                    self.repo.remotes.origin.push()
                except GitCommandError as e:
                    # If push fails, try to pull first
                    self.repo.remotes.origin.pull()
                    self.repo.remotes.origin.push()
        except GitCommandError as e:
            raise Exception(f"Git error: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to commit and push changes: {str(e)}")

    def _record_backup_time(self):
        """Record the time of successful backup"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(os.path.expanduser("~/.autostash/last_backup"), "w") as f:
            f.write(timestamp)

    def _append_backup_history(self, metadata):
        """Append backup time and details to history file and sync with repository"""
        try:
            # Ensure .autostash directory exists
            autostash_dir = os.path.expanduser("~/.autostash")
            os.makedirs(autostash_dir, exist_ok=True)
            
            timestamp = metadata['timestamp']
            
            # Calculate backup size and count files
            total_size = 0
            file_count = 0
            changed_files = 0
            
            # Get the backup folder path
            backup_folder_path = os.path.join(self.repo_path, metadata['backup_name'])
            
            # Count files in each source folder
            for folder_name, original_path in metadata['folders'].items():
                folder_path = os.path.join(backup_folder_path, folder_name)
                if os.path.exists(folder_path):
                    # Handle compressed/encrypted files
                    if os.path.exists(os.path.join(folder_path, "backup.tar.gz.gpg")):
                        # Handle encrypted compressed file
                        tar_path = os.path.join(folder_path, "backup.tar.gz.gpg")
                        file_count += 1
                        total_size += os.path.getsize(tar_path)
                        if (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(tar_path))).total_seconds() < 3600:
                            changed_files += 1
                    elif os.path.exists(os.path.join(folder_path, "backup.tar.gz")):
                        # Handle compressed file
                        tar_path = os.path.join(folder_path, "backup.tar.gz")
                        file_count += 1
                        total_size += os.path.getsize(tar_path)
                        if (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(tar_path))).total_seconds() < 3600:
                            changed_files += 1
                    else:
                        # Count individual files
                        for root, dirs, files in os.walk(folder_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # Skip metadata and temporary files, but include .gpg files
                                if not file.endswith(('.tmp', 'metadata.json')):
                                    try:
                                        file_size = os.path.getsize(file_path)
                                        total_size += file_size
                                        file_count += 1
                                        # Check if file was modified in the last hour
                                        if (datetime.datetime.now() - datetime.datetime.fromtimestamp(os.path.getmtime(file_path))).total_seconds() < 3600:
                                            changed_files += 1
                                    except (OSError, FileNotFoundError) as e:
                                        self.logger.warning(f"Could not access file {file_path}: {str(e)}")
                                        continue

            # Format size to human-readable format
            def format_size(size):
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if size < 1024:
                        return f"{size:.1f} {unit}"
                    size /= 1024
                return f"{size:.1f} TB"

            # Create detailed backup entry
            backup_entry = {
                'timestamp': timestamp,
                'total_files': file_count,
                'changed_files': changed_files,
                'total_size': format_size(total_size),
                'type': 'Full' if not self.incremental else 'Incremental',
                'folders': metadata['folders'],
                'backup_name': metadata['backup_name'],
                'compressed': metadata['options'].get('compress', False),
                'encrypted': metadata['options'].get('encrypt', False)
            }
            
            # Save to local history file
            history_path = os.path.join(autostash_dir, "backup_history")
            with open(history_path, "a") as f:
                f.write(json.dumps(backup_entry) + "\n")
            
            # Save to repository history file
            repo_history_path = os.path.join(self.repo_path, "backup_history")
            with open(repo_history_path, "a") as f:
                f.write(json.dumps(backup_entry) + "\n")
            
            # Add and commit the history file to repository
            self.repo.git.add(repo_history_path)
            self.repo.git.commit(m=f"Update backup history: {timestamp}")
            self.repo.git.push()
                
            self.logger.info(f"Backup history updated: {file_count} files, {format_size(total_size)}")
            
        except Exception as e:
            self.logger.error(f"Failed to update backup history: {str(e)}")
            raise

    def sync_backup_history(self):
        """Sync backup history with the repository"""
        try:
            repo_history_path = os.path.join(self.repo_path, "backup_history")
            local_history_path = os.path.expanduser("~/.autostash/backup_history")
            
            # If repository history exists, use it
            if os.path.exists(repo_history_path):
                # Read repository history
                with open(repo_history_path, "r") as f:
                    repo_entries = [line.strip() for line in f if line.strip()]
                
                # Read local history if it exists
                local_entries = []
                if os.path.exists(local_history_path):
                    with open(local_history_path, "r") as f:
                        local_entries = [line.strip() for line in f if line.strip()]
                
                # Merge entries, preferring repository entries
                merged_entries = []
                seen_timestamps = set()
                
                # Add repository entries first
                for entry in repo_entries:
                    try:
                        data = json.loads(entry)
                        timestamp = data.get('timestamp')
                        if timestamp and timestamp not in seen_timestamps:
                            merged_entries.append(entry)
                            seen_timestamps.add(timestamp)
                    except json.JSONDecodeError:
                        continue
                
                # Add local entries that aren't in repository
                for entry in local_entries:
                    try:
                        data = json.loads(entry)
                        timestamp = data.get('timestamp')
                        if timestamp and timestamp not in seen_timestamps:
                            merged_entries.append(entry)
                            seen_timestamps.add(timestamp)
                    except json.JSONDecodeError:
                        continue
                
                # Sort entries by timestamp
                merged_entries.sort(key=lambda x: json.loads(x)['timestamp'], reverse=True)
                
                # Check if there are any changes to commit
                current_repo_content = ""
                if os.path.exists(repo_history_path):
                    with open(repo_history_path, "r") as f:
                        current_repo_content = f.read()
                
                new_content = "\n".join(merged_entries) + "\n"
                
                # Only write and commit if there are changes
                if current_repo_content != new_content:
                    # Write merged history to both locations
                    with open(repo_history_path, "w") as f:
                        f.write(new_content)
                    
                    with open(local_history_path, "w") as f:
                        f.write(new_content)
                    
                    # Commit changes to repository
                    self.repo.git.add(repo_history_path)
                    self.repo.git.commit(m="Sync backup history")
                    self.repo.git.push()
                    
                    self.logger.info(f"Backup history synced: {len(merged_entries)} entries")
                else:
                    self.logger.info("No changes to sync in backup history")
                
                return len(merged_entries)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Failed to sync backup history: {str(e)}")
            raise

    def verify_and_repair_history(self):
        """Verify and repair the backup history file if needed"""
        try:
            # First sync with repository
            self.sync_backup_history()
            
            history_path = os.path.expanduser("~/.autostash/backup_history")
            if not os.path.exists(history_path):
                self.logger.info("No backup history file found, creating new one")
                return
                
            # Read and verify each line
            valid_entries = []
            with open(history_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        # Try to parse the JSON
                        entry = json.loads(line)
                        # Verify required fields
                        required_fields = ['timestamp', 'total_files', 'total_size', 'type', 'folders', 'backup_name']
                        if all(field in entry for field in required_fields):
                            valid_entries.append(line)
                        else:
                            self.logger.warning(f"Invalid backup entry found, missing required fields: {entry}")
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON found in history file: {line}")
                        continue
            
            # If we found invalid entries, rewrite the file
            if len(valid_entries) < len(open(history_path).readlines()):
                self.logger.info(f"Repairing backup history file. Found {len(valid_entries)} valid entries")
                with open(history_path, "w") as f:
                    for entry in valid_entries:
                        f.write(entry + "\n")
                
                # Also update repository history
                repo_history_path = os.path.join(self.repo_path, "backup_history")
                with open(repo_history_path, "w") as f:
                    for entry in valid_entries:
                        f.write(entry + "\n")
                
                # Commit changes to repository
                self.repo.git.add(repo_history_path)
                self.repo.git.commit(m="Repair backup history")
                self.repo.git.push()
                
                self.logger.info("Backup history file repaired successfully")
            
            return len(valid_entries)
            
        except Exception as e:
            self.logger.error(f"Failed to verify/repair backup history: {str(e)}")
            raise

    def get_last_backup_time(self):
        try:
            with open(os.path.expanduser("~/.autostash/last_backup"), "r") as f:
                return f.read().strip()
        except Exception:
            return None

    def restore(self, repo, backup_folder=None, password_callback=None):
        """Restore files from a backup with enhanced error handling and validation"""
        try:
            # Validate repository name
            if not repo:
                raise ValueError("No repository specified for restore")
            
            # Initialize repository path
            repo_name = repo.split('/')[-1]  # Get just the repository name
            repo_path = os.path.join(self.repo_path, repo_name)
            
            # Ensure repository exists
            if not os.path.exists(repo_path):
                self.logger.info(f"Repository not found locally, cloning {repo}")
                try:
                    repo_url = f"https://github.com/{repo}.git"
                    self.repo = Repo.clone_from(repo_url, repo_path)
                except Exception as e:
                    raise Exception(f"Failed to clone repository {repo}: {str(e)}")
            else:
                # Update existing repository
                try:
                    self.repo = Repo(repo_path)
                    self.repo.remotes.origin.pull()
                except Exception as e:
                    raise Exception(f"Failed to update repository: {str(e)}")

            # Find the backup folder
            if not backup_folder:
                # Find the latest backup folder
                backup_folders = [f for f in os.listdir(repo_path) 
                                if f.startswith("Backup_") and os.path.isdir(os.path.join(repo_path, f))]
                if not backup_folders:
                    raise Exception("No backup folders found")
                backup_folder = sorted(backup_folders)[-1]  # Get the latest backup

            # Ensure backup folder exists
            backup_path = os.path.join(repo_path, backup_folder)
            if not os.path.exists(backup_path):
                raise Exception(f"Backup folder {backup_folder} not found")

            # Load and validate metadata
            metadata_path = os.path.join(backup_path, "metadata.json")
            if not os.path.exists(metadata_path):
                raise Exception("Backup metadata not found")

            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            except json.JSONDecodeError:
                raise Exception("Invalid backup metadata format")

            # Validate metadata
            required_fields = ['timestamp', 'folders', 'backup_name']
            if not all(field in metadata for field in required_fields):
                raise Exception("Backup metadata is incomplete")

            # Get original paths from metadata
            original_paths = metadata.get('folders', {})
            if not original_paths:
                raise Exception("No original paths found in metadata")

            files_restored = 0
            total_size = 0
            first_restored_path = None
            failed_files = []

            # Function to handle sudo commands with GUI password prompt
            def run_sudo_command(cmd):
                if password_callback:
                    # Get password from GUI
                    password = password_callback()
                    if not password:
                        raise Exception("Password required for restore operation")
                    
                    # Create a temporary file to store the password
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                        f.write(f"{password}\n")
                        pass_file = f.name
                    
                    try:
                        # Use the password file with sudo
                        result = subprocess.run(
                            ['sudo', '-S'] + cmd,
                            input=f"{password}\n",
                            text=True,
                            capture_output=True
                        )
                        if result.returncode != 0:
                            raise Exception(f"Sudo command failed: {result.stderr}")
                        return result
                    finally:
                        # Clean up the temporary password file
                        os.unlink(pass_file)
                else:
                    # Fallback to regular sudo if no callback provided
                    return subprocess.run(['sudo'] + cmd, check=True)

            # Restore each folder
            for folder_name, original_path in original_paths.items():
                source_folder = os.path.join(backup_path, folder_name)
                if not os.path.exists(source_folder):
                    self.logger.warning(f"Source folder {source_folder} not found, skipping...")
                    continue

                try:
                    # Check if this is a system path that needs sudo
                    needs_sudo = original_path.startswith('/etc/') or original_path == '/etc'
                    
                    # Create destination directory if it doesn't exist
                    if needs_sudo:
                        run_sudo_command(['mkdir', '-p', original_path])
                    else:
                        os.makedirs(original_path, exist_ok=True)
                    
                    if first_restored_path is None:
                        first_restored_path = original_path

                    # Check for compressed backup
                    compressed_file = os.path.join(source_folder, "backup.tar.gz")
                    encrypted_compressed_file = os.path.join(source_folder, "backup.tar.gz.gpg")
                    
                    if os.path.exists(encrypted_compressed_file):
                        # Handle encrypted compressed backup
                        temp_file = os.path.join('/tmp', 'temp_backup.tar.gz')
                        try:
                            # Decrypt the file
                            with open(encrypted_compressed_file, 'rb') as f:
                                decrypted_data = self.gpg.decrypt_file(f)
                            with open(temp_file, 'wb') as f:
                                f.write(decrypted_data.data)
                            
                            # Extract the decrypted archive
                            if needs_sudo:
                                run_sudo_command(['tar', '-xzf', temp_file, '-C', original_path])
                            else:
                                with tarfile.open(temp_file, 'r:gz') as tar:
                                    tar.extractall(path=original_path)
                            
                            # Count files in the archive
                            with tarfile.open(temp_file, 'r:gz') as tar:
                                files_restored += len(tar.getmembers())
                                total_size += os.path.getsize(encrypted_compressed_file)
                            
                            self.logger.info(f"Restored encrypted compressed backup to {original_path}")
                        finally:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                                
                    elif os.path.exists(compressed_file):
                        # Handle compressed backup
                        if needs_sudo:
                            run_sudo_command(['tar', '-xzf', compressed_file, '-C', original_path])
                        else:
                            with tarfile.open(compressed_file, 'r:gz') as tar:
                                tar.extractall(path=original_path)
                        
                        # Count files in the archive
                        with tarfile.open(compressed_file, 'r:gz') as tar:
                            files_restored += len(tar.getmembers())
                            total_size += os.path.getsize(compressed_file)
                        
                        self.logger.info(f"Restored compressed backup to {original_path}")
                    else:
                        # Handle regular files
                        for root, dirs, files in os.walk(source_folder):
                            # Calculate relative path from source folder
                            rel_path = os.path.relpath(root, source_folder)
                            if rel_path == '.':
                                rel_path = ''

                            # Create corresponding directory in destination
                            dest_dir = os.path.join(original_path, rel_path)
                            if needs_sudo:
                                run_sudo_command(['mkdir', '-p', dest_dir])
                            else:
                                os.makedirs(dest_dir, exist_ok=True)

                            # Restore files
                            for file in files:
                                source_file = os.path.join(root, file)
                                dest_file = os.path.join(dest_dir, file)

                                try:
                                    # Handle encrypted files
                                    if file.endswith('.gpg'):
                                        # Decrypt the file
                                        decrypted_file = os.path.join(dest_dir, file[:-4])  # Remove .gpg extension
                                        with open(source_file, 'rb') as f:
                                            decrypted_data = self.gpg.decrypt_file(f)
                                        
                                        if needs_sudo:
                                            # Write to a temporary file first
                                            temp_file = os.path.join('/tmp', os.path.basename(decrypted_file))
                                            with open(temp_file, 'wb') as f:
                                                f.write(decrypted_data.data)
                                            # Move to final location with sudo
                                            run_sudo_command(['mv', temp_file, decrypted_file])
                                        else:
                                            with open(decrypted_file, 'wb') as f:
                                                f.write(decrypted_data.data)
                                        
                                        files_restored += 1
                                        total_size += os.path.getsize(decrypted_file)
                                        self.logger.info(f"Decrypted and restored: {decrypted_file}")

                                    # Handle regular files
                                    else:
                                        if needs_sudo:
                                            # Copy to a temporary file first
                                            temp_file = os.path.join('/tmp', os.path.basename(dest_file))
                                            shutil.copy2(source_file, temp_file)
                                            # Move to final location with sudo
                                            run_sudo_command(['mv', temp_file, dest_file])
                                        else:
                                            shutil.copy2(source_file, dest_file)
                                        
                                        files_restored += 1
                                        total_size += os.path.getsize(dest_file)
                                        self.logger.info(f"Restored: {dest_file}")

                                except Exception as e:
                                    failed_files.append((source_file, str(e)))
                                    self.logger.error(f"Error restoring {source_file}: {e}")
                                    continue

                except Exception as e:
                    self.logger.error(f"Error restoring folder {folder_name}: {e}")
                    failed_files.append((folder_name, str(e)))
                    continue

            if files_restored == 0:
                raise Exception("No files were restored")

            # Log restore summary
            self.logger.info(f"Restore completed: {files_restored} files restored, total size: {total_size} bytes")
            if failed_files:
                self.logger.warning(f"Failed to restore {len(failed_files)} files/folders")

            return {
                'status': 'success',
                'files_restored': files_restored,
                'total_size': total_size,
                'path': first_restored_path,
                'backup_folder': backup_folder,
                'metadata': metadata,
                'failed_files': failed_files
            }

        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            raise

    def verify_backups(self):
        """Verify the integrity of all backups"""
        try:
            self.logger.info("Starting backup verification")
            result = {
                "status": "success",
                "total": 0,
                "verified": 0,
                "failed": 0,
                "failed_backups": []
            }

            # Get all backup commits
            commits = list(self.repo.iter_commits())
            result["total"] = len(commits)

            for commit in commits:
                try:
                    # Verify commit signature if present
                    if commit.gpgsig:
                        self.gpg.verify(commit.gpgsig)
                    
                    # Verify file integrity
                    for item in commit.tree.traverse():
                        if item.type == 'blob':  # File
                            # Verify file hash
                            file_content = item.data_stream.read()
                            if not file_content:
                                raise Exception(f"Empty file: {item.path}")
                            
                            # For encrypted files, verify they can be decrypted
                            if item.path.endswith('.gpg'):
                                try:
                                    self.gpg.decrypt_file(file_content)
                                except Exception as e:
                                    raise Exception(f"Failed to decrypt: {item.path}")
                    
                    result["verified"] += 1
                except Exception as e:
                    result["failed"] += 1
                    result["failed_backups"].append(commit.hexsha[:8])
                    self.logger.error(f"Verification failed for commit {commit.hexsha[:8]}: {str(e)}")

            if result["failed"] > 0:
                result["status"] = "warning"

            self.logger.info(f"Verification completed: {result['verified']} verified, {result['failed']} failed")
            return result

        except Exception as e:
            self.logger.error(f"Verification process failed: {str(e)}")
            raise

    def cleanup_all_backups(self):
        """Clean up all backups from the repository"""
        try:
            self.logger.info("Starting complete backup cleanup")
            
            # Get the repository size before cleanup
            size_before = self._get_repo_size()
            
            # Remove all files except .git
            for root, dirs, files in os.walk(self.repo_path):
                if '.git' in root:
                    continue
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                    except Exception as e:
                        self.logger.error(f"Failed to remove file {file}: {str(e)}")
            
            # Remove all directories except .git
            for root, dirs, files in os.walk(self.repo_path, topdown=False):
                if '.git' in root:
                    continue
                for dir_name in dirs:
                    try:
                        dir_path = os.path.join(root, dir_name)
                        if os.path.exists(dir_path):
                            shutil.rmtree(dir_path)
                    except Exception as e:
                        self.logger.error(f"Failed to remove directory {dir_name}: {str(e)}")
            
            # Create a new commit to remove all files
            try:
                self.repo.git.add(A=True)
                self.repo.git.commit(m="Cleanup: Remove all backups")
                self.repo.git.push('--force')
            except Exception as e:
                self.logger.error(f"Failed to commit cleanup: {str(e)}")
            
            # Calculate space freed
            size_after = self._get_repo_size()
            space_freed = size_before - size_after
            
            # Clear backup history
            history_path = os.path.expanduser("~/.autostash/backup_history")
            if os.path.exists(history_path):
                os.remove(history_path)
            
            # Clear last backup time
            last_backup_path = os.path.expanduser("~/.autostash/last_backup")
            if os.path.exists(last_backup_path):
                os.remove(last_backup_path)
            
            self.logger.info(f"Complete cleanup finished. Freed {space_freed} bytes")
            return {
                "status": "success",
                "space_freed": space_freed
            }
            
        except Exception as e:
            self.logger.error(f"Complete cleanup failed: {str(e)}")
            raise Exception(f"Failed to clean up backups: {str(e)}")

    def cleanup_old_backups(self, retention_days=None):
        """Clean up backups older than the specified retention period or all backups if retention_days is None"""
        try:
            if retention_days is None:
                return self.cleanup_all_backups()
                
            self.logger.info(f"Starting cleanup of backups older than {retention_days} days")
            result = {
                "removed": 0,
                "space_freed": 0
            }

            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
            
            # Get all backup commits
            commits = list(self.repo.iter_commits())
            
            for commit in commits:
                commit_date = datetime.datetime.fromtimestamp(commit.committed_date)
                if commit_date < cutoff_date:
                    try:
                        # Calculate space before removal
                        size_before = self._get_repo_size()
                        
                        # Remove the commit
                        self.repo.git.reset('--hard', commit.hexsha + '^')
                        self.repo.git.push('--force')
                        
                        # Calculate space freed
                        size_after = self._get_repo_size()
                        result["space_freed"] += size_before - size_after
                        result["removed"] += 1
                        
                        self.logger.info(f"Removed backup from {commit_date}")
                    except Exception as e:
                        self.logger.error(f"Failed to remove backup from {commit_date}: {str(e)}")

            self.logger.info(f"Cleanup completed: {result['removed']} backups removed, {result['space_freed']} bytes freed")
            return result

        except Exception as e:
            self.logger.error(f"Cleanup process failed: {str(e)}")
            raise

    def _get_repo_size(self):
        """Get the total size of the repository"""
        total_size = 0
        for root, dirs, files in os.walk(self.repo_path):
            for file in files:
                file_path = os.path.join(root, file)
                total_size += os.path.getsize(file_path)
        return total_size

    def manage_gpg_keys(self, action, key_data=None):
        """Manage GPG keys for backup encryption"""
        try:
            if action == "import":
                if not key_data:
                    raise ValueError("Key data required for import")
                result = self.gpg.import_keys(key_data)
                return {"status": "success", "imported": result.count}
            
            elif action == "export":
                keys = self.gpg.list_keys()
                if not keys:
                    raise Exception("No keys available for export")
                exported = self.gpg.export_keys(keys[0]['fingerprint'])
                return {"status": "success", "key_data": exported}
            
            elif action == "generate":
                # Generate a new GPG key
                input_data = self.gpg.gen_key_input(
                    name_email=f"{os.getenv('USER')}@localhost",
                    passphrase="",  # Empty passphrase for automated backups
                    key_type="RSA",
                    key_length=4096
                )
                key = self.gpg.gen_key(input_data)
                return {"status": "success", "fingerprint": key.fingerprint}
            
            else:
                raise ValueError(f"Invalid action: {action}")

        except Exception as e:
            self.logger.error(f"GPG key management failed: {str(e)}")
            raise

