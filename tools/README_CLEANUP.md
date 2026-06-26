# C

## 

### 1: 

```bash
python tools/cleanup_c_drive_quick.py
```

****:
- ，
- 
- 

### 2: 

```bash
# 
python tools/cleanup_c_drive.py --dry-run

# 
python tools/cleanup_c_drive.py

# 
python tools/cleanup_c_drive.py --all
```

## 

|  |  |  |  |
|------|------|------|------|
| `--temp` | Windows | ✅  |  |
| `--python-cache` | Python | ✅  |  |
| `--old-logs` | 30 | ✅  |  |
| `--browser-cache` |  | ❌  |  |
| `--old-downloads` | 90 | ❌  |  |

## 

### 1: 
```bash
python tools/cleanup_c_drive.py --temp
```

### 2: Python
```bash
python tools/cleanup_c_drive.py --temp --python-cache
```

### 3: 
```bash
python tools/cleanup_c_drive.py --all --dry-run
```

### 4: 
```bash
python tools/cleanup_c_drive.py --all
```

## 

⚠️ ****:
1.  `--dry-run` 
2. `--browser-cache` ，
3. `--old-downloads` ，
4. 

## 

### 
- ✅ Windows（TEMP）
- ✅ Python（__pycache__, .pyc）
- ✅ （30）

### 
- ⚠️ （Chrome, Edge, Firefox）
- ⚠️ （90）

## 

 `cleanup_log.txt`，：
- 
- 
- 

## 

**Q: ？**  
A: ，。

**Q: ？**  
A: ，。

**Q: ？**  
A: ，。

**Q: ？**  
A: C，。

## 

， `cleanup_log.txt` 。

















