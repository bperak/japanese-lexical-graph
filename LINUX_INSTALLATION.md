# Detailed Linux Installation Guide

This guide provides comprehensive instructions for installing and running the Japanese Lexical Graph application on Linux systems.

## System Prerequisites

Different Linux distributions require different packages. Here are instructions for common distributions:

### Debian/Ubuntu-based Systems
```bash
# Update package lists
sudo apt update

# Install required system packages
sudo apt install -y python3-dev python3-pip python3-venv git build-essential libssl-dev libffi-dev

# Optional: Install packages for better performance with NetworkX
sudo apt install -y python3-numpy python3-scipy
```

### Red Hat/Fedora-based Systems
```bash
# Install required system packages
sudo dnf install -y python3-devel python3-pip git openssl-devel libffi-devel gcc make

# Optional: Install packages for better performance with NetworkX
sudo dnf install -y python3-numpy python3-scipy
```

### Arch Linux
```bash
# Install required system packages
sudo pacman -S python python-pip git base-devel openssl

# Optional: Install packages for better performance with NetworkX
sudo pacman -S python-numpy python-scipy
```

## Setting Up the Application

1. Clone the repository and navigate to the project directory
   ```bash
   git clone https://github.com/bperak/japanese-lexical-graph.git
   cd japanese-lexical-graph
   ```

2. Create and activate a virtual environment
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Update pip and install dependencies
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
   
   **Note**: The `jreadability` library will automatically download Japanese language models (including MeCab and UniDic) during installation. This may take a few minutes on first install.

   If you encounter issues with Japanese text analysis, you can manually reinstall:
   ```bash
   pip install --force-reinstall jreadability
   ```

4. Create a `.env` file with your API key
   ```bash
   echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
   echo "GEMINI_DEFAULT_MODEL=gemini-2.0-flash" >> .env
   chmod 600 .env  # Restrict permissions for security
   ```

5. Start the application
   ```bash
   python app.py
   ```
   
   The application will be available at `http://localhost:5000` by default.

## Running as a Service (systemd)

To run the application as a service that starts automatically on boot:

1. Create a systemd service file
   ```bash
   sudo nano /etc/systemd/system/japanese-lexical-graph.service
   ```

2. Add the following content (adjust paths as needed):
   ```
   [Unit]
   Description=Japanese Lexical Graph Web Application
   After=network.target

   [Service]
   User=your_username
   WorkingDirectory=/path/to/japanese-lexical-graph
   Environment="PATH=/path/to/japanese-lexical-graph/venv/bin"
   ExecStart=/path/to/japanese-lexical-graph/venv/bin/python app.py

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable japanese-lexical-graph
   sudo systemctl start japanese-lexical-graph
   ```

4. Check the status of the service
   ```bash
   sudo systemctl status japanese-lexical-graph
   ```

## Running Behind a Reverse Proxy (Nginx)

For production deployments, it's recommended to run the application behind a reverse proxy:

1. Install Nginx
   ```bash
   # Debian/Ubuntu
   sudo apt install -y nginx

   # Red Hat/Fedora
   sudo dnf install -y nginx

   # Arch Linux
   sudo pacman -S nginx
   ```

2. Create a Nginx site configuration
   ```bash
   sudo nano /etc/nginx/sites-available/japanese-lexical-graph
   ```

3. Add the following configuration (adjust as needed):
   ```
   server {
       listen 80;
       server_name your-domain.com www.your-domain.com;

       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

4. Enable the site and restart Nginx
   ```bash
   # Debian/Ubuntu
   sudo ln -s /etc/nginx/sites-available/japanese-lexical-graph /etc/nginx/sites-enabled/
   
   # All distributions
   sudo nginx -t  # Test the configuration
   sudo systemctl restart nginx
   ```

## Troubleshooting Common Linux Issues

### Permission Issues
If you encounter permission errors:
```bash
# Verify ownership of the application directory
sudo chown -R your_username:your_username /path/to/japanese-lexical-graph

# Ensure the pickle file is readable
chmod 644 /path/to/japanese-lexical-graph/G_synonyms_2024_09_18.pickle
```

### Network Access Issues
If you can't access the application:
```bash
# Check if the application is running
ps aux | grep app.py

# Verify the firewall settings
sudo ufw status
# If needed, allow the port
sudo ufw allow 5000/tcp

# For SELinux systems (RHEL/Fedora)
sudo setsebool -P httpd_can_network_connect 1
```

### Python Issues
If you encounter missing packages or version issues:
```bash
# Verify Python version
python --version  # Should be 3.10+

# Verify correct pip is used
which pip  # Should point to your virtual environment

# Reinstall requirements with verbose output
pip install -v -r requirements.txt
```

### Japanese Text Analysis Issues
If readability analysis is not working correctly:
```bash
# Check if jreadability is properly installed
python -c "import jreadability; print('jreadability available')"

# Reinstall Japanese language dependencies
pip install --force-reinstall jreadability fugashi unidic-lite

# If MeCab issues persist on some systems, you may need system MeCab
# Debian/Ubuntu
sudo apt install -y mecab mecab-ipadic-utf8

# Red Hat/Fedora
sudo dnf install -y mecab mecab-ipadic

# Test readability analysis
python -c "from readability_helper import analyze_text_readability; print(analyze_text_readability('これはテストです。'))"
```

### Memory Issues with Large Graph Files
If the application crashes when loading large graph files:
```bash
# Increase system swap (example adds 2GB)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
# To make permanent, add to /etc/fstab:
# /swapfile swap swap defaults 0 0
```

## Production Deployment Tips

### Security Considerations

1. Set up HTTPS with Let's Encrypt
   ```bash
   # Install Certbot (Debian/Ubuntu)
   sudo apt install -y certbot python3-certbot-nginx
   
   # Obtain certificate
   sudo certbot --nginx -d your-domain.com -d www.your-domain.com
   ```

2. Configure user permissions appropriately
   ```bash
   # Create a dedicated user
   sudo adduser --system --group japanapp
   
   # Set ownership
   sudo chown -R japanapp:japanapp /path/to/japanese-lexical-graph
   ```

3. Set up proper firewall rules
   ```bash
   # Allow only necessary ports
   sudo ufw allow ssh
   sudo ufw allow http
   sudo ufw allow https
   sudo ufw enable
   ```

### Performance Optimization

1. Install Redis for improved caching
   ```bash
   # Debian/Ubuntu
   sudo apt install -y redis-server
   
   # Configure app to use Redis
   echo "REDIS_URL=redis://localhost:6379/0" >> .env
   ```

2. Set up log rotation
   ```bash
   sudo nano /etc/logrotate.d/japanese-lexical-graph
   ```
   
   Add:
   ```
   /path/to/japanese-lexical-graph/logs/*.log {
     daily
     missingok
     rotate 14
     compress
     delaycompress
     notifempty
     create 0640 japanapp japanapp
   }
   ``` 