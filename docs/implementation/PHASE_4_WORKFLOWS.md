# Phase 4: Workflow Automation

**Status**: 🔵 Not Started (Blocked by Phase 3)  
**Duration**: 2 weeks (Weeks 12-13)  
**Priority**: Medium  
**Prerequisites**: Phase 3 complete

---

## 🎯 Objectives

Turn the static workflow UI cards into functional, executable automation pipelines that orchestrate multi-step research and content generation tasks.

### Success Criteria
- ✅ 7 workflow templates functional
- ✅ Workflow execution engine working
- ✅ Progress tracking real-time
- ✅ Results saved as artifacts
- ✅ Workflows customizable
- ✅ Execution time <5 minutes for complex workflows
- ✅ Tests maintain 80%+ coverage

---

## 📋 Workflow Templates

### 1. Research Workflow
**Purpose**: Comprehensive topic research with source validation

**Steps**:
1. Web search for topic
2. Scrape top 10 results
3. Extract entities and relationships
4. Synthesize findings
5. Generate report with citations

### 2. Document Analysis
**Purpose**: Deep analysis of single document

**Steps**:
1. Scrape or upload document
2. Extract key entities
3. Identify main themes
4. Generate summary
5. Build entity graph

### 3. Mind Map Generation
**Purpose**: Visual concept mapping

**Steps**:
1. Research topic
2. Extract concepts and relationships
3. Build hierarchical structure
4. Generate mind map visualization
5. Export as artifact

### 4. Knowledge Graph Exploration
**Purpose**: Navigate entity connections

**Steps**:
1. Identify starting entity
2. Traverse relationships (depth 2-3)
3. Collect connected entities
4. Build subgraph
5. Visualize in UI

### 5. Content Planning
**Purpose**: Strategic content creation

**Steps**:
1. Research topic and competitors
2. Identify content gaps
3. Generate outline
4. Suggest keywords
5. Create content calendar

### 6. PRD Generation
**Purpose**: Product Requirements Document creation

**Steps**:
1. Analyze market and competitors
2. Identify user needs
3. Define features and requirements
4. Generate PRD structure
5. Output formatted document

### 7. Task Breakdown
**Purpose**: Project decomposition

**Steps**:
1. Analyze project description
2. Identify components
3. Break into tasks
4. Estimate effort
5. Generate task list with dependencies

---

## 🏗️ Workflow Engine Architecture

### Workflow Definition (YAML)
```yaml
# workflows/research.yaml
name: "Research Workflow"
description: "Comprehensive topic research with source validation"
version: "1.0"
author: "system"

inputs:
  - name: "topic"
    type: "string"
    required: true
    description: "Research topic"
  
  - name: "depth"
    type: "integer"
    default: 10
    description: "Number of sources to scrape"

outputs:
  - name: "report"
    type: "markdown"
    description: "Research report"
  
  - name: "sources"
    type: "array"
    description: "List of sources"
  
  - name: "entities"
    type: "graph"
    description: "Extracted entity graph"

steps:
  - id: "search"
    name: "Web Search"
    type: "command"
    command: "/search"
    args: "${inputs.topic}"
    outputs:
      results: "search_results"
  
  - id: "scrape"
    name: "Scrape Top Results"
    type: "parallel"
    foreach: "${steps.search.results[:inputs.depth]}"
    command: "/scrape"
    args: "${item.url}"
    outputs:
      content: "scraped_content"
  
  - id: "extract"
    name: "Extract Entities"
    type: "function"
    function: "extract_entities"
    inputs:
      texts: "${steps.scrape.content}"
    outputs:
      entities: "extracted_entities"
  
  - id: "synthesize"
    name: "Synthesize Findings"
    type: "llm"
    prompt: |
      Synthesize the following research on "${inputs.topic}":
      
      ${steps.scrape.content}
      
      Create a comprehensive report covering:
      - Key findings
      - Main themes
      - Important entities: ${steps.extract.entities}
      - Conclusions
      
      Format as markdown with citations.
    outputs:
      report: "final_report"
  
  - id: "build_graph"
    name: "Build Knowledge Graph"
    type: "function"
    function: "build_graph"
    inputs:
      entities: "${steps.extract.entities}"
      content: "${steps.scrape.content}"
    outputs:
      graph: "entity_graph"

on_success:
  - save_artifact:
      type: "research_report"
      data: "${steps.synthesize.report}"
  
  - save_artifact:
      type: "knowledge_graph"
      data: "${steps.build_graph.graph}"

on_failure:
  - notify:
      message: "Research workflow failed: ${error.message}"
```

### Workflow Engine
```python
# apps/api/app/services/workflow_engine.py
import yaml
from typing import Dict, Any, List
from jinja2 import Template
from app.services.command_handler import CommandHandler
from app.services.llm import LLMService

class WorkflowEngine:
    """Execute multi-step workflows defined in YAML."""
    
    def __init__(self):
        self.command_handler = CommandHandler()
        self.llm_service = LLMService()
        self.context = {}
    
    async def load_workflow(self, workflow_path: str) -> Dict[str, Any]:
        """Load workflow definition from YAML file."""
        with open(workflow_path, 'r') as f:
            workflow = yaml.safe_load(f)
        return workflow
    
    async def execute(
        self,
        workflow: Dict[str, Any],
        inputs: Dict[str, Any],
        on_progress: callable = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow.
        
        Args:
            workflow: Workflow definition
            inputs: Input values
            on_progress: Callback for progress updates
        
        Returns:
            Workflow execution results
        """
        self.context = {"inputs": inputs, "steps": {}}
        total_steps = len(workflow["steps"])
        
        try:
            # Execute each step
            for i, step in enumerate(workflow["steps"]):
                if on_progress:
                    on_progress(step["name"], i + 1, total_steps)
                
                result = await self._execute_step(step)
                self.context["steps"][step["id"]] = result
            
            # Execute on_success handlers
            if "on_success" in workflow:
                await self._execute_handlers(workflow["on_success"])
            
            # Build outputs
            outputs = {}
            for output_def in workflow.get("outputs", []):
                output_value = self._resolve_template(
                    f"${{steps.{output_def['name']}}}"
                )
                outputs[output_def["name"]] = output_value
            
            return {
                "status": "success",
                "outputs": outputs,
                "context": self.context
            }
        
        except Exception as e:
            # Execute on_failure handlers
            if "on_failure" in workflow:
                self.context["error"] = {"message": str(e)}
                await self._execute_handlers(workflow["on_failure"])
            
            return {
                "status": "failed",
                "error": str(e),
                "context": self.context
            }
    
    async def _execute_step(self, step: Dict[str, Any]) -> Any:
        """Execute a single workflow step."""
        step_type = step["type"]
        
        if step_type == "command":
            return await self._execute_command_step(step)
        elif step_type == "llm":
            return await self._execute_llm_step(step)
        elif step_type == "function":
            return await self._execute_function_step(step)
        elif step_type == "parallel":
            return await self._execute_parallel_step(step)
        else:
            raise ValueError(f"Unknown step type: {step_type}")
    
    async def _execute_command_step(self, step: Dict[str, Any]) -> Any:
        """Execute a command step."""
        command = step["command"]
        args_template = step["args"]
        args = self._resolve_template(args_template)
        
        result = await self.command_handler.execute(command, args)
        
        # Map outputs
        outputs = {}
        if "outputs" in step:
            for key, value in step["outputs"].items():
                outputs[key] = result.get(key)
        
        return outputs if outputs else result
    
    async def _execute_llm_step(self, step: Dict[str, Any]) -> Any:
        """Execute an LLM generation step."""
        prompt_template = step["prompt"]
        prompt = self._resolve_template(prompt_template)
        
        response = await self.llm_service.generate_response(
            query=prompt,
            context=""
        )
        
        outputs = {}
        if "outputs" in step:
            for key, _ in step["outputs"].items():
                outputs[key] = response
        
        return outputs if outputs else response
    
    async def _execute_function_step(self, step: Dict[str, Any]) -> Any:
        """Execute a custom function step."""
        function_name = step["function"]
        inputs = {}
        
        if "inputs" in step:
            for key, value_template in step["inputs"].items():
                inputs[key] = self._resolve_template(value_template)
        
        # Call registered function
        function = self._get_function(function_name)
        result = await function(**inputs)
        
        # Map outputs
        outputs = {}
        if "outputs" in step:
            for key, _ in step["outputs"].items():
                outputs[key] = result.get(key)
        
        return outputs if outputs else result
    
    async def _execute_parallel_step(self, step: Dict[str, Any]) -> List[Any]:
        """Execute a step in parallel for multiple items."""
        import asyncio
        
        items_template = step["foreach"]
        items = self._resolve_template(items_template)
        
        tasks = []
        for item in items:
            # Create temporary context with item
            original_context = self.context.copy()
            self.context["item"] = item
            
            # Create step config
            item_step = {
                "type": "command",
                "command": step["command"],
                "args": step["args"]
            }
            
            task = self._execute_step(item_step)
            tasks.append(task)
            
            # Restore context
            self.context = original_context
        
        # Execute in parallel
        results = await asyncio.gather(*tasks)
        
        return results
    
    def _resolve_template(self, template: str) -> Any:
        """Resolve a template string using Jinja2."""
        if not isinstance(template, str):
            return template
        
        if not template.startswith("${") or not template.endswith("}"):
            return template
        
        # Extract expression
        expression = template[2:-1]
        
        # Use Jinja2 for complex expressions
        jinja_template = Template("{{ " + expression + " }}")
        result = jinja_template.render(**self.context)
        
        # Try to parse as Python literal
        try:
            import ast
            return ast.literal_eval(result)
        except:
            return result
    
    def _get_function(self, function_name: str) -> callable:
        """Get a registered function by name."""
        # Registry of available functions
        functions = {
            "extract_entities": self._func_extract_entities,
            "build_graph": self._func_build_graph,
        }
        
        if function_name not in functions:
            raise ValueError(f"Unknown function: {function_name}")
        
        return functions[function_name]
    
    async def _func_extract_entities(self, texts: List[str]) -> Dict[str, Any]:
        """Function: Extract entities from texts."""
        from app.services.entity_extractor import EntityExtractor
        
        extractor = EntityExtractor()
        all_entities = []
        
        for text in texts:
            entities = await extractor.extract_entities(text)
            all_entities.extend(entities)
        
        return {"entities": all_entities}
    
    async def _func_build_graph(
        self,
        entities: List[Dict],
        content: List[str]
    ) -> Dict[str, Any]:
        """Function: Build knowledge graph from entities."""
        from app.services.graph_db import GraphDBService
        from app.services.relationship_extractor import RelationshipExtractor
        
        graph_db = GraphDBService()
        rel_extractor = RelationshipExtractor()
        
        # Create entity nodes
        for entity in entities:
            await graph_db.create_entity(
                entity_id=entity["id"],
                entity_type=entity["type"],
                text=entity["text"],
                metadata=entity.get("metadata", {})
            )
        
        # Extract and create relationships
        all_text = "\n\n".join(content)
        relationships = await rel_extractor.extract_relationships(
            text=all_text,
            entities=entities
        )
        
        for source, rel_type, target in relationships:
            await graph_db.create_relationship(
                source_id=source,
                target_id=target,
                relationship_type=rel_type,
                metadata={}
            )
        
        return {"graph": {"entities": entities, "relationships": relationships}}
    
    async def _execute_handlers(self, handlers: List[Dict[str, Any]]):
        """Execute workflow handlers (success/failure)."""
        for handler in handlers:
            if "save_artifact" in handler:
                await self._save_artifact(handler["save_artifact"])
            elif "notify" in handler:
                await self._notify(handler["notify"])
    
    async def _save_artifact(self, config: Dict[str, Any]):
        """Save workflow artifact."""
        # Implementation: save to database or file system
        pass
    
    async def _notify(self, config: Dict[str, Any]):
        """Send notification."""
        # Implementation: send notification (log, webhook, etc.)
        message = self._resolve_template(config["message"])
        print(f"NOTIFICATION: {message}")
```

---

## 📦 Workflow API

### Endpoints
```python
# apps/api/app/api/v1/endpoints/workflows.py
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.services.workflow_engine import WorkflowEngine
import uuid

router = APIRouter()

class WorkflowExecutionRequest(BaseModel):
    workflow_name: str
    inputs: Dict[str, Any]

class WorkflowExecutionResponse(BaseModel):
    execution_id: str
    status: str
    workflow_name: str

# In-memory execution store (use Redis in production)
executions = {}

@router.post("/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks
):
    """Execute a workflow in the background."""
    execution_id = str(uuid.uuid4())
    
    # Initialize execution record
    executions[execution_id] = {
        "id": execution_id,
        "workflow_name": request.workflow_name,
        "status": "running",
        "progress": 0,
        "current_step": None,
        "result": None
    }
    
    # Start execution in background
    background_tasks.add_task(
        _run_workflow,
        execution_id,
        request.workflow_name,
        request.inputs
    )
    
    return WorkflowExecutionResponse(
        execution_id=execution_id,
        status="running",
        workflow_name=request.workflow_name
    )

@router.get("/execution/{execution_id}")
async def get_execution_status(execution_id: str):
    """Get workflow execution status."""
    if execution_id not in executions:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return executions[execution_id]

@router.get("/templates")
async def list_workflow_templates():
    """List available workflow templates."""
    templates = [
        {
            "name": "research",
            "title": "Research Workflow",
            "description": "Comprehensive topic research",
            "inputs": [
                {"name": "topic", "type": "string", "required": True},
                {"name": "depth", "type": "integer", "default": 10}
            ]
        },
        {
            "name": "document_analysis",
            "title": "Document Analysis",
            "description": "Deep document analysis",
            "inputs": [
                {"name": "url", "type": "string", "required": True}
            ]
        },
        # ... other templates
    ]
    return {"templates": templates}

async def _run_workflow(
    execution_id: str,
    workflow_name: str,
    inputs: Dict[str, Any]
):
    """Background task to run workflow."""
    engine = WorkflowEngine()
    
    def update_progress(step_name: str, current: int, total: int):
        executions[execution_id]["current_step"] = step_name
        executions[execution_id]["progress"] = int((current / total) * 100)
    
    try:
        # Load workflow
        workflow = await engine.load_workflow(f"workflows/{workflow_name}.yaml")
        
        # Execute
        result = await engine.execute(
            workflow=workflow,
            inputs=inputs,
            on_progress=update_progress
        )
        
        # Update execution record
        executions[execution_id]["status"] = result["status"]
        executions[execution_id]["progress"] = 100
        executions[execution_id]["result"] = result
    
    except Exception as e:
        executions[execution_id]["status"] = "failed"
        executions[execution_id]["error"] = str(e)
```

---

## 🎨 Frontend Integration

### Workflow Execution Component
```typescript
// apps/web/components/workflows/WorkflowExecutor.tsx
'use client';

import { useState } from 'react';
import { PlayCircle, Loader2 } from 'lucide-react';

interface WorkflowTemplate {
  name: string;
  title: string;
  description: string;
  inputs: Array<{
    name: string;
    type: string;
    required: boolean;
    default?: any;
  }>;
}

export default function WorkflowExecutor({ template }: { template: WorkflowTemplate }) {
  const [inputs, setInputs] = useState<Record<string, any>>({});
  const [executionId, setExecutionId] = useState<string | null>(null);
  const [status, setStatus] = useState<'idle' | 'running' | 'completed' | 'failed'>('idle');
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState<string | null>(null);

  const executeWorkflow = async () => {
    setStatus('running');
    
    const response = await fetch('/api/workflows/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow_name: template.name,
        inputs
      })
    });
    
    const data = await response.json();
    setExecutionId(data.execution_id);
    
    // Poll for status
    pollStatus(data.execution_id);
  };

  const pollStatus = async (id: string) => {
    const interval = setInterval(async () => {
      const response = await fetch(`/api/workflows/execution/${id}`);
      const data = await response.json();
      
      setProgress(data.progress);
      setCurrentStep(data.current_step);
      
      if (data.status === 'completed' || data.status === 'failed') {
        setStatus(data.status);
        clearInterval(interval);
      }
    }, 1000);
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-bold mb-4">{template.title}</h2>
      <p className="text-gray-600 mb-6">{template.description}</p>

      {/* Input Form */}
      <div className="space-y-4 mb-6">
        {template.inputs.map((input) => (
          <div key={input.name}>
            <label className="block text-sm font-medium mb-1">
              {input.name}
              {input.required && <span className="text-red-500">*</span>}
            </label>
            <input
              type={input.type === 'integer' ? 'number' : 'text'}
              value={inputs[input.name] || input.default || ''}
              onChange={(e) => setInputs({ ...inputs, [input.name]: e.target.value })}
              className="w-full px-3 py-2 border rounded-lg"
              disabled={status === 'running'}
            />
          </div>
        ))}
      </div>

      {/* Execute Button */}
      <button
        onClick={executeWorkflow}
        disabled={status === 'running'}
        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {status === 'running' ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            Running...
          </>
        ) : (
          <>
            <PlayCircle className="w-5 h-5" />
            Execute Workflow
          </>
        )}
      </button>

      {/* Progress */}
      {status === 'running' && (
        <div className="mt-6">
          <div className="flex justify-between text-sm mb-2">
            <span>{currentStep}</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Result */}
      {status === 'completed' && (
        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-green-800 font-medium">Workflow completed successfully!</p>
        </div>
      )}

      {status === 'failed' && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800 font-medium">Workflow failed.</p>
        </div>
      )}
    </div>
  );
}
```

---

## 🧪 Testing Strategy

### Workflow Engine Tests
```python
# tests/services/test_workflow_engine.py
import pytest
from app.services.workflow_engine import WorkflowEngine

pytestmark = pytest.mark.anyio

class TestWorkflowEngine:
    async def test_simple_workflow_execution(self):
        """Test execution of a simple workflow."""
        engine = WorkflowEngine()
        
        workflow = {
            "name": "Test Workflow",
            "inputs": [{"name": "value", "type": "string"}],
            "steps": [
                {
                    "id": "step1",
                    "name": "Test Step",
                    "type": "function",
                    "function": "identity",
                    "inputs": {"x": "${inputs.value}"},
                    "outputs": {"result": "output"}
                }
            ],
            "outputs": [{"name": "result"}]
        }
        
        result = await engine.execute(
            workflow=workflow,
            inputs={"value": "test"}
        )
        
        assert result["status"] == "success"
        assert result["outputs"]["result"] == "test"
```

---

## ✅ Definition of Done

- [ ] 7 workflow templates created
- [ ] Workflow engine executes correctly
- [ ] Progress tracking works
- [ ] Artifacts saved properly
- [ ] Frontend integration complete
- [ ] Workflows execute in <5 minutes
- [ ] All tests pass (80%+ coverage)
- [ ] Documentation complete

---

**Previous Phase**: [PHASE_3_VISUALIZATION.md](PHASE_3_VISUALIZATION.md)  
**Implementation Plan**: [IMPLEMENTATION_PLAN.md](../../IMPLEMENTATION_PLAN.md)
