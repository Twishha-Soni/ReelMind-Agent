# Chunking
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_RESULTS = 3

# Models
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
VIDEO_ANALYSIS_MODEL = "models/gemini-2.5-flash"
ANSWER_FORMAT_MODEL = "models/gemini-3.1-flash-lite"

# Rate limiting (seconds between Gemini calls during bulk onboarding)
RATE_LIMIT_DELAY = 30