# AWS EC2 Deployment Guide

## Overview

Production deployment of FastAPI LangGraph Agent Service on AWS EC2 with Docker.

## Prerequisites

- AWS Account (Free Tier eligible)
- Local terminal access
- Project repository with Dockerfile

## Deployment Steps

### Step 1: AWS EC2 Instance Setup

#### 1.1 Create EC2 Instance

1. **AWS Console** → **EC2** → **Launch Instance**
2. **Configuration:**
   - **Name**: `fastapi-ubuntu`
   - **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)
   - **Instance Type**: `t2.micro` (Free Tier) or `t3.micro`
   - **Key Pair**: Create new or use existing (`fastAPI-keyPair`)
   - **Security Group**: Create new
     - **Name**: `ubuntu-sg`
     - **Inbound Rules**:
       - SSH (22): My IP
       - HTTP (80): Anywhere (0.0.0.0/0)
       - HTTPS (443): Anywhere (0.0.0.0/0)
       - Custom TCP (8000): Anywhere (0.0.0.0/0) - FastAPI port

#### 1.2 Connect to EC2

```bash
# Local terminal
ssh -i /path/to/fastAPI-keyPair.pem ubuntu@<EC2-PUBLIC-IP>

# Example:
ssh -i ~/Desktop/fastAPI-keyPair.pem ubuntu@13.60.28.115
```

**Note**: If "Permissions too open" error:
```bash
chmod 400 ~/Desktop/fastAPI-keyPair.pem
```

---

### Step 2: Server Preparation

#### 2.1 System Update

```bash
sudo apt update && sudo apt upgrade -y
```

#### 2.2 Install Docker

```bash
# Install Docker
sudo apt install docker.io docker-compose -y

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER

# Reconnect to apply changes
exit
# Then reconnect:
ssh -i ~/Desktop/fastAPI-keyPair.pem ubuntu@<EC2-PUBLIC-IP>

# Verify
docker --version
```

---

### Step 3: Application Deployment

#### 3.1 Upload Code

**Option A: SCP (Local → EC2)**

```bash
# From local terminal
scp -i ~/Desktop/fastAPI-keyPair.pem \
    -r /path/to/BE/ \
    ubuntu@<EC2-PUBLIC-IP>:~/
```

**Option B: Git Clone**

```bash
# On EC2
git clone https://github.com/yourusername/your-repo.git
cd your-repo
```

#### 3.2 Environment Configuration

```bash
cd ~/BE

# Create .env file
nano .env
```

**.env content:**
```bash
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_MODEL=gpt-4o-mini
CHECKPOINT_DB_PATH=data/agent_checkpoints.sqlite
BACKEND_CORS_ORIGINS=http://localhost:5173,https://your-project.vercel.app
BACKEND_CORS_ORIGIN_REGEX=
AGENT_FALLBACK_MESSAGE=We could not process your request right now. Please try again shortly.
```

**Save**: `Ctrl+O` → Enter → `Ctrl+X`

#### 3.3 Build and Run

```bash
# Build Docker image
docker build -t fastapi-app .

# Run container
docker run -d -p 8000:8000 --name myapp fastapi-app

# Check running containers
docker ps

# View logs
docker logs myapp
```

---

### Step 4: Verification

#### 4.1 Health Check

```bash
# On EC2
curl http://localhost:8000/health/live

# Expected: {"status": "ok"}
```

#### 4.2 External Access

From browser:
```
http://<EC2-PUBLIC-IP>:8000/docs       # Swagger UI
http://<EC2-PUBLIC-IP>:8000/health/live # Health check
```

**Troubleshooting:**
- If connection refused → Check security group (port 8000 open?)
- If timeout → Check EC2 state (Running?), Public IP assigned?

---

## Frontend Deployment (Vercel)

### Frontend Environment Variables

Create `frontend/.env` for local development or configure the same values in Vercel:

```bash
VITE_API_URL=http://localhost:8000
```

For production Vercel deployments:

```bash
VITE_API_URL=http://<EC2-PUBLIC-IP>:8000
```

### CORS Configuration

The backend must allow the frontend origin:

```bash
BACKEND_CORS_ORIGINS=http://localhost:5173,https://your-project.vercel.app
```

Optional preview deployment regex:

```bash
BACKEND_CORS_ORIGIN_REGEX=https://your-project-.*\.vercel\.app
```

---

## Docker Management

### Useful Commands

```bash
# View logs
docker logs myapp
docker logs -f myapp  # Follow mode

# Restart container
docker restart myapp

# Stop container
docker stop myapp

# Remove container
docker rm myapp

# Rebuild after code changes
docker stop myapp
docker rm myapp
docker build -t fastapi-app .
docker run -d -p 8000:8000 --name myapp fastapi-app

# SSH into running container
docker exec -it myapp /bin/bash
```

---

## Production Enhancements

### 1. Nginx Reverse Proxy (Optional)

Install Nginx for better performance and SSL:

```bash
sudo apt install nginx -y

# Configure /etc/nginx/sites-available/default
sudo nano /etc/nginx/sites-available/default
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo nginx -t
sudo systemctl restart nginx
```

### 2. Auto-restart on Boot

```bash
# Docker container auto-restart
docker run -d -p 8000:8000 --restart unless-stopped --name myapp fastapi-app
```

### 3. Database Upgrade (SQLite → PostgreSQL)

For production, migrate to PostgreSQL:

```bash
# Install PostgreSQL on EC2
sudo apt install postgresql postgresql-contrib -y

# Or use AWS RDS
# Update .env:
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

---

## Cost Management

### AWS Free Tier Limits

| Resource | Free Tier | Notes |
|----------|-----------|-------|
| EC2 t2.micro | 750 hours/month | 24/7 running = ~$0 |
| EBS (8GB) | 30GB-month | Included |
| Data Transfer | 100GB/month | Inbound free, outbound costs |

### Cost Optimization

1. **Stop when not in use:**
   ```bash
   # AWS Console → EC2 → Instance → Stop
   # (Note: EBS costs still apply)
   ```

2. **Terminate completely:**
   ```bash
   # AWS Console → EC2 → Instance → Terminate
   # (All costs stop, data lost)
   ```

3. **Monitoring:**
   - AWS Billing Dashboard
   - Set up billing alerts ($10 threshold)

---

## Troubleshooting

### Permission Denied (SSH)

```bash
# Fix key permissions
chmod 400 ~/Desktop/fastAPI-keyPair.pem

# Use correct username
# Ubuntu AMI: ubuntu@
# Amazon Linux AMI: ec2-user@
```

### Docker Permission Denied

```bash
# Re-add to docker group
sudo usermod -aG docker $USER
# Logout and reconnect
```

### Port 8000 Connection Refused

1. Check security group (inbound rule for 8000)
2. Check container is running: `docker ps`
3. Check logs: `docker logs myapp`

### High Latency

- EC2 region: Choose closest to users (Seoul for Korea)
- Consider upgrading to t3.small if needed (not Free Tier)

---

## Security Checklist

- [ ] Security Group: SSH restricted to My IP only
- [ ] .env file: Never committed to git
- [ ] API Keys: Rotated regularly
- [ ] Updates: `sudo apt update && sudo apt upgrade` monthly
- [ ] Backups: Database backup strategy (if using PostgreSQL)

---

## Next Steps

1. **Domain Setup**: Route53 + Elastic IP
2. **SSL Certificate**: Let's Encrypt (Certbot)
3. **Monitoring**: CloudWatch or Prometheus
4. **CI/CD**: GitHub Actions for automated deployment
