import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///local.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER") or ("/tmp/uploads" if os.getenv("VERCEL") else "/data/uploads")
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(20 * 1024 * 1024)))
    GANACHE_HOST = os.getenv("GANACHE_HOST")
    GANACHE_PORT = os.getenv("GANACHE_PORT")
    WEB3_PROVIDER = os.getenv("WEB3_PROVIDER")
    CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

    @staticmethod
    def build_web3_provider():
        p = os.getenv("WEB3_PROVIDER")
        if p:
            return p
        h = os.getenv("GANACHE_HOST")
        r = os.getenv("GANACHE_PORT")
        if h and r:
            return f"http://{h}:{r}"
        return os.getenv("HTTP_PROVIDER", "http://127.0.0.1:8545")
