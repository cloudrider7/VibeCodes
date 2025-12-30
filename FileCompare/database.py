import sqlite3
import os
from typing import List, Tuple, Optional

class DatabaseManager:
    def __init__(self, db_path: str = "file_index.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Optimize SQLite for speed
        c.execute("PRAGMA journal_mode=WAL;")
        c.execute("PRAGMA synchronous=NORMAL;")
        
        # File Table
        # partial_hash and full_hash can be NULL initially
        c.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                size INTEGER NOT NULL,
                mtime REAL,
                partial_hash TEXT,
                full_hash TEXT,
                extension TEXT
            )
        ''')
        
        # Index on size for fast initial grouping
        c.execute("CREATE INDEX IF NOT EXISTS idx_size ON files(size)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_partial ON files(partial_hash)")
        
        conn.commit()
        conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def insert_file(self, path: str, size: int, mtime: float, extension: str):
        conn = self.get_connection()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO files (path, size, mtime, extension) VALUES (?, ?, ?, ?)",
                (path, size, mtime, extension)
            )
            conn.commit()
        except sqlite3.Error as e:
            print(f"DB Insert Error: {e}")
        finally:
            conn.close()

    def update_partial_hash(self, path: str, p_hash: str):
        conn = self.get_connection()
        conn.execute("UPDATE files SET partial_hash = ? WHERE path = ?", (p_hash, path))
        conn.commit()
        conn.close()

    def update_full_hash(self, path: str, f_hash: str):
        conn = self.get_connection()
        conn.execute("UPDATE files SET full_hash = ? WHERE path = ?", (f_hash, path))
        conn.commit()
        conn.close()

    def get_files_by_size(self, min_size: int = 0) -> List[Tuple]:
        """Returns files that share the same size (potential duplicates)"""
        conn = self.get_connection()
        c = conn.cursor()
        # Find sizes that appear more than once
        query = '''
            SELECT * FROM files WHERE size IN (
                SELECT size FROM files 
                WHERE size > ?
                GROUP BY size 
                HAVING COUNT(*) > 1
            )
            ORDER BY size DESC
        '''
        c.execute(query, (min_size,))
        results = c.fetchall()
        conn.close()
        return results

    def get_files_for_full_scan(self) -> List[Tuple]:
        """Returns files that share size AND partial hash (high probability duplicates)"""
        conn = self.get_connection()
        c = conn.cursor()
        query = '''
            SELECT * FROM files WHERE partial_hash IS NOT NULL AND partial_hash IN (
                SELECT partial_hash FROM files 
                WHERE partial_hash IS NOT NULL
                GROUP BY partial_hash 
                HAVING COUNT(*) > 1
            )
            ORDER BY size DESC
        '''
        c.execute(query)
        results = c.fetchall()
        conn.close()
        return results

    def get_final_duplicates(self) -> List[Tuple]:
        """Returns files that have identical FULL hashes (confirmed duplicates)"""
        conn = self.get_connection()
        c = conn.cursor()
        # Group by full_hash
        query = '''
            SELECT full_hash, size, path, mtime FROM files 
            WHERE full_hash IS NOT NULL AND full_hash IN (
                SELECT full_hash FROM files
                WHERE full_hash IS NOT NULL
                GROUP BY full_hash
                HAVING COUNT(*) > 1
            )
            ORDER BY size DESC, full_hash
        '''
        c.execute(query)
        results = c.fetchall()
        conn.close()
        return results

    def clear_db(self):
        conn = self.get_connection()
        try:
            conn.execute("DELETE FROM files")
            conn.commit()
        finally:
            conn.close()
