import os
import time
import hashlib
import xxhash
import threading
from abc import ABC, abstractmethod
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import blake3

class HashStrategy(ABC):
    def __init__(self, digest_size: int = 32):
        self.digest_size = digest_size # in bytes

    @abstractmethod
    def get_name(self) -> str:
        pass
        
    @abstractmethod
    def hash_content(self, data: bytes) -> str:
        pass
        
    @abstractmethod
    def get_hasher(self):
        """Returns a hasher object with update() method"""
        pass

    @abstractmethod
    def finalize(self, hasher) -> str:
        """Returns hexdigest from hasher"""
        pass

class XXHashStrategy(HashStrategy):
    def get_name(self) -> str:
        return "xxhash"
        
    def hash_content(self, data: bytes) -> str:
        return xxhash.xxh64(data).hexdigest()
        
    def get_hasher(self):
        return xxhash.xxh64()
    
    def finalize(self, hasher) -> str:
        return hasher.hexdigest()

class Blake3Strategy(HashStrategy):
    def get_name(self) -> str:
        return "blake3"
        
    def hash_content(self, data: bytes) -> str:
        # blake3 supports variable length via length arg (default 32)
        return blake3.blake3(data).hexdigest(length=self.digest_size)
        
    def get_hasher(self):
        return blake3.blake3()
    
    def finalize(self, hasher) -> str:
        return hasher.hexdigest(length=self.digest_size)

class Shake128Strategy(HashStrategy):
    def get_name(self) -> str:
        return "shake_128"
        
    def hash_content(self, data: bytes) -> str:
        return hashlib.shake_128(data).hexdigest(self.digest_size)
    
    def get_hasher(self):
        return hashlib.shake_128()
    
    def finalize(self, hasher) -> str:
        return hasher.hexdigest(self.digest_size)

