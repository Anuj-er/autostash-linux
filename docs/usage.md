# AutoStash Usage Guide

## Getting Started

### Launching the Application
```bash
python main.py
```

### Main Interface
The application has three main tabs:
1. Backup Configuration
2. System Monitor
3. Backup History

## Backup Configuration

### Selecting Folders
1. Click "Browse" to select folders for backup
2. Add multiple folders as needed
3. Remove folders using the "Remove" button

### GitHub Repository
1. Click "Connect GitHub" to authenticate
2. Select an existing repository or create a new one
3. The repository will be used to store your backups

### Backup Options
- **System Files**: Backup system directories (requires sudo)
- **Encryption**: Encrypt backups using GPG
- **Compression**: Compress backup files to save space
- **Incremental**: Only backup changed files

### Scheduling
1. Select backup frequency:
   - Daily
   - Weekly
   - Monthly
   - Custom
2. Set backup time
3. Click "Set Schedule" to activate

## System Monitor

### Resource Usage
- Real-time CPU usage
- Memory utilization
- Disk space monitoring
- System information display

### Warnings
- Resource usage warnings
- Backup status notifications
- System health indicators

## Backup History

### Viewing Backups
- List of all backups with timestamps
- Backup details (size, files, type)
- Search and filter functionality

### Restoring Backups
1. Select a backup from the history
2. Click "Restore" or double-click the backup
3. Choose restore location
4. Confirm restoration

### Managing Backups
- View backup details
- Delete old backups
- Verify backup integrity
- Export backup information

## Advanced Options

### Configuration
- Export/Import settings
- Custom backup paths
- Advanced scheduling options

### Maintenance
- Verify all backups
- Clean up old backups
- Repair corrupted backups

### Security
- Manage GPG keys
- Configure encryption settings
- Set up backup authentication

## Best Practices

### Regular Maintenance
1. Monitor backup history
2. Clean up old backups regularly
3. Verify backup integrity
4. Check system resources

### Security
1. Keep GPG keys secure
2. Regularly rotate GitHub tokens
3. Use strong encryption
4. Monitor access logs

### Performance
1. Schedule backups during low-usage periods
2. Monitor system resources
3. Use incremental backups for large datasets
4. Compress backups to save space

## Troubleshooting

### Common Issues
1. Backup fails to start
   - Check permissions
   - Verify GitHub connection
   - Ensure sufficient disk space

2. Restore fails
   - Verify backup integrity
   - Check file permissions
   - Ensure sufficient space

3. Schedule issues
   - Check system time
   - Verify cron service
   - Review schedule settings

### Getting Help
- Check the [Setup Guide](setup.md)
- Review error logs
- Contact support

## Keyboard Shortcuts
- `Ctrl+B`: Start backup
- `Ctrl+R`: Restore backup
- `Ctrl+S`: Save settings
- `Ctrl+Q`: Quit application

## Support
For additional help:
- Email: support@autostash.com
- GitHub Issues: [Report Issues](https://github.com/Anuj-er/autostash-linux/issues)
- Documentation: [Full Documentation](https://github.com/Anuj-er/autostash-linux/docs) 
