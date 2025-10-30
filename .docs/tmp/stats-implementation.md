# Real-Time Statistics Implementation

## Objective
Replace hardcoded mock statistics in the UI with real-time data from the Qdrant vector database.

## Investigation Findings

### 1. Current State Analysis

**Frontend Component**: [apps/web/components/sidebar/StatisticsSection.tsx](../../apps/web/components/sidebar/StatisticsSection.tsx)
- **Finding**: Displayed hardcoded values (1,247 documents, 45.2K vectors, 2.4 GB storage)
- **Conclusion**: Needed conversion to client component with data fetching

**Backend Service**: [apps/api/app/services/vector_db.py:117-126](../../apps/api/app/services/vector_db.py#L117-L126)
- **Finding**: Basic `get_collection_info()` existed returning minimal stats
- **Conclusion**: Required enhancement to return comprehensive metrics

**Existing API**: [apps/api/app/api/v1/endpoints/query.py:101-108](../../apps/api/app/api/v1/endpoints/query.py#L101-L108)
- **Finding**: `/api/v1/query/collection/info` endpoint already existed
- **Conclusion**: Could reuse this endpoint with enhanced data

## Implementation (TDD Approach)

### Phase 1: RED - Write Failing Test
**Created**: [apps/api/tests/api/v1/endpoints/test_stats.py](../../apps/api/tests/api/v1/endpoints/test_stats.py)
- Test validates stats endpoint returns required fields
- Test checks data types and non-negative values
- Test ensures storage information is available

### Phase 2: GREEN - Backend Enhancement
**Modified**: [apps/api/app/services/vector_db.py:117-146](../../apps/api/app/services/vector_db.py#L117-L146)

**Changes**:
- Added storage size calculation (vectors: 768 floats × 4 bytes + ~2KB payload overhead)
- Implemented human-readable size formatting (B/KB/MB/GB)
- Added fields:
  - `indexed_vectors_count`
  - `segments_count`
  - `storage` (formatted string)
  - `storage_bytes` (raw value)

**Formula**:
```
storage = (vectors_count × 768 × 4) + (points_count × 2048)
```

### Phase 3: API Route Creation
**Created**: [apps/web/app/api/stats/route.ts](../../apps/web/app/api/stats/route.ts)
- Proxies requests to `http://localhost:4400/api/v1/query/collection/info`
- Implements error handling for backend failures
- Disables Next.js caching (`cache: "no-store"`) for fresh data

### Phase 4: Frontend Integration
**Modified**: [apps/web/components/sidebar/StatisticsSection.tsx](../../apps/web/components/sidebar/StatisticsSection.tsx)

**Key Changes**:
1. Added `"use client"` directive for React hooks
2. Implemented data fetching with `useEffect`
3. Auto-refresh every 30 seconds
4. Number formatting utility:
   - ≥1M: "1.5M"
   - ≥1K: "45.2K"
   - <1K: "247"
5. Status color coding (green/yellow based on Qdrant health)
6. Loading and error states

## Data Flow

```
User Interface (StatisticsSection)
    ↓ fetch("/api/stats")
Next.js API Route (/api/stats/route.ts)
    ↓ fetch("http://localhost:4400/api/v1/query/collection/info")
FastAPI Endpoint (query.py:101)
    ↓ await vector_db_service.get_collection_info()
Qdrant Service (vector_db.py:117)
    ↓ self.client.get_collection()
Qdrant Database
```

## Key Design Decisions

1. **No caching**: Stats must reflect real-time state
2. **30-second refresh**: Balance between freshness and load
3. **Storage estimation**: Approximate calculation (Qdrant doesn't expose exact sizes)
4. **Type safety**: Strict TypeScript interface, no `any` types
5. **Error handling**: Graceful degradation with error messages

## Files Modified/Created

### Created
- `apps/api/tests/api/v1/endpoints/test_stats.py`
- `apps/web/app/api/stats/route.ts`

### Modified
- `apps/api/app/services/vector_db.py`
- `apps/web/components/sidebar/StatisticsSection.tsx`

## Testing

Backend test runs with:
```bash
cd apps/api
poetry install
poetry run pytest tests/api/v1/endpoints/test_stats.py -v
```

## Notes

- Storage calculation is an **estimate** (Qdrant client doesn't expose exact disk usage)
- Component maintains loading state for better UX during initial fetch
- Auto-refresh ensures stats stay current as crawls complete
- Status field uses Qdrant's health indicator ("green" = healthy)