class SHA256Strategy(HashStrategy):
    def get_name(self) -> str:
        return "sha256"
        
    def hash_content(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()
        
    def get_hasher(self):
        return hashlib.sha256()
    
    def finalize(self, hasher) -> str:
        return hasher.hexdigest()

class ScannerEngine:
    def __init__(self, hash_strategy: HashStrategy = XXHashStrategy()):
        self.strategy = hash_strategy
        self.stop_event = threading.Event()

    def set_strategy(self, strategy: HashStrategy):
        self.strategy = strategy

    def get_partial_hash(self, file_path: str, chunk_size: int = 4096) -> str:
        """
        Reads first and last chunks of the file.
        Returns a combined hash of both chunks.
        """
        try:
            file_size = os.path.getsize(file_path)
            with open(file_path, "rb") as f:
                # Read head
                head_data = f.read(chunk_size)
                
                # Read tail if file is larger than chunk
                if file_size > chunk_size:
                    f.seek(max(0, file_size - chunk_size))
                    tail_data = f.read(chunk_size)
                else:
                    tail_data = b""
                
                # Combine and hash
                combined = head_data + tail_data
                return self.strategy.hash_content(combined)
        except OSError:
            return ""

    def get_full_hash(self, file_path: str, buffer_size: int = 65536) -> str:
        hasher = self.strategy.get_hasher()
        try:
            with open(file_path, "rb") as f:
                while True:
                    if self.stop_event.is_set():
                        return ""
                    chunk = f.read(buffer_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return self.strategy.finalize(hasher)
        except OSError:
            return ""

    def stop(self):
        self.stop_event.set()

class FileScanner:
    def __init__(self, db_manager, hash_strategy: HashStrategy = XXHashStrategy(), num_workers: int = 4, on_progress=None):
        self.db = db_manager
        self.hasher = ScannerEngine(hash_strategy)
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        self.lock = threading.Lock()
        self.scanned_count = 0
        self.duplicate_count = 0
        self.running = False
        self.on_progress = on_progress
        self.last_update = 0
        
        # Filters
        self.ignore_folders = set()
        self.ignore_extensions = set()
        self.min_file_size = 0
        
    def configure_filters(self, ignore_folders: list, ignore_extensions: list, min_file_size: int):
        self.ignore_folders = set(os.path.normpath(p) for p in ignore_folders)
        self.ignore_extensions = set(e.lower() for e in ignore_extensions)
        self.min_file_size = min_file_size
    
    def scan_roots(self, root_paths: list[str], is_spinning_disk: bool = False):
        """
        Scans multiple root directories.
        If is_spinning_disk is True, we should strictly serialise the I/O or limit workers.
        """
        self.running = True
        
        # Adaptive Threading
        # If HDD/Network, use 1 or 2 workers max for Scanning phase to reduce seeking?
        # Actually proper traversal on HDD is single-threaded DFS. 
        # But Hashing can be parallel if read sequentially?
        # The user requested "Explicitly deny multithreading".
        
        original_workers = self.executor._max_workers
        
        if is_spinning_disk:
            # We can't easily resize ThreadPoolExecutor, so we rely on how we submit tasks.
            # But for simplicity, if HDD, we might just run synchronously or use a semaphore?
            # Creating a new executor is cleaner logic, but let's stick to the pool 
            # and just throttle submission if we wanted.
            # User requirement: "Deny multithreading".
            # so we essentially want 1 thread.
            # HDD/Network Mode: Forcing sequential execution to prevent thrashing.
            pass


        
        for root in root_paths:
            if not self.running: break
            self._recursive_scan(root)
            
    def _recursive_scan(self, path):
        try:
             with os.scandir(path) as it:
                for entry in it:
                    if not self.running: break
                    
                    if entry.is_dir(follow_symlinks=False):
                        if os.path.normpath(entry.path) in self.ignore_folders:
                            continue
                        self._recursive_scan(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        try:
                            # Extension Filter
                            ext = os.path.splitext(entry.name)[1].lower()
                            if ext in self.ignore_extensions:
                                continue
                                
                            stat = entry.stat()
                            # Min Size Filter (always skip empty files)
                            if stat.st_size > 0 and stat.st_size >= self.min_file_size:
                                self.db.insert_file(
                                    path=entry.path, 
                                    size=stat.st_size, 
                                    mtime=stat.st_mtime, 
                                    extension=ext
                                )
                                self.scanned_count += 1
                                current_time = time.time()
                                if self.on_progress and (current_time - self.last_update > 0.05):
                                    self.on_progress("scanned", self.scanned_count)
                                    self.last_update = current_time
                        except OSError:
                            continue
        except OSError:
            pass

    def process_duplicates(self, force_single_thread: bool = False):
        """Executes Stage 2 and 3 of deduplication"""
        
        # Stage 2: Partial Hash
        size_dupes = self.db.get_files_by_size()
        total_partial = len(size_dupes)
        completed_partial = 0
        
        futures = []
        
        for file_record in size_dupes:
            if not self.running: break
            path = file_record[1]
            
            if force_single_thread:
                # Run inline
                self._compute_partial(path)
                completed_partial += 1
                self._report_progress("hashing_partial", completed_partial, total_partial)
            else:
                f = self.executor.submit(self._compute_partial, path)
                futures.append(f)
            
        if not force_single_thread:
            for f in futures:
                if not self.running: break
                f.result()
                completed_partial += 1
                self._report_progress("hashing_partial", completed_partial, total_partial)
            
        # Stage 3: Full Hash
        partial_dupes = self.db.get_files_for_full_scan()
        total_full = len(partial_dupes)
        completed_full = 0
        futures = []
        
        for file_record in partial_dupes:
            if not self.running: break
            path = file_record[1]
            
            if force_single_thread:
                self._compute_full(path)
                completed_full += 1
                self._report_progress("hashing_full", completed_full, total_full)
            else:
                f = self.executor.submit(self._compute_full, path)
                futures.append(f)
                
        if not force_single_thread:
            for f in futures:
                if not self.running: break
                f.result()
                completed_full += 1
                self._report_progress("hashing_full", completed_full, total_full)
            
            
        # print("Scan complete.") # Removed to prevent terminal blocking

    def _report_progress(self, stage, current, total):
        current_time = time.time()
        # Update at most 20Hz or if complete
        time.sleep(0.001) # Yield to UI thread
        if self.on_progress and (current_time - self.last_update > 0.05 or current == total):
            self.on_progress(stage, (current, total))
            self.last_update = current_time

    def _compute_partial(self, path):
        p_hash = self.hasher.get_partial_hash(path)
        if p_hash:
            self.db.update_partial_hash(path, p_hash)

    def _compute_full(self, path):
        f_hash = self.hasher.get_full_hash(path)
        if f_hash:
            self.db.update_full_hash(path, f_hash)

    def get_duplicates(self):
        return self.db.get_final_duplicates()
