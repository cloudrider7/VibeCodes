import time
import os
import hashlib
import multiprocessing
import platform
import xxhash
import blake3
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

@dataclass
class SystemProfile:
    cpu_count: int
    recommended_workers: int
    recommended_algo: str
    benchmark_score: float  # MB/s
    scores: dict = None
    reasoning: str = ""
    
    @staticmethod
    def get_context(algo: str, score: float, bit_length: int = 256) -> dict:
        """Returns dict with keys: 'prefix', 'interactive', 'tooltip'"""
        # GB/s conversion
        gb_s = score / 1024.0
        # Unified Prefix Format
        prefix = f"{algo} rated for {gb_s:.1f} GB/s ({bit_length}-bit). "
        interactive = ""
        tooltip = ""
        
        suffix = " chance of collision."
        
        if algo == "xxhash":
            suitability = "Suitable for up to 1 million files with "
            probability = "a 1 in 10 million"
            tooltip = "1 in 10,000,000"
            
        elif algo in ["blake3", "sha256", "shake_128"]:
            if bit_length == 128:
                # Birthday bound 2^64 ~ 1.8e19
                suitability = "Suitable for up to 18 Quintillion files with "
                probability = "a 1 in 340 Undecillion"
                tooltip = "1 in 340,282,366,920,938,463,463,374,607,431,768,211,456 (38 zeros)"
            elif bit_length == 512:
                 # Birthday bound 2^256 ~ 1e77
                 suitability = "Suitable for up to 100 Quattuorvigintillion files with "
                 probability = "a 1 in 10^154"
                 tooltip = "1 in 1.3 Quinquagintillion (that's 154 zeroes!)"
            else:
                # 256-bit standard. Birthday bound 2^128 ~ 3.4e38
                suitability = "Suitable for up to 340 Undecillion files with "
                probability = "a 1 in 10^77"
                tooltip = "1 in 100 Quattuorvigintillion (77 zeroes!)"
             
        # Fallback
        if not suitability:
             suitability = "Suitable for general use. "
             probability = "Standard collision resistance"
             suffix = "."
             tooltip = "Standard"

        return {
            "prefix": prefix,
            "suitability": suitability,
            "probability": probability,
            "suffix": suffix,
            "tooltip": tooltip
        }

class Profiler:
    def __init__(self):
        self.chunk_size = 100 * 1024 * 1024  # 100 MB test chunk

    def _benchmark_algo(self, algo_name: str, data: bytes, length: int = 32) -> float:
        """Returns MB/s for a given algorithm and output length (in bytes)."""
        start_time = time.time()
        if algo_name == "xxhash":
            xxhash.xxh64(data).hexdigest()
        elif algo_name == "blake3":
            blake3.blake3(data).hexdigest(length=length)
        elif algo_name == "sha256":
            hashlib.sha256(data).hexdigest()
        elif algo_name == "shake_128":
            hashlib.shake_128(data).hexdigest(length)
            
        end_time = time.time()
        
        duration = end_time - start_time
        if duration == 0: return 99999.0 # unexpected fast
        
        md_size = len(data) / (1024 * 1024)
        return md_size / duration

    def run_benchmark(self, enabled: bool = True) -> SystemProfile:
        cpu_count = multiprocessing.cpu_count()
        # Conservative worker count
        workers = max(1, cpu_count - 1)
        if cpu_count > 8:
            workers = cpu_count - 2
            
        if not enabled:
            return SystemProfile(
                cpu_count=cpu_count,
                recommended_workers=workers,
                recommended_algo="xxhash", 
                benchmark_score=0.0,
                reasoning="Benchmark disabled by user settings.",
                scores={"xxhash": 0, "blake3": 0, "sha256": 0, "shake_128": 0}
            )
            
        print("Running hardware benchmark...")
        # create random data in memory
        data = os.urandom(self.chunk_size)
        
        # Test algorithms
        scores = {}
        
        # Fixed Length Algos
        scores["xxhash"] = self._benchmark_algo("xxhash", data)
        scores["sha256"] = self._benchmark_algo("sha256", data)
        
        # Variable Length Algos (128, 256, 512 bits -> 16, 32, 64 bytes)
        for algo in ["blake3", "shake_128"]:
            for bits in [128, 256, 512]:
                byte_len = bits // 8
                score = self._benchmark_algo(algo, data, length=byte_len)
                scores[f"{algo}_{bits}"] = score
                
                # Set 'standard' 256-bit score as the base key for compatibility
                if bits == 256:
                    scores[algo] = score
            
        print(f"Benchmark Results (MB/s): {scores}")
        
        # Determine recommendation
        best_algo = max(scores, key=scores.get)
        best_score = scores[best_algo]
        
        # Initial reasoning for recommended
        initial_ctx = SystemProfile.get_context(best_algo.split('_')[0], best_score)
        initial_reasoning = initial_ctx["prefix"] + initial_ctx["suitability"] + initial_ctx["probability"] + initial_ctx["suffix"]
        
        return SystemProfile(
            cpu_count=cpu_count,
            recommended_workers=workers,
            recommended_algo=best_algo.split('_')[0],
            benchmark_score=best_score,
            reasoning=initial_reasoning,
            scores=scores
        )
            
    def hydrate_profile(self, scores: dict, recommended: str = None) -> SystemProfile:
        """Creates a profile from stored scores without running benchmarks."""
        cpu_count = multiprocessing.cpu_count()
        workers = max(1, cpu_count - 1)
        if cpu_count > 8:
            workers = cpu_count - 2
            
        if not scores:
            scores = {"xxhash": 0, "blake3": 0, "sha256": 0, "shake_128": 0}
            
        best_algo = recommended
        if not best_algo:
             # Recalculate if missing
             try:
                best_algo = max(scores, key=lambda k: scores[k] if isinstance(scores[k], (int, float)) else 0)
             except ValueError:
                best_algo = "xxhash"
                
        # Get base score (handling the bit-length keys if present)
        # We need the score for the *recommended* algo to generate context
        best_score = scores.get(best_algo, 0)
        
        # Initial reasoning
        initial_ctx = SystemProfile.get_context(best_algo.split('_')[0], best_score)
        initial_reasoning = initial_ctx["prefix"] + initial_ctx["suitability"] + initial_ctx["probability"] + initial_ctx["suffix"]
        
        return SystemProfile(
            cpu_count=cpu_count,
            recommended_workers=workers,
            recommended_algo=best_algo.split('_')[0], # Ensure clean name
            benchmark_score=best_score,
            reasoning=initial_reasoning,
            scores=scores
        )

class DriveDetector:
    @staticmethod
    def get_drive_type(path: str) -> str:
        """
        Returns 'SSD', 'HDD', 'mSATA' (treat as SSD), 'Network', or 'Unknown'.
        """
        abs_path = os.path.abspath(path)
        
        # Network Share Detection
        if abs_path.startswith(r"\\"):
            return "Network"
            
        drive_letter = os.path.splitdrive(abs_path)[0].upper() # "C:"
        if not drive_letter:
            return "Unknown"
            
        # PoweShell Command
        # Mapping: Partition(DriveLetter) -> Disk -> PhysicalDisk -> MediaType
        # Note: This might fail on some complex setups (RAID, etc), defaulting to Unknown (safe).
        # PowerShell Command to check media type
        # Mapping: DriveLetter -> Partition -> Disk -> PhysicalDisk -> MediaType
        cmd = [
            "powershell", "-ExecutionPolicy", "Bypass", "-Command",
            f"Get-Partition -DriveLetter {drive_letter[0]} | Get-Disk | Get-PhysicalDisk | Select-Object -ExpandProperty MediaType"
        ]
        
        try:
            # Use subprocess to hide window on Windows
            import subprocess
            
            # Hide console window
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                startupinfo=startupinfo
            )
            
            output = result.stdout.strip().upper()
            
            if "SSD" in output: return "SSD"
            if "HDD" in output: return "HDD"
            # Some returns might be integers 4 (SSD) / 3 (HDD) if newer PS version
            if output == "4": return "SSD"
            if output == "3": return "HDD"
            
        except Exception:
            pass
            
        return "Unknown"

if __name__ == "__main__":
    p = Profiler()
    profile = p.run_benchmark()
    print(profile)
    
    # Test Detector
    print(f"C: Drive Type: {DriveDetector.get_drive_type('C:')}")

