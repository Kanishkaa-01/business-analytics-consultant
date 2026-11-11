import { describe, it, expect, vi } from 'vitest';
import { StoredAnalysisSummary, PaginatedStoredAnalysesResponse } from '../types';

/**
 * Stored Analyses Pagination & Navigation Unit Tests
 */

describe('Stored Analyses Pagination Logic and State Transitions', () => {
  // Helper for mock data
  const createMockAnalyses = (count: number): StoredAnalysisSummary[] => {
    return Array.from({ length: count }, (_, i) => ({
      id: `analysis-${i + 1}`,
      analysis_name: `Analysis Run ${i + 1}`,
      dataset_id: `ds-${i + 1}`,
      dataset_name: `Dataset ${i + 1}.csv`,
      target_column: 'Revenue',
      date_column: 'Date',
      status: 'completed',
      execution_time_ms: 120 + i * 5,
      health_score: 75 + (i % 25),
      created_at: new Date(Date.now() - i * 86400000).toISOString(),
    }));
  };

  // 1. Pagination Calculation & Range Label
  describe('Pagination Calculation & Range Display', () => {
    it('calculates correct totalPages, startIdx, and endIdx for various page sizes', () => {
      const totalCount = 47;
      const pageSize = 10;
      const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
      expect(totalPages).toBe(5);

      // Page 1
      const p1 = 1;
      const startIdx1 = (p1 - 1) * pageSize + 1;
      const endIdx1 = Math.min(totalCount, p1 * pageSize);
      expect(startIdx1).toBe(1);
      expect(endIdx1).toBe(10);

      // Page 5 (last page with remainder)
      const p5 = 5;
      const startIdx5 = (p5 - 1) * pageSize + 1;
      const endIdx5 = Math.min(totalCount, p5 * pageSize);
      expect(startIdx5).toBe(41);
      expect(endIdx5).toBe(47);
    });

    it('formats singular and plural record count labels accurately', () => {
      const formatRangeLabel = (start: number, end: number, total: number) => {
        const noun = total === 1 ? 'analysis' : 'analyses';
        return `Showing ${start}–${end} of ${total} ${noun}`;
      };

      expect(formatRangeLabel(1, 1, 1)).toBe('Showing 1–1 of 1 analysis');
      expect(formatRangeLabel(1, 10, 25)).toBe('Showing 1–10 of 25 analyses');
      expect(formatRangeLabel(21, 25, 25)).toBe('Showing 21–25 of 25 analyses');
    });

    it('handles empty datasets with 1 total page and bounds', () => {
      const totalCount = 0;
      const pageSize = 10;
      const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
      expect(totalPages).toBe(1);
    });
  });

  // 2. Numeric Page Button Generation with Ellipsis
  describe('Page Button Generator Algorithm', () => {
    const generatePageButtons = (currentPage: number, totalPages: number): (number | string)[] => {
      const buttons: (number | string)[] = [];
      if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) buttons.push(i);
      } else {
        buttons.push(1);
        if (currentPage > 3) buttons.push('...');

        const start = Math.max(2, currentPage - 1);
        const end = Math.min(totalPages - 1, currentPage + 1);

        for (let i = start; i <= end; i++) {
          if (!buttons.includes(i)) buttons.push(i);
        }

        if (currentPage < totalPages - 2) buttons.push('...');
        if (!buttons.includes(totalPages)) buttons.push(totalPages);
      }
      return buttons;
    };

    it('displays all pages when totalPages <= 7', () => {
      expect(generatePageButtons(1, 5)).toEqual([1, 2, 3, 4, 5]);
      expect(generatePageButtons(3, 7)).toEqual([1, 2, 3, 4, 5, 6, 7]);
    });

    it('inserts ellipsis correctly when totalPages > 7 and user is at start', () => {
      const buttons = generatePageButtons(1, 10);
      expect(buttons).toEqual([1, 2, '...', 10]);
    });

    it('inserts ellipsis on both sides when user is in the middle of a large list', () => {
      const buttons = generatePageButtons(5, 10);
      expect(buttons).toEqual([1, '...', 4, 5, 6, '...', 10]);
    });

    it('inserts ellipsis only on left when user is near the end', () => {
      const buttons = generatePageButtons(9, 10);
      expect(buttons).toEqual([1, '...', 8, 9, 10]);
    });
  });

  // 3. Navigation Controls & Boundary Disabling
  describe('Navigation Boundary Controls', () => {
    it('disables previous button on page 1 and next button on last page', () => {
      const isPrevDisabled = (page: number, _loading: boolean) => page <= 1;
      const isNextDisabled = (page: number, totalPages: number, _loading: boolean) => page >= totalPages;

      expect(isPrevDisabled(1, false)).toBe(true);
      expect(isPrevDisabled(2, false)).toBe(false);

      expect(isNextDisabled(1, 5, false)).toBe(false);
      expect(isNextDisabled(5, 5, false)).toBe(true);
      expect(isNextDisabled(6, 5, false)).toBe(true);
    });

    it('validates page change transitions correctly', () => {
      let currentPage = 2;
      const totalPages = 4;

      const handlePageChange = (newPage: number) => {
        if (newPage >= 1 && newPage <= totalPages && newPage !== currentPage) {
          currentPage = newPage;
          return true;
        }
        return false;
      };

      expect(handlePageChange(0)).toBe(false);
      expect(currentPage).toBe(2);

      expect(handlePageChange(5)).toBe(false);
      expect(currentPage).toBe(2);

      expect(handlePageChange(2)).toBe(false);
      expect(currentPage).toBe(2);

      expect(handlePageChange(3)).toBe(true);
      expect(currentPage).toBe(3);
    });
  });

  // 4. Page Size, Search, and Sort Resets
  describe('State Resets on Filter and Parameter Changes', () => {
    it('resets page to 1 when changing page size', () => {
      let currentPage = 4;
      let pageSize = 10;

      const handlePageSizeChange = (newSize: number) => {
        pageSize = newSize;
        currentPage = 1;
      };

      handlePageSizeChange(20);
      expect(pageSize).toBe(20);
      expect(currentPage).toBe(1);
    });

    it('resets page to 1 when changing search query', () => {
      let currentPage = 3;
      let search = '';

      const handleSearchChange = (query: string) => {
        search = query.trim();
        currentPage = 1;
      };

      handleSearchChange('Electronics');
      expect(search).toBe('Electronics');
      expect(currentPage).toBe(1);
    });

    it('resets page to 1 when changing sort order', () => {
      let currentPage = 5;
      let sortKey = 'newest';

      const handleSortChange = (newSort: string) => {
        sortKey = newSort;
        currentPage = 1;
      };

      handleSortChange('health');
      expect(sortKey).toBe('health');
      expect(currentPage).toBe(1);
    });
  });

  // 5. Deletion on Last Page Behavior
  describe('Deletion Behavior on Boundary Pages', () => {
    it('navigates to previous page if the only item on the current page (page > 1) is deleted', () => {
      let currentPage = 3;
      const itemsOnCurrentPage = 1; // Only 1 item remaining on page 3

      const calculateTargetPageAfterDelete = (page: number, itemsCount: number): number => {
        const willBeEmptyPage = itemsCount === 1 && page > 1;
        return willBeEmptyPage ? page - 1 : page;
      };

      const target = calculateTargetPageAfterDelete(currentPage, itemsOnCurrentPage);
      expect(target).toBe(2);
    });

    it('keeps page at 1 if deleting the only item on page 1', () => {
      const currentPage = 1;
      const itemsOnCurrentPage = 1;

      const calculateTargetPageAfterDelete = (page: number, itemsCount: number): number => {
        const willBeEmptyPage = itemsCount === 1 && page > 1;
        return willBeEmptyPage ? page - 1 : page;
      };

      const target = calculateTargetPageAfterDelete(currentPage, itemsOnCurrentPage);
      expect(target).toBe(1);
    });

    it('remains on the same page if multiple items exist on the current page', () => {
      const currentPage = 3;
      const itemsOnCurrentPage = 5;

      const calculateTargetPageAfterDelete = (page: number, itemsCount: number): number => {
        const willBeEmptyPage = itemsCount === 1 && page > 1;
        return willBeEmptyPage ? page - 1 : page;
      };

      const target = calculateTargetPageAfterDelete(currentPage, itemsOnCurrentPage);
      expect(target).toBe(3);
    });
  });

  // 6. API Compatibility: Paginated vs Unpaginated Responses
  describe('API Compatibility Handling', () => {
    it('correctly adapts backend PaginatedStoredAnalysesResponse', () => {
      const mockBackendResponse: PaginatedStoredAnalysesResponse = {
        items: createMockAnalyses(10),
        total: 35,
        page: 2,
        page_size: 10,
        total_pages: 4,
      };

      const isBackendPaginated = !Array.isArray(mockBackendResponse) && 'items' in mockBackendResponse;
      expect(isBackendPaginated).toBe(true);

      const items = mockBackendResponse.items;
      const totalCount = mockBackendResponse.total;
      const totalPages = mockBackendResponse.total_pages;

      expect(items.length).toBe(10);
      expect(totalCount).toBe(35);
      expect(totalPages).toBe(4);
    });

    it('correctly adapts legacy unpaginated array response for backward compatibility', () => {
      const mockRawArray: StoredAnalysisSummary[] = createMockAnalyses(7);
      const pageSize = 10;

      const isBackendPaginated = !Array.isArray(mockRawArray) && 'items' in (mockRawArray as any);
      expect(isBackendPaginated).toBe(false);

      const items = Array.isArray(mockRawArray) ? mockRawArray : [];
      const totalCount = items.length;
      const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

      expect(items.length).toBe(7);
      expect(totalCount).toBe(7);
      expect(totalPages).toBe(1);
    });
  });
});
