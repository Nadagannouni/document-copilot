import os


os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@example.supabase.co:5432/postgres")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
os.environ.setdefault("OPENAI_EMBEDDING_DIMENSIONS", "1536")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:5173")
