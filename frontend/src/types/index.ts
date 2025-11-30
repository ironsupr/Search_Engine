export interface SearchResult {
  title: string;
  url: string;
  content: string;
  score: number;
  pagerank?: number;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  page: number;
  size: number;
  time: number;
}
