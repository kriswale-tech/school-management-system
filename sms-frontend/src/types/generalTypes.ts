export type PaginatedResponse<T> = {
    count: number;
    page_count: number;
    page: number;
    page_size: number;
    total_pages: number;
    start_index: number;
    end_index: number;
    has_next: boolean;
    has_previous: boolean;
    next: string | null;
    previous: string | null;
    results: T[];
  };
  