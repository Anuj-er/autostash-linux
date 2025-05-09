# AutoStash Setup Guide

## Prerequisites
- Python 3.8 or higher
- Git
- GitHub account (for cloud backup)
- GPG (for encrypted backups)

## System Requirements
- Linux operating system
- Minimum 2GB RAM
- 1GB free disk space
- Internet connection for GitHub integration

## Installation Steps

### 1. Clone the Repository
```bash
git clone https://github.com/Anuj-er/autostash-linux.git
cd autostash
```

### 2. Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies
```bash
# Install base requirements
pip install -r requirements/base.txt

# For development (optional)
pip install -r requirements/dev.txt
```

### 4. Configure GitHub Integration
1. Create a GitHub Personal Access Token:
   - Go to GitHub Settings > Developer Settings > Personal Access Tokens
   - Generate new token with 'repo' scope
   - Copy the token

2. Configure AutoStash:
   - Run the application
   - Go to Backup Configuration
   - Click "Connect GitHub"
   - Enter your GitHub token

### 5. Set Up GPG (Optional, for encrypted backups)
1. Install GPG:
   ```bash
   sudo apt-get install gnupg  # On Debian/Ubuntu
   # or
   sudo yum install gnupg  # On RHEL/CentOS
   ```

2. Generate GPG key:
   ```bash
   gpg --full-generate-key
   ```

3. Export public key:
   ```bash
   gpg --export --armor your-email@example.com > public.key
   ```

### 6. Configure System Permissions
The application requires certain system permissions to function properly:

1. Create required directories:
   ```bash
   sudo mkdir -p /var/log/autostash
   sudo chown $USER:$USER /var/log/autostash
   ```

2. Set up backup directories:
   ```bash
   mkdir -p ~/.autostash
   ```

## Troubleshooting

### Common Issues

1. Permission Denied
   - Ensure you have write permissions to required directories
   - Run with sudo if necessary

2. GitHub Connection Failed
   - Verify your GitHub token is valid
   - Check internet connection
   - Ensure token has correct permissions

3. GPG Issues
   - Verify GPG is installed
   - Check key permissions
   - Ensure key is properly exported

### Getting Help
- Check the [Usage Guide](usage.md)
- Open an issue on GitHub
- Contact support at support@autostash.com

## Next Steps
- Read the [Usage Guide](usage.md) to learn how to use AutoStash
- Configure your first backup
- Set up automated scheduling 