export interface SearchResult {
  title: string;
  url: string;
  description: string;
  snippet: string;
  score: number;
  crawled_at?: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
  took_ms: number;
  cached: boolean;
}
