# Redis Configuration Guide

## Tổng quan

ResSynt sử dụng Redis cho 3 mục đích chính:
1. **Cache** - Lưu trữ tạm thời để tăng tốc độ truy vấn
2. **Celery Broker** - Message queue cho async tasks
3. **Celery Result Backend** - Lưu kết quả của async tasks

---

## 🔧 Cài đặt Redis

### Windows (Development)

**Cách 1: WSL2 (Khuyến nghị)**
```bash
# Trong WSL2 Ubuntu
sudo apt update
sudo apt install redis-server
sudo service redis-server start
redis-cli ping  # Should return PONG
```

**Cách 2: Docker**
```bash
docker run -d --name redis -p 6379:6379 redis:alpine
```

**Cách 3: Memurai (Native Windows)**
- Download từ: https://www.memurai.com/
- Install và chạy như Windows service

### Linux (Production)
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Kiểm tra Redis hoạt động
```bash
redis-cli ping
# Output: PONG

redis-cli info | grep used_memory_human
# Output: used_memory_human:1.23M
```

---

## ⚙️ Cấu hình Environment Variables

### File `.env`

```dotenv
# =============================================================================
# REDIS & CELERY
# =============================================================================
# Dev: có thể để trống (sẽ dùng LocMemCache)
# Prod: BẮT BUỘC phải có

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

### Giải thích Redis Database Numbers
- `redis://localhost:6379/0` → Database 0: Django Cache
- `redis://localhost:6379/1` → Database 1: Celery Broker (message queue)
- `redis://localhost:6379/2` → Database 2: Celery Result Backend

> **Lưu ý**: Redis mặc định có 16 databases (0-15), có thể tăng trong `redis.conf`

---

## 🔄 So sánh Development vs Production

| Tính năng | Development (`dev.py`) | Production (`prod.py`) |
|-----------|------------------------|------------------------|
| **Cache Backend** | `LocMemCache` (in-memory) | `RedisCache` |
| **Redis Required** | ❌ Không cần | ✅ Bắt buộc |
| **Celery Mode** | `ALWAYS_EAGER=True` (sync) | `ALWAYS_EAGER=False` (async) |
| **Session Storage** | Database | Database (có thể Redis) |
| **Performance** | Nhanh (không network) | Tối ưu (shared cache) |

---

## 📁 Chi tiết cấu hình theo môi trường

### Development (`config/settings/dev.py`)

```python
# CACHE (Force LocMemCache in dev - SKIP Redis for speed)
# Override base.py cache config to avoid Redis connection delays
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "resync-dev-cache",
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        }
    }
}
```

**Ưu điểm:**
- Không cần cài Redis
- Khởi động nhanh (không có network delay)
- Đơn giản cho debugging

**Hạn chế:**
- Cache không share giữa processes
- Cache mất khi restart server

---

### Production (`config/settings/prod.py`)

```python
# CACHE (Redis - Required)
redis_url = env("REDIS_URL", default=None)

if redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "KEY_PREFIX": "cache",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,  # Graceful degradation
                "CONNECTION_POOL_CLASS_KWARGS": {
                    "max_connections": 50,
                    "timeout": 20,
                },
            },
        },
        "sessions": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_url,
            "KEY_PREFIX": "session",
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
            },
        },
    }
    SESSION_CACHE_ALIAS = "sessions"
```

**Ưu điểm:**
- Cache shared giữa tất cả workers
- Persistent (không mất khi restart app)
- Tốc độ cao (in-memory)
- Hỗ trợ clustering

---

## 🚀 Celery Configuration

### Development (Eager Mode - No Redis needed)

```python
# config/settings/base.py
CELERY_TASK_ALWAYS_EAGER = True      # Chạy task đồng bộ
CELERY_TASK_EAGER_PROPAGATES = True  # Propagate exceptions
```

Task được thực thi ngay lập tức trong process hiện tại, không cần Redis broker.

