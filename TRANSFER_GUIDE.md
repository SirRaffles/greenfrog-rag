# Transferring matchainitiative Content from MacBook to NAS

## Issue Diagnosis

SSH/SCP is failing between MacBook and NAS due to authentication issues.

**Symptoms:**
- SCP commands from MacBook fail
- Password authentication errors in `/var/log/auth.log`
- Connection times out or rejects password

---

## Solution 1: Use SMB/CIFS (Recommended - Easiest)

### On MacBook:

1. **Connect to NAS via Finder**
   ```
   - Open Finder
   - Press ⌘K (Go → Connect to Server)
   - Enter: smb://192.168.50.171
   - Username: Davrine
   - Password: UGrinFr0g!n
   ```

2. **Navigate and Copy**
   ```
   - Navigate to: docker/greenfrog-rag/data/scraped/
   - Drag and drop: ~/Documents/matchainitiative folder
   ```

**Advantages:**
- ✅ No SSH required
- ✅ Visual interface
- ✅ Reliable on macOS

---

## Solution 2: Fix SSH Key Authentication

The NAS has SSH keys but they're not trusted by the MacBook.

### On MacBook Terminal:

1. **Copy NAS public key to MacBook**
   ```bash
   # First, get the NAS public key content
   # You'll need to run this on the NAS and copy the output
   cat /volume1/homes/Davrine/.ssh/id_rsa.pub
   ```

2. **Or generate new SSH key on MacBook**
   ```bash
   # Generate key on MacBook (if you don't have one)
   ssh-keygen -t rsa -b 4096 -C "macbook@greenfrog"

   # Copy MacBook public key to NAS
   ssh-copy-id Davrine@192.168.50.171
   # Enter password: UGrinFr0g!n
   ```

3. **Test SSH connection**
   ```bash
   ssh Davrine@192.168.50.171 "hostname && whoami"
   # Should work without password prompt
   ```

4. **Then use SCP**
   ```bash
   scp -r ~/Documents/matchainitiative Davrine@192.168.50.171:/volume1/docker/greenfrog-rag/data/scraped/
   ```

---

## Solution 3: Use rsync over SSH

More reliable than SCP for large transfers:

```bash
rsync -avz --progress \
  ~/Documents/matchainitiative/ \
  Davrine@192.168.50.171:/volume1/docker/greenfrog-rag/data/scraped/matchainitiative/
```

**Advantages:**
- ✅ Resumes on interruption
- ✅ Shows progress
- ✅ Only transfers changed files

---

## Solution 4: Use NAS Web Interface (UGREEN File Manager)

1. Open browser: `http://192.168.50.171`
2. Login with Davrine / UGrinFr0g!n
3. Navigate to: `docker/greenfrog-rag/data/scraped/`
4. Upload: `matchainitiative` folder

**Note:** May be slow for large folders

---

## Solution 5: Enable Password Authentication (If SSH key fails)

### On NAS (via current session):

```bash
# Backup current config
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup

# Enable password authentication
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Restart SSH service
sudo systemctl restart ssh

# Verify
sudo systemctl status ssh
```

Then retry SCP from MacBook.

---

## Manual Verification Steps

### On MacBook:

```bash
# 1. Check if you can ping the NAS
ping -c 3 192.168.50.171

# 2. Check if SSH port is reachable
nc -zv 192.168.50.171 22

# 3. Try verbose SSH connection
ssh -v Davrine@192.168.50.171

# 4. Check your SSH config
cat ~/.ssh/config
```

### Common Issues:

| Issue | Solution |
|-------|----------|
| **Timeout** | Check firewall on NAS/router |
| **Connection refused** | SSH service not running |
| **Permission denied (publickey)** | Use password auth or fix keys |
| **Password incorrect** | Verify: UGrinFr0g!n |
| **Host key verification failed** | Remove old key: `ssh-keygen -R 192.168.50.171` |

---

## Recommended Approach for Now

**Use SMB (Solution 1)** - It's the fastest and most reliable:

1. **On MacBook Finder**: ⌘K → `smb://192.168.50.171`
2. **Login**: Davrine / UGrinFr0g!n
3. **Navigate**: docker/greenfrog-rag/data/scraped/
4. **Drag**: ~/Documents/matchainitiative folder

---

## After Transfer - Verify

Run this on NAS:

```bash
# Check if files arrived
ls -la /volume1/docker/greenfrog-rag/data/scraped/matchainitiative/

# Count files
find /volume1/docker/greenfrog-rag/data/scraped/matchainitiative/ -type f | wc -l

# Check size
du -sh /volume1/docker/greenfrog-rag/data/scraped/matchainitiative/
```

---

## Next Steps After Transfer

Once the content is on the NAS, we'll:

1. ✅ Parse the local matchainitiative data
2. ✅ Import into ChromaDB via AnythingLLM
3. ✅ Set up incremental sync scraper (for future updates)

Let me know which method you'd like to use!
