#!/bin/bash
# Deployment script for Japanese Lexical Graph on Linux servers with HTTPS support

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting deployment of Japanese Lexical Graph with HTTPS...${NC}"

# Check if running as root (not recommended)
if [ "$EUID" -eq 0 ]; then
  echo -e "${RED}Warning: Running as root is not recommended.${NC}"
  read -p "Continue anyway? (y/n): " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment aborted.${NC}"
    exit 1
  fi
fi

# SSL Certificate Configuration
CERT_DIR="/home/Liks/certs"
CERT_FILE="$CERT_DIR/liks.cer"
KEY_FILE="$CERT_DIR/liks.key"

# Check for existing SSL certificates
echo -e "${YELLOW}Checking SSL certificates...${NC}"
if [ ! -d "$CERT_DIR" ]; then
  echo -e "${YELLOW}Creating certificate directory at $CERT_DIR${NC}"
  mkdir -p "$CERT_DIR"
fi

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
  echo -e "${YELLOW}SSL certificate or key not found. Would you like to:${NC}"
  echo "1) Use self-signed certificate (not recommended for production)"
  echo "2) Specify path to existing certificates"
  echo "3) Deploy without SSL (not recommended)"
  read -p "Choose an option (1-3): " ssl_option
  
  case $ssl_option in
    1)
      echo -e "${YELLOW}Generating self-signed SSL certificate (valid for 365 days)...${NC}"
      openssl req -x509 -newkey rsa:4096 -nodes -out "$CERT_FILE" -keyout "$KEY_FILE" -days 365 -subj "/C=HR/ST=Primorje-Gorski Kotar/L=Rijeka/O=University of Rijeka/OU=IT/CN=japanese-lexical-graph.ffri.hr"
      if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to generate self-signed certificates. Aborting deployment.${NC}"
        exit 1
      fi
      echo -e "${GREEN}Self-signed certificate generated successfully!${NC}"
      ;;
    2)
      read -p "Enter path to certificate file: " custom_cert
      read -p "Enter path to key file: " custom_key
      
      if [ ! -f "$custom_cert" ] || [ ! -f "$custom_key" ]; then
        echo -e "${RED}Certificate or key not found at the specified paths. Aborting deployment.${NC}"
        exit 1
      fi
      
      echo -e "${YELLOW}Copying certificates to $CERT_DIR${NC}"
      cp "$custom_cert" "$CERT_FILE"
      cp "$custom_key" "$KEY_FILE"
      
      # Set proper permissions
      chmod 600 "$KEY_FILE"
      chmod 644 "$CERT_FILE"
      ;;
    3)
      echo -e "${RED}Warning: Deploying without SSL is not recommended for production.${NC}"
      echo -e "${YELLOW}Setting environment variables to disable SSL...${NC}"
      export USE_SSL=false
      ;;
    *)
      echo -e "${RED}Invalid option. Aborting deployment.${NC}"
      exit 1
      ;;
  esac
else
  echo -e "${GREEN}SSL certificates found at:${NC}"
  echo -e "Certificate: $CERT_FILE"
  echo -e "Key: $KEY_FILE"
  
  # Set proper permissions
  chmod 600 "$KEY_FILE"
  chmod 644 "$CERT_FILE"
fi

# Export SSL certificate paths for the Flask application
export SSL_CERT_PATH="$CERT_FILE"
export SSL_KEY_PATH="$KEY_FILE"

# Update repository
echo -e "${YELLOW}Updating repository from GitHub...${NC}"
git pull origin main
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to pull latest changes. Aborting deployment.${NC}"
  exit 1
fi

# Setup virtual environment
echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
if [ ! -d "myenv" ]; then
  python -m venv myenv
  if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create virtual environment. Aborting deployment.${NC}"
    exit 1
  fi
fi

# Activate virtual environment and install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
source myenv/bin/activate
pip install -r requirements.txt
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to install dependencies. Aborting deployment.${NC}"
  exit 1
fi

# Check if port 8003 is already in use
port_check=$(netstat -tuln | grep 8003)
if [ ! -z "$port_check" ]; then
  echo -e "${YELLOW}Port 8003 is already in use. Checking for Flask processes...${NC}"
  flask_proc=$(ps aux | grep "python app.py" | grep -v grep)
  if [ ! -z "$flask_proc" ]; then
    echo -e "${YELLOW}Found running Flask application. Stopping it...${NC}"
    pid=$(echo $flask_proc | awk '{print $2}')
    kill $pid
    sleep 2
  fi
fi

# Run tests if they exist
if [ -d "tests" ]; then
  echo -e "${YELLOW}Running tests...${NC}"
  python -m unittest discover tests
  if [ $? -ne 0 ]; then
    echo -e "${RED}Tests failed. Aborting deployment.${NC}"
    exit 1
  fi
fi

# Create a systemd service file for automatic startup
echo -e "${YELLOW}Creating systemd service file...${NC}"
SERVICE_FILE="/tmp/japanese-lexical-graph.service"
cat > $SERVICE_FILE << EOF
[Unit]
Description=Japanese Lexical Graph Visualization Service
After=network.target

[Service]
User=$(whoami)
WorkingDirectory=$(pwd)
Environment="SSL_CERT_PATH=$CERT_FILE"
Environment="SSL_KEY_PATH=$KEY_FILE"
ExecStart=$(which python) app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo -e "${YELLOW}To install as a system service, run:${NC}"
echo -e "sudo cp $SERVICE_FILE /etc/systemd/system/"
echo -e "sudo systemctl enable japanese-lexical-graph.service"
echo -e "sudo systemctl start japanese-lexical-graph.service"

# Start application in background
echo -e "${YELLOW}Starting application...${NC}"
nohup python app.py > app.log 2>&1 &
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to start application. Check app.log for details.${NC}"
  exit 1
fi

# Display HTTPS URL
if [ "$USE_SSL" != "false" ]; then
  echo -e "${GREEN}Deployment completed successfully!${NC}"
  echo -e "${YELLOW}Application is running with HTTPS at: https://31.147.206.155:8003${NC}"
  echo -e "${YELLOW}Certificate location: $CERT_FILE${NC}"
  echo -e "${YELLOW}Key location: $KEY_FILE${NC}"
else
  echo -e "${GREEN}Deployment completed successfully!${NC}"
  echo -e "${RED}Application is running WITHOUT SSL at: http://31.147.206.155:8003${NC}"
  echo -e "${RED}Consider enabling SSL for production use!${NC}"
fi

echo -e "${YELLOW}Check application logs with: tail -f app.log${NC}"

# Additional instructions for Let's Encrypt SSL (if needed)
echo -e "\n${GREEN}=== Additional SSL Setup Information ===${NC}"
echo -e "${YELLOW}For production use, consider using Let's Encrypt for free SSL certificates:${NC}"
echo -e "1. Install certbot: sudo apt install certbot"
echo -e "2. Get a certificate: sudo certbot certonly --standalone -d your-domain.com"
echo -e "3. Update certificate paths in the deployment script or environment variables"
echo -e "4. Certificates will be available at: /etc/letsencrypt/live/your-domain.com/"
echo -e "${YELLOW}See https://letsencrypt.org/getting-started/ for more information.${NC}" 