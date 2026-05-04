import os
import redis


# =========================
# CREATE REDIS CLIENT
# =========================
def get_redis():
    redis_url = os.getenv("REDIS_URL")

    try:
        if redis_url:
            client = redis.from_url(
                redis_url,
                socket_timeout=3,
                socket_connect_timeout=3,
                retry_on_timeout=True
            )
        else:
            client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                socket_timeout=3,
                socket_connect_timeout=3,
                retry_on_timeout=True
            )

        # =========================
        # TEST CONNECTION
        # =========================
        client.ping()
        print("✅ Redis connected")

        return client

    except Exception as e:
        print("❌ Redis connection failed")
        print("   ↳ detail:", e)
        print("   ↳ url:", redis_url)

        return None


# =========================
# SAFE GET
# =========================
def redis_get(key: str):
    if not redis_client:
        return None

    try:
        value = redis_client.get(key)
        return value.decode() if value else None
    except Exception as e:
        print(f"❌ Redis GET error ({key}):", e)
        return None


# =========================
# SAFE SET
# =========================
def redis_set(key: str, value: str, ex: int = 3600):
    if not redis_client:
        return

    try:
        redis_client.set(key, value, ex=ex)
    except Exception as e:
        print(f"❌ Redis SET error ({key}):", e)


# =========================
# GLOBAL CLIENT
# =========================
redis_client = get_redis()