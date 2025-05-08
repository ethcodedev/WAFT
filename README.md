# WAFT: A Simple Fuzzer Tool
FInal project for COSI 107a

## Basic Setup

### Clone repo
```bash
git clone https://github.com/ethcodedev/FuzzerTool.git 
```

### Setup venv
```bash
1. cd FuzzerTool
2. python3 -m venv .venv
3. source .venv/bin/activate 
```

### Install dependencies
```bash
pip install -r requirements.txt
```

## Setup: DVWA via Docker

This project assumes you’re running DVWA locally in a Docker container. Follow these steps:

### Prerequisites

- Docker Desktop (or Docker Engine) installed on your machine  
- Ports **80** (HTTP) and **3306** (MySQL) free on `localhost`  

### 1. Pull & Run the DVWA Container

```bash
# 1.1 Pull the official DVWA image
docker pull vulnerables/web-dvwa

# 1.2 Run DVWA
#   - `--rm` removes the container when stopped
#   - `-d` runs in the background
#   - `-p 80:80` maps container’s port 80 → host’s port 80
docker run --rm -d -p 80:80 vulnerables/web-dvwa
```

### 2. Fuzzing DVWA (Damn Vulnerable Web Application)

#### Discover all inputs in DVWA
```bash
python fuzz.py discover http://localhost:80 \
  --common-words=words.txt \
  --extensions=extensions.txt \
  --custom-auth=dvwa
```

#### Run full vulnerability test against DVWA
```bash
python fuzz.py test http://localhost:80 \
  --vectors=vectors.txt \
  --sanitized-chars=badchars.txt \
  --sensitive=sensitive.txt \
  --slow=500 \
  --custom-auth=dvwa
```
