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
                decode_responses=True
            )
        else:
            client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True
            )

        # test connection
        client.ping()
        print("✅ Redis connected")

        return client

    except Exception as e:
        print("❌ Redis connection failed:", e)
        return None


# =========================
# GLOBAL CLIENT
# =========================
redis_client = get_redis()