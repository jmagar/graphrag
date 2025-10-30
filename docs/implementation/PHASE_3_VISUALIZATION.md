# Phase 3: Visualization & Commands

**Status**: 🔵 Not Started (Blocked by Phase 2)  
**Duration**: 3 weeks (Weeks 9-11)  
**Priority**: Medium  
**Prerequisites**: Phase 2 complete

---

## 🎯 Objectives

Make the knowledge graph visible and interactive in the UI, implement command execution system, and enable spaces/tags functionality.

### Success Criteria
- ✅ Knowledge graph visualized with React Flow
- ✅ All 7 commands functional
- ✅ Spaces & tags working
- ✅ Graph exploration smooth (<2s load)
- ✅ Citation click-through working
- ✅ Mobile-responsive visualizations
- ✅ Tests maintain 70%+ coverage

---

## 📋 Deliverables

### 1. Knowledge Graph Visualization

#### React Flow Integration
```typescript
// apps/web/components/graph/KnowledgeGraphView.tsx
'use client';

import React, { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';

interface GraphData {
  nodes: Array<{
    id: string;
    type: string;
    text: string;
    metadata: any;
  }>;
  edges: Array<{
    source: string;
    target: string;
    type: string;
  }>;
}

export default function KnowledgeGraphView({ entityId }: { entityId?: string }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  useEffect(() => {
    loadGraph();
  }, [entityId]);

  const loadGraph = async () => {
    setIsLoading(true);
    try {
      const endpoint = entityId 
        ? `/api/graph/entities/${entityId}/connections`
        : `/api/graph/entities/search?limit=50`;
      
      const response = await fetch(endpoint);
      const data: GraphData = await response.json();

      // Transform to React Flow format
      const flowNodes: Node[] = data.nodes.map((node) => ({
        id: node.id,
        type: getNodeType(node.type),
        position: { x: 0, y: 0 }, // Will be auto-laid out
        data: {
          label: node.text,
          type: node.type,
          metadata: node.metadata,
        },
        style: getNodeStyle(node.type),
      }));

      const flowEdges: Edge[] = data.edges.map((edge, index) => ({
        id: `edge-${index}`,
        source: edge.source,
        target: edge.target,
        label: edge.type,
        type: 'smoothstep',
        animated: true,
        style: { stroke: '#64748b' },
      }));

      // Auto-layout (dagre or elk)
      const layouted = autoLayout(flowNodes, flowEdges);
      
      setNodes(layouted.nodes);
      setEdges(layouted.edges);
    } catch (error) {
      console.error('Failed to load graph:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const onNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    setSelectedNode(node);
    // Could expand to show connected nodes
  }, []);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }

  return (
    <div className="h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        fitView
        attributionPosition="bottom-left"
      >
        <Controls />
        <Background />
        
        {selectedNode && (
          <Panel position="top-right" className="bg-white p-4 rounded-lg shadow-lg max-w-sm">
            <h3 className="font-semibold text-lg mb-2">
              {selectedNode.data.label}
            </h3>
            <div className="text-sm text-gray-600">
              <p><strong>Type:</strong> {selectedNode.data.type}</p>
              {selectedNode.data.metadata && (
                <div className="mt-2">
                  <strong>Metadata:</strong>
                  <pre className="text-xs mt-1 p-2 bg-gray-50 rounded">
                    {JSON.stringify(selectedNode.data.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="mt-3 text-sm text-blue-600 hover:underline"
            >
              Close
            </button>
          </Panel>
        )}
      </ReactFlow>
    </div>
  );
}

// Helper functions
function getNodeType(entityType: string): string {
  const typeMap: Record<string, string> = {
    PERSON: 'input',
    ORGANIZATION: 'default',
    LOCATION: 'default',
    CONCEPT: 'output',
  };
  return typeMap[entityType] || 'default';
}

function getNodeStyle(entityType: string): React.CSSProperties {
  const colorMap: Record<string, string> = {
    PERSON: '#3b82f6',      // blue
    ORGANIZATION: '#10b981', // green
    LOCATION: '#f59e0b',     // amber
    CONCEPT: '#8b5cf6',      // purple
    PRODUCT: '#ec4899',      // pink
  };
  
  return {
    background: colorMap[entityType] || '#64748b',
    color: 'white',
    border: '2px solid white',
    borderRadius: '8px',
    padding: '10px',
    fontSize: '12px',
    fontWeight: '500',
  };
}

function autoLayout(nodes: Node[], edges: Edge[]) {
  // Use dagre or elk for automatic graph layout
  // For simplicity, using a force-directed layout
  // In production, integrate @dagrejs/dagre or elkjs
  
  const layoutedNodes = nodes.map((node, index) => ({
    ...node,
    position: {
      x: (index % 5) * 200,
      y: Math.floor(index / 5) * 150,
    },
  }));
  
  return { nodes: layoutedNodes, edges };
}
```

#### Graph View Modal
```typescript
// apps/web/components/graph/GraphViewModal.tsx
'use client';

import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import KnowledgeGraphView from './KnowledgeGraphView';

interface GraphViewModalProps {
  isOpen: boolean;
  onClose: () => void;
  entityId?: string;
  title?: string;
}

export default function GraphViewModal({
  isOpen,
  onClose,
  entityId,
  title = 'Knowledge Graph',
}: GraphViewModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl h-[80vh]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="h-full">
          <KnowledgeGraphView entityId={entityId} />
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

---

### 2. Command Execution System

#### Command Handler Service
```python
# apps/api/app/services/command_handler.py
from typing import Dict, Any, List
from app.services.firecrawl import FirecrawlService
from app.services.hybrid_query import HybridQueryEngine

class CommandHandler:
    """Handle execution of slash commands."""
    
    COMMANDS = {
        "/search": "Search the web",
        "/scrape": "Scrape a specific URL",
        "/map": "Map all URLs from a website",
        "/extract": "Extract structured data",
        "/graph": "Visualize knowledge graph",
        "/summarize": "Summarize documents",
        "/compare": "Compare documents",
    }
    
    async def execute(self, command: str, args: str) -> Dict[str, Any]:
        """Execute a command and return results."""
        if command == "/search":
            return await self._search_web(args)
        elif command == "/scrape":
            return await self._scrape_url(args)
        elif command == "/map":
            return await self._map_website(args)
        elif command == "/extract":
            return await self._extract_data(args)
        elif command == "/graph":
            return await self._show_graph(args)
        elif command == "/summarize":
            return await self._summarize(args)
        elif command == "/compare":
            return await self._compare(args)
        else:
            raise ValueError(f"Unknown command: {command}")
    
    async def _search_web(self, query: str) -> Dict[str, Any]:
        """Execute /search command."""
        firecrawl = FirecrawlService()
        results = await firecrawl.search_web(query)
        
        return {
            "command": "/search",
            "query": query,
            "results": results.get("data", []),
            "artifact_type": "search_results",
        }
    
    async def _scrape_url(self, url: str) -> Dict[str, Any]:
        """Execute /scrape command."""
        firecrawl = FirecrawlService()
        result = await firecrawl.scrape_url(url)
        
        return {
            "command": "/scrape",
            "url": url,
            "content": result.get("data", {}).get("markdown", ""),
            "artifact_type": "scraped_content",
        }
    
    async def _map_website(self, url: str) -> Dict[str, Any]:
        """Execute /map command."""
        firecrawl = FirecrawlService()
        result = await firecrawl.map_url(url)
        
        return {
            "command": "/map",
            "url": url,
            "urls": result.get("data", []),
            "artifact_type": "url_map",
        }
    
    async def _extract_data(self, args: str) -> Dict[str, Any]:
        """Execute /extract command - requires URL and schema."""
        # Parse: /extract <url> {"schema": {...}}
        # Implementation depends on format
        pass
    
    async def _show_graph(self, entity_name: str) -> Dict[str, Any]:
        """Execute /graph command."""
        from app.services.graph_db import GraphDBService
        
        graph_db = GraphDBService()
        entities = await graph_db.search_entities(entity_name, limit=1)
        
        if not entities:
            return {
                "command": "/graph",
                "error": f"Entity '{entity_name}' not found",
            }
        
        entity = entities[0]
        connections = await graph_db.find_connected_entities(
            entity_id=entity["id"],
            max_depth=2
        )
        
        return {
            "command": "/graph",
            "entity": entity,
            "connections": connections,
            "artifact_type": "knowledge_graph",
        }
    
    async def _summarize(self, query: str) -> Dict[str, Any]:
        """Execute /summarize command."""
        # Search for documents, then summarize
        hybrid_engine = HybridQueryEngine()
        results = await hybrid_engine.hybrid_search(query, vector_limit=10)
        
        # Use LLM to summarize
        from app.services.llm import LLMService
        llm = LLMService()
        
        context = "\n\n".join([
            r["content"][:500] for r in results["combined_results"][:5]
        ])
        
        summary = await llm.generate_response(
            query=f"Summarize the following information about '{query}':",
            context=context
        )
        
        return {
            "command": "/summarize",
            "query": query,
            "summary": summary,
            "sources": results["combined_results"][:5],
            "artifact_type": "summary",
        }
    
    async def _compare(self, args: str) -> Dict[str, Any]:
        """Execute /compare command."""
        # Parse: /compare entity1 vs entity2
        # Implementation depends on format
        pass
```

#### Command Endpoint
```python
# apps/api/app/api/v1/endpoints/commands.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.command_handler import CommandHandler

router = APIRouter()

class CommandRequest(BaseModel):
    command: str
    args: str

@router.post("/execute")
async def execute_command(request: CommandRequest):
    """Execute a slash command."""
    handler = CommandHandler()
    
    try:
        result = await handler.execute(request.command, request.args)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {str(e)}")

@router.get("/list")
async def list_commands():
    """List all available commands."""
    return {
        "commands": [
            {"name": cmd, "description": desc}
            for cmd, desc in CommandHandler.COMMANDS.items()
        ]
    }
```

#### Frontend Command Integration
```typescript
// apps/web/components/input/CommandsDropdown.tsx - Update to call API
import { useState, useEffect } from 'react';
import { Command } from 'lucide-react';

interface CommandOption {
  name: string;
  description: string;
}

export default function CommandsDropdown({ onSelect }: { onSelect: (cmd: string) => void }) {
  const [commands, setCommands] = useState<CommandOption[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    fetch('/api/commands/list')
      .then((res) => res.json())
      .then((data) => setCommands(data.commands));
  }, []);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 hover:bg-gray-100 rounded-lg"
      >
        <Command className="w-5 h-5" />
      </button>

      {isOpen && (
        <div className="absolute bottom-full mb-2 left-0 bg-white border rounded-lg shadow-lg w-64 max-h-96 overflow-y-auto">
          {commands.map((cmd) => (
            <button
              key={cmd.name}
              onClick={() => {
                onSelect(cmd.name);
                setIsOpen(false);
              }}
              className="w-full px-4 py-2 text-left hover:bg-gray-50 border-b last:border-b-0"
            >
              <div className="font-medium text-sm">{cmd.name}</div>
              <div className="text-xs text-gray-500">{cmd.description}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

---

### 3. Spaces & Tags Functionality

#### Backend Implementation (Already in Phase 1 DB schema)
```python
# apps/api/app/api/v1/endpoints/spaces.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.database import get_session

router = APIRouter()

@router.get("/")
async def list_spaces(db: AsyncSession = Depends(get_session)):
    """List all spaces with conversation counts."""
    # Query distinct spaces
    pass

@router.get("/{space}/conversations")
async def get_space_conversations(
    space: str,
    db: AsyncSession = Depends(get_session)
):
    """Get all conversations in a space."""
    pass

@router.get("/tags")
async def list_tags(db: AsyncSession = Depends(get_session)):
    """List all tags with usage counts."""
    pass
```

#### Frontend Spaces Sidebar
```typescript
// apps/web/components/sidebar/SpacesSection.tsx
'use client';

import { useChatStore } from '@/stores/chatStore';
import { Hash, Plus } from 'lucide-react';

export default function SpacesSection() {
  const { spaces, currentSpace, setSpace, createSpace } = useChatStore();

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3 px-2">
        <h3 className="text-sm font-medium text-gray-500">Spaces</h3>
        <button
          onClick={() => {
            const name = prompt('Space name:');
            if (name) createSpace(name);
          }}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      <div className="space-y-1">
        {spaces.map((space) => (
          <button
            key={space.name}
            onClick={() => setSpace(space.name)}
            className={`
              w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm
              ${currentSpace === space.name ? 'bg-blue-50 text-blue-600' : 'hover:bg-gray-50'}
            `}
          >
            <Hash className="w-4 h-4" />
            <span className="flex-1 text-left">{space.name}</span>
            <span className="text-xs text-gray-400">{space.count}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
```

---

### 4. Citation Click-Through

#### Citation Component
```typescript
// apps/web/components/chat/Citation.tsx
'use client';

import { ExternalLink } from 'lucide-react';

interface CitationProps {
  source: {
    url: string;
    title: string;
    snippet: string;
  };
  index: number;
}

export default function Citation({ source, index }: CitationProps) {
  return (
    <div className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-medium">
          {index + 1}
        </div>
        
        <div className="flex-1 min-w-0">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-sm hover:underline flex items-center gap-1 mb-1"
          >
            {source.title}
            <ExternalLink className="w-3 h-3" />
          </a>
          
          <p className="text-xs text-gray-600 line-clamp-2">
            {source.snippet}
          </p>
          
          <div className="text-xs text-gray-400 mt-1 truncate">
            {source.url}
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## 🧪 Testing Strategy

### Frontend Component Tests
```typescript
// apps/web/__tests__/components/graph/KnowledgeGraphView.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import KnowledgeGraphView from '@/components/graph/KnowledgeGraphView';

describe('KnowledgeGraphView', () => {
  it('should render loading state initially', () => {
    render(<KnowledgeGraphView />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should load and display graph data', async () => {
    // Mock API response
    global.fetch = jest.fn(() =>
      Promise.resolve({
        json: () => Promise.resolve({
          nodes: [{ id: '1', type: 'PERSON', text: 'Alice' }],
          edges: [],
        }),
      })
    );

    render(<KnowledgeGraphView />);

    await waitFor(() => {
      expect(screen.getByText('Alice')).toBeInTheDocument();
    });
  });
});
```

### Backend Command Tests
```python
# tests/api/v1/endpoints/test_commands.py
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

class TestCommands:
    async def test_search_command_execution(
        self, test_client: AsyncClient, respx_mock
    ):
        """Test /search command execution."""
        # Mock Firecrawl API
        respx_mock.post("http://mock-firecrawl:4200/v2/search").mock(
            return_value={"data": [{"url": "https://example.com"}]}
        )
        
        # Execute command
        response = await test_client.post(
            "/api/v1/commands/execute",
            json={"command": "/search", "args": "test query"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["command"] == "/search"
        assert "results" in data
```

---

## 📦 Dependencies

### Frontend
```json
{
  "dependencies": {
    "reactflow": "^11.10.0",
    "@dagrejs/dagre": "^1.0.4"
  }
}
```

---

## ✅ Definition of Done

- [ ] Knowledge graph renders correctly
- [ ] All 7 commands execute
- [ ] Spaces filtering works
- [ ] Tags applied and filtered
- [ ] Citations clickable
- [ ] Graph loads in <2 seconds
- [ ] Mobile-responsive
- [ ] Tests pass (70%+ coverage)
- [ ] Performance benchmarked

---

**Next Phase**: [PHASE_4_WORKFLOWS.md](PHASE_4_WORKFLOWS.md)
