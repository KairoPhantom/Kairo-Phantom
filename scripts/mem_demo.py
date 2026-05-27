import os
import sqlite3
import sys
import uuid
import time
from pathlib import Path

# Enforce clean package imports to sidecar
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

try:
    from kairo_sidecar.sidecar.embeddings import embed_text
except ImportError:
    # Minimal fallback hashing same as Rust not(feature = "local-embeddings")
    import hashlib
    def embed_text(text: str) -> list[float]:
        vec = [0.0] * 256
        for i in range(256):
            h = hashlib.md5(f"{text}_{i}".encode("utf-8")).digest()
            val = int.from_bytes(h[:4], "big") / 4294967295.0
            vec[i] = val * 2.0 - 1.0
        norm = sum(x * x for x in vec) ** 0.5
        return [x / max(norm, 1e-9) for x in vec]

def get_db_path() -> Path:
    home = Path.home()
    kairo_dir = home / ".kairo-phantom"
    kairo_dir.mkdir(parents=True, exist_ok=True)
    return kairo_dir / "mem_machine.db"

def seed_session_1(db_path: Path):
    print("=== SESSION 1: Seeding preference signals into MemMachine ===")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Initialize schema in case it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_memory (
            id TEXT PRIMARY KEY,
            timestamp INTEGER,
            content TEXT,
            full_episode TEXT,
            embedding BLOB,
            app_context TEXT,
            context_key TEXT,
            is_ground_truth INTEGER DEFAULT 0,
            storage_strength REAL DEFAULT 1.0,
            retrieval_strength REAL DEFAULT 1.0,
            tags TEXT
        )
    """)
    
    preferences = [
        {
            "content": "User prefers high-contrast dark color palettes with deep slate background (#020617) for RevealJS presentation slides.",
            "app_context": "revealjs",
            "context_key": "revealjs",
            "tags": "style,revealjs"
        },
        {
            "content": "User enforces strict PowerPoint rules: slide bullet lengths must be concise and limited to <= 5 words.",
            "app_context": "powerpnt",
            "context_key": "pptx",
            "tags": "format,pptx"
        },
        {
            "content": "User requests precise technical terminology and sans-serif typography stacks (Inter/Plus Jakarta Sans) for Word document templates.",
            "app_context": "winword",
            "context_key": "docx",
            "tags": "layout,docx"
        }
    ]
    
    import pickle
    for pref in preferences:
        # Check if already seeded to prevent duplicates
        cursor.execute("SELECT id FROM semantic_memory WHERE content = ?", (pref["content"],))
        if cursor.fetchone():
            print(f"Skipping duplicate seed: {pref['content'][:50]}...")
            continue
            
        mem_id = str(uuid.uuid4())
        timestamp = int(time.time())
        vec = embed_text(pref["content"])
        # Serialize float vector as binary blob using pickle/bincode-equivalent format
        # In rusqlite bincode format, serialize/deserialize matches bincode crate.
        # But we can write raw float list serialized to binary (bincode uses flat little endian floats)
        import struct
        embedding_blob = struct.pack(f"<{len(vec)}f", *vec)
        
        cursor.execute("""
            INSERT INTO semantic_memory (id, timestamp, content, full_episode, embedding, app_context, context_key, is_ground_truth, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (mem_id, timestamp, pref["content"], "", embedding_blob, pref["app_context"], pref["context_key"], 1, pref["tags"]))
        print(f"Seeded: '{pref['content'][:60]}...'")
        
    conn.commit()
    conn.close()
    print("Session 1 Seeding Complete.\n")

def simulate_session_2(db_path: Path):
    print("=== SESSION 2: Demonstrating recall under contextual queries ===")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Query matching PPTX context key
    cursor.execute("""
        SELECT content, app_context, tags 
        FROM semantic_memory 
        WHERE context_key = 'pptx'
        ORDER BY storage_strength DESC, timestamp DESC
        LIMIT 1
    """)
    res = cursor.fetchone()
    if res:
        print("Recall PPTX rule:")
        print(f"  -> App Context: {res[1]}")
        print(f"  -> Content: {res[0]}")
        print(f"  -> Tags: {res[2]}\n")
    else:
        print("No PPTX rule recalled!\n")
        
    # Query matching RevealJS style preference
    cursor.execute("""
        SELECT content, app_context, tags 
        FROM semantic_memory 
        WHERE context_key = 'revealjs'
        ORDER BY storage_strength DESC, timestamp DESC
        LIMIT 1
    """)
    res = cursor.fetchone()
    if res:
        print("Recall RevealJS style preference:")
        print(f"  -> App Context: {res[1]}")
        print(f"  -> Content: {res[0]}")
        print(f"  -> Tags: {res[2]}\n")
    else:
        print("No RevealJS preference recalled!\n")
        
    conn.close()
    print("Session 2 Recall Verification Complete.")

if __name__ == "__main__":
    db = get_db_path()
    seed_session_1(db)
    simulate_session_2(db)
