"""
PageRank Computation Service

Implements the PageRank algorithm for ranking pages by authority.
Runs as a batch job (e.g., daily via cron/Kubernetes CronJob).

Features:
- Efficient sparse matrix computation with scipy
- Handles dangling nodes
- Stores results in Redis for fast lookup
- Logs computation stats
"""

import numpy as np
from scipy.sparse import csr_matrix, lil_matrix
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import settings
from shared.database import redis_manager, db_manager
from shared.utils import url_to_hash


class PageRankComputer:
    """
    Computes PageRank scores using power iteration method
    
    Algorithm:
    PR(u) = (1-d)/N + d * Σ PR(v) / L(v)
    
    Where:
    - d = damping factor (0.85)
    - N = total number of pages
    - L(v) = number of outbound links from page v
    """
    
    def __init__(self):
        self.redis = redis_manager.connect()
        
        # Configuration
        self.damping = settings.pagerank_damping
        self.iterations = settings.pagerank_iterations
        self.convergence_threshold = 1e-6
        
        # Data structures
        self.url_to_idx: Dict[str, int] = {}
        self.idx_to_url: Dict[int, str] = {}
        self.n_pages = 0
        
        # Results
        self.scores: Optional[np.ndarray] = None
        self.computation_time = 0
    
    def load_graph(self) -> Tuple[csr_matrix, int]:
        """
        Load link graph from PostgreSQL
        
        Returns:
            Tuple of (adjacency matrix, number of nodes)
        """
        print("📊 Loading link graph from database...")
        
        # Get all unique URLs (both source and target)
        with db_manager.get_cursor() as cur:
            # Get unique pages from pages table
            cur.execute("SELECT DISTINCT url FROM pages")
            pages = cur.fetchall()
            
            for idx, row in enumerate(pages):
                url = row['url']
                self.url_to_idx[url] = idx
                self.idx_to_url[idx] = url
        
        self.n_pages = len(self.url_to_idx)
        print(f"   Found {self.n_pages} pages")
        
        if self.n_pages == 0:
            return csr_matrix((0, 0)), 0
        
        # Build adjacency matrix using LIL format (efficient for construction)
        adj_matrix = lil_matrix((self.n_pages, self.n_pages), dtype=np.float32)
        
        # Load links
        with db_manager.get_cursor() as cur:
            cur.execute("""
                SELECT source_url, target_url 
                FROM links
                WHERE source_url IN (SELECT url FROM pages)
                AND target_url IN (SELECT url FROM pages)
            """)
            
            link_count = 0
            for row in cur:
                source_url = row['source_url']
                target_url = row['target_url']
                
                if source_url in self.url_to_idx and target_url in self.url_to_idx:
                    source_idx = self.url_to_idx[source_url]
                    target_idx = self.url_to_idx[target_url]
                    
                    # Link from source to target
                    # In adjacency matrix: A[target, source] = 1
                    # (column = source, row = target for transition matrix)
                    adj_matrix[target_idx, source_idx] = 1.0
                    link_count += 1
        
        print(f"   Loaded {link_count} links")
        
        # Convert to CSR format for efficient arithmetic
        return adj_matrix.tocsr(), self.n_pages
    
    def compute(self) -> np.ndarray:
        """
        Compute PageRank using power iteration
        
        Returns:
            Array of PageRank scores
        """
        start_time = time.time()
        
        # Load graph
        adj_matrix, n = self.load_graph()
        
        if n == 0:
            print("⚠️ No pages to compute PageRank for")
            return np.array([])
        
        print(f"🔄 Computing PageRank (n={n}, d={self.damping}, iterations={self.iterations})")
        
        # Calculate out-degree for each node
        out_degree = np.array(adj_matrix.sum(axis=0)).flatten()
        
        # Handle dangling nodes (nodes with no outlinks)
        dangling_nodes = np.where(out_degree == 0)[0]
        print(f"   Found {len(dangling_nodes)} dangling nodes")
        
        # Avoid division by zero
        out_degree[out_degree == 0] = 1
        
        # Create transition matrix: M = A * D^(-1)
        # Where D is diagonal matrix of out-degrees
        d_inv = 1.0 / out_degree
        
        # Normalize columns (each column sums to 1)
        # M[i,j] = A[i,j] / out_degree[j]
        transition_matrix = adj_matrix.multiply(d_inv)
        
        # Initialize PageRank vector uniformly
        rank = np.ones(n, dtype=np.float32) / n
        
        # Teleport probability
        teleport = (1 - self.damping) / n
        
        # Power iteration
        for iteration in range(self.iterations):
            prev_rank = rank.copy()
            
            # Standard PageRank update
            rank = self.damping * transition_matrix.dot(rank)
            
            # Handle dangling nodes: distribute their rank equally
            dangling_sum = self.damping * prev_rank[dangling_nodes].sum() / n
            rank += dangling_sum
            
            # Add teleportation
            rank += teleport
            
            # Check convergence
            diff = np.abs(rank - prev_rank).sum()
            
            if (iteration + 1) % 5 == 0:
                print(f"   Iteration {iteration + 1}: diff = {diff:.8f}")
            
            if diff < self.convergence_threshold:
                print(f"   ✅ Converged after {iteration + 1} iterations")
                break
        
        # Normalize scores to sum to 1
        rank = rank / rank.sum()
        
        self.scores = rank
        self.computation_time = time.time() - start_time
        
        print(f"   ⏱️ Computation time: {self.computation_time:.2f}s")
        
        return rank
    
    def store_scores(self, ttl: int = 7 * 24 * 3600):
        """
        Store PageRank scores in Redis for fast lookup
        
        Args:
            ttl: Time-to-live in seconds (default: 7 days)
        """
        if self.scores is None:
            print("⚠️ No scores to store. Run compute() first.")
            return
        
        print(f"💾 Storing {len(self.scores)} PageRank scores in Redis...")
        
        # Use pipeline for efficiency
        pipe = self.redis.pipeline()
        
        for idx, score in enumerate(self.scores):
            url = self.idx_to_url[idx]
            url_hash = url_to_hash(url)[:16]  # Use first 16 chars of hash
            
            key = f"pagerank:{url_hash}"
            pipe.setex(key, ttl, str(float(score)))
        
        pipe.execute()
        
        # Store metadata
        self.redis.hset("pagerank:meta", mapping={
            "computed_at": datetime.utcnow().isoformat(),
            "n_pages": str(self.n_pages),
            "computation_time": str(self.computation_time),
            "damping": str(self.damping),
            "iterations": str(self.iterations)
        })
        
        print("   ✅ Scores stored successfully")
    
    def store_to_postgres(self):
        """Store PageRank scores in PostgreSQL for persistence"""
        if self.scores is None:
            return
        
        print("💾 Storing PageRank scores in PostgreSQL...")
        
        with db_manager.get_cursor() as cur:
            # Clear old scores
            cur.execute("TRUNCATE TABLE pagerank_scores")
            
            # Insert new scores in batches
            batch_size = 1000
            values = []
            
            for idx, score in enumerate(self.scores):
                url = self.idx_to_url[idx]
                url_hash = url_to_hash(url)
                values.append((url_hash, url, float(score)))
                
                if len(values) >= batch_size:
                    cur.executemany(
                        "INSERT INTO pagerank_scores (url_hash, url, score) VALUES (%s, %s, %s)",
                        values
                    )
                    values = []
            
            # Insert remaining
            if values:
                cur.executemany(
                    "INSERT INTO pagerank_scores (url_hash, url, score) VALUES (%s, %s, %s)",
                    values
                )
        
        print("   ✅ Stored in PostgreSQL")
    
    def get_top_pages(self, n: int = 20) -> List[Tuple[str, float]]:
        """Get top N pages by PageRank score"""
        if self.scores is None:
            return []
        
        # Get indices of top N scores
        top_indices = np.argsort(self.scores)[-n:][::-1]
        
        results = []
        for idx in top_indices:
            url = self.idx_to_url[idx]
            score = float(self.scores[idx])
            results.append((url, score))
        
        return results
    
    def print_stats(self):
        """Print PageRank computation statistics"""
        if self.scores is None:
            print("No scores computed yet.")
            return
        
        print(f"""
╔══════════════════════════════════════════════════════╗
║              PageRank Statistics                     ║
╠══════════════════════════════════════════════════════╣
║ Total Pages:      {self.n_pages:<35} ║
║ Damping Factor:   {self.damping:<35} ║
║ Iterations:       {self.iterations:<35} ║
║ Computation Time: {self.computation_time:.2f}s{' ' * (32 - len(f'{self.computation_time:.2f}s'))} ║
╠══════════════════════════════════════════════════════╣
║ Score Statistics:                                    ║
║   Min:  {self.scores.min():.8f}{' ' * 39} ║
║   Max:  {self.scores.max():.8f}{' ' * 39} ║
║   Mean: {self.scores.mean():.8f}{' ' * 39} ║
║   Std:  {self.scores.std():.8f}{' ' * 39} ║
╚══════════════════════════════════════════════════════╝
        """)
        
        # Print top pages
        print("\n🏆 Top 10 Pages by PageRank:")
        print("-" * 70)
        for i, (url, score) in enumerate(self.get_top_pages(10), 1):
            truncated_url = url[:55] + "..." if len(url) > 55 else url
            print(f"  {i:2}. {truncated_url:<58} {score:.6f}")


def run_pagerank_job():
    """Main entry point for PageRank batch job"""
    print("""
╔══════════════════════════════════════════════════════╗
║         PageRank Batch Job Starting                  ║
╚══════════════════════════════════════════════════════╝
    """)
    
    start_time = time.time()
    
    computer = PageRankComputer()
    
    # Compute PageRank
    scores = computer.compute()
    
    if len(scores) > 0:
        # Store results
        computer.store_scores()
        computer.store_to_postgres()
        
        # Print statistics
        computer.print_stats()
    
    total_time = time.time() - start_time
    print(f"\n✅ PageRank job completed in {total_time:.2f}s")


if __name__ == "__main__":
    run_pagerank_job()