### Production (Async Mode - Redis required)

```python
# config/settings/prod.py
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
CELERY_BROKER_URL = env("CELERY_BROKER_URL")      # redis://localhost:6379/1
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")  # redis://localhost:6379/2
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_POOL_LIMIT = 10
CELERY_RESULT_EXPIRES = 3600  # 1 hour
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
```

**Khởi động Celery worker:**
```bash
# Terminal 1: Celery worker
celery -A config worker -l INFO

# Terminal 2: Celery beat (scheduler - optional)
celery -A config beat -l INFO
```

---

## 🔍 Debug Redis Issues

### Kiểm tra kết nối
```python
# Django shell
python manage.py shell

from django.core.cache import cache
cache.set('test_key', 'test_value', 60)
print(cache.get('test_key'))  # Should print: test_value
```

### Xem Redis logs
```bash
# Linux
sudo tail -f /var/log/redis/redis-server.log

# Docker
docker logs -f redis
```

### Monitor Redis real-time
```bash
redis-cli monitor
```

### Xem cache stats
```bash
redis-cli info stats
redis-cli info memory
```

### Clear all cache
```bash
redis-cli FLUSHDB      # Clear current database
redis-cli FLUSHALL     # Clear ALL databases (careful!)
```

---

## ⚡ Performance Tuning

### Redis Config (`/etc/redis/redis.conf`)

```conf
# Memory limit
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence (disable for pure cache)
save ""
appendonly no

# Network
tcp-keepalive 300
timeout 0

# Performance
tcp-backlog 511
```

### Django Settings tối ưu

```python
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "IGNORE_EXCEPTIONS": True,
            "SOCKET_CONNECT_TIMEOUT": 2,  # Fast fail
            "SOCKET_TIMEOUT": 2,
            "CONNECTION_POOL_CLASS_KWARGS": {
                "max_connections": 50,
                "timeout": 2,
            },
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",  # Compress large values
        },
    }
}
```

---

## 🛡️ Security (Production)

### Redis Authentication
```conf
# redis.conf
requirepass your_strong_password_here
```

```dotenv
# .env
REDIS_URL=redis://:your_strong_password_here@localhost:6379/0
```

### Bind to localhost only
```conf
# redis.conf
bind 127.0.0.1
protected-mode yes
```

### Disable dangerous commands
```conf
# redis.conf
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command DEBUG ""
rename-command CONFIG ""
```

---

## 📊 Khi nào cần Redis?

| Scenario | Redis cần không? |
|----------|------------------|
| Development local | ❌ Không (dùng LocMemCache) |
| Testing CI/CD | ❌ Không (dùng LocMemCache) |
| Single server production | ✅ Có (shared cache) |
| Multi-server production | ✅ Bắt buộc (distributed cache) |
| Background tasks (Celery) | ✅ Bắt buộc (broker) |
| Real-time features | ✅ Bắt buộc (pub/sub) |

---

## 🔧 Quick Troubleshooting

| Vấn đề | Nguyên nhân | Giải pháp |
|--------|-------------|-----------|
| Server chậm khi dev | Redis timeout (không chạy) | Dùng `dev.py` settings |
| Cache không hoạt động | REDIS_URL sai | Kiểm tra `.env` |
| Celery task không chạy | Broker không kết nối | Kiểm tra Redis running |
| Connection refused | Redis không chạy | `sudo service redis-server start` |
| Memory full | Không set maxmemory | Set `maxmemory 256mb` |

---

## 📝 Checklist

### Development
- [ ] Sử dụng `DJANGO_ENV=dev`
- [ ] Không cần cài Redis
- [ ] Cache dùng LocMemCache tự động

### Production
- [ ] Redis server đang chạy
- [ ] `.env` có `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- [ ] Redis có password (nếu public)
- [ ] Redis bind localhost only
- [ ] Celery worker đang chạy
- [ ] Monitor Redis memory usage
