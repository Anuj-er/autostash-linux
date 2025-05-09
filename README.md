# 🚀 AutoStash - Linux Backup System

<div align="center">
  <h3>Team Project - Linux System Programming</h3>
  <p>A comprehensive backup solution developed as part of our Linux System Programming course</p>
</div>

## 👥 Team Members

<table>
<tr>
<td align="center">
  <b>Anuj Kumar</b><br>
  <sub>Backend Development & System Integration</sub>
</td>
<td align="center">
  <b>Anushi</b><br>
  <sub>GUI Development & User Interface</sub>
</td>
</tr>
<tr>
<td align="center">
  <b>Akanksha Mishra</b><br>
  <sub>Backup Logic & Security</sub>
</td>
<td align="center">
  <b>Abhinav Rathee</b><br>
  <sub>System Monitoring & Documentation</sub>
</td>
</tr>
</table>

## 📋 Project Overview

AutoStash is a Linux backup solution developed as our team project for the Linux System Programming course. It demonstrates our understanding of Linux system programming concepts, including file operations, process management, and system monitoring.

### ✨ Key Features

<table>
<tr>
<td width="50%">

- 🔒 **Security Features**
  - GPG encryption implementation
  - Secure file handling
  - Access control mechanisms

- ⚡ **System Integration**
  - Resource monitoring
  - Process management
  - File system operations

</td>
<td width="50%">

- 📊 **User Interface**
  - Modern GUI using tkinter
  - Real-time system monitoring
  - Intuitive backup management

- 🔄 **Backup Features**
  - Incremental backups
  - GitHub integration
  - Automated scheduling

</td>
</tr>
</table>

## 🏗️ Project Structure

```mermaid
graph TD
    A[AutoStash] --> B[core/]
    A --> C[docs/]
    A --> D[requirements/]
    A --> E[main.py]
    A --> F[styles.py]
    
    B --> B1[backup_logic.py]
    B --> B2[config_manager.py]
    B --> B3[github_integration.py]
    B --> B4[imports.py]
    B --> B5[resource_monitor.py]
    B --> B6[scheduler.py]
    B --> B7[system_info.py]
    
    C --> C1[README.md]
    C --> C2[setup.md]
    C --> C3[usage.md]
    
    D --> D1[base.txt]
    D --> D2[dev.txt]
```

## 🛠️ Technical Implementation

### Core Components

```mermaid
graph LR
    A[System Monitoring] --> D[AutoStash]
    B[Backup Logic] --> D
    C[GUI Interface] --> D
    E[Security] --> D
```

### System Architecture

```mermaid
sequenceDiagram
    participant U as User Interface
    participant B as Backup System
    participant M as Monitor
    participant S as Security

    U->>B: Backup Request
    B->>M: Check Resources
    B->>S: Verify Security
    B->>B: Process Backup
    B->>U: Update Status
```

## 📚 Documentation

- [Setup Guide](docs/setup.md) - Installation and configuration
- [Usage Guide](docs/usage.md) - User manual and features
- [Technical Documentation](docs/technical.md) - Implementation details

## 🎓 Learning Outcomes

This project helped us gain practical experience in:
- Linux system programming
- File system operations
- Process management
- GUI development
- Security implementation
- Team collaboration
- Documentation writing

## 🛠️ Development Setup

### For Developers
```bash
# Clone the repository
git clone https://github.com/yourusername/autostash.git
cd autostash

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -r requirements/dev.txt
```

### Building the Executable
To create a standalone executable that doesn't require Python or dependencies to be installed:

```bash
# Install development dependencies
pip install -r requirements/dev.txt

# Build the executable
python build.py
```

The executable will be created in the `dist` directory. Users can simply run:
```bash
./dist/autostash
```

### For End Users
End users only need to:
1. Download the executable from the releases page
2. Make it executable:
   ```bash
   chmod +x autostash
   ```
3. Run it:
   ```bash
   ./autostash
   ```

## 📝 Project Report

Our detailed project report covers:
- System architecture
- Implementation details
- Testing methodology
- Performance analysis
- Future improvements

## 🤝 Acknowledgments

We would like to thank our course instructor and mentors for their guidance throughout this project.

---

<div align="center">
  <p>Developed as part of Linux System Programming Course</p>
  <p>© 2024 Team AutoStash</p>
</div>