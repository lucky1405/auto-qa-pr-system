"""
Scalable Asynchronous Task Queue & Worker Pool.
Enables non-blocking PR analysis, parallel job execution, task state tracking,
and real-time Pub/Sub WebSocket event broadcasting.
"""
import asyncio
import uuid
import datetime
from typing import Dict, Any, Optional, List, Callable, Set
from app.models.pr import PullRequest, PRStatus
from app.models.agents import OrchestrationPipelineResult
from app.models.metrics import ComprehensiveQualityReport
from app.agents.orchestrator import orchestrator
from app.metrics.engine import metrics_engine
from app.rag.engine import rag_engine

class TaskItem:
    def __init__(self, task_id: str, pr: PullRequest):
        self.task_id = task_id
        self.pr = pr
        self.status: str = "QUEUED"
        self.progress: int = 0
        self.current_stage: str = "QUEUED"
        self.pipeline_result: Optional[OrchestrationPipelineResult] = None
        self.quality_report: Optional[ComprehensiveQualityReport] = None
        self.events: List[Dict[str, Any]] = []
        self.created_at: str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        self.error: Optional[str] = None

class ScalableWorkerPool:
    def __init__(self, concurrency: int = 4, max_queue_size: int = 100):
        self.concurrency = concurrency
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self.tasks: Dict[str, TaskItem] = {}
        self.workers: List[asyncio.Task] = []
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self.global_subscribers: Set[asyncio.Queue] = set()
        self.is_running = False

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        for i in range(self.concurrency):
            worker_task = asyncio.create_task(self._worker_loop(worker_id=i + 1))
            self.workers.append(worker_task)

    async def stop(self):
        self.is_running = False
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    async def enqueue(self, pr: PullRequest) -> str:
        task_id = f"task-{uuid.uuid4().hex[:8]}"
        task = TaskItem(task_id, pr)
        self.tasks[task_id] = task
        await self.queue.put(task)
        await self._broadcast(task_id, {
            "type": "TASK_QUEUED",
            "task_id": task_id,
            "pr_id": pr.id,
            "status": "QUEUED"
        })
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskItem]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        return [
            {
                "task_id": t.task_id,
                "pr_id": t.pr.id,
                "pr_title": t.pr.title,
                "status": t.status,
                "progress": t.progress,
                "current_stage": t.current_stage,
                "created_at": t.created_at,
                "completed_at": t.completed_at
            }
            for t in reversed(list(self.tasks.values()))
        ]

    async def subscribe(self, task_id: Optional[str] = None) -> asyncio.Queue:
        q = asyncio.Queue()
        if task_id:
            if task_id not in self.subscribers:
                self.subscribers[task_id] = set()
            self.subscribers[task_id].add(q)
        else:
            self.global_subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue, task_id: Optional[str] = None):
        if task_id and task_id in self.subscribers:
            self.subscribers[task_id].discard(q)
        self.global_subscribers.discard(q)

    async def _broadcast(self, task_id: str, data: Dict[str, Any]):
        # Direct subscribers
        if task_id in self.subscribers:
            for q in list(self.subscribers[task_id]):
                try:
                    await q.put(data)
                except Exception:
                    pass
        # Global subscribers
        for q in list(self.global_subscribers):
            try:
                await q.put(data)
            except Exception:
                pass

    async def _worker_loop(self, worker_id: int):
        while self.is_running:
            try:
                task: TaskItem = await self.queue.get()
            except asyncio.CancelledError:
                break

            try:
                task.status = "PROCESSING"
                task.current_stage = "STARTING"
                task.progress = 10

                # Callback to stream events to clients
                async def handle_event(stage: str, event_data: Dict[str, Any]):
                    task.current_stage = stage
                    task.events.append(event_data)
                    # Compute approximate progress
                    progress_map = {
                        "INGESTION": 20,
                        "FAN_OUT": 35,
                        "REVIEW_AGGREGATION": 50,
                        "RAG_RETRIEVAL": 65,
                        "REPAIR_ATTEMPT": 75,
                        "SANDBOX_DISPATCH": 85,
                        "SANDBOX_PASSED": 95,
                        "SANDBOX_FAILED": 80,
                        "PIPELINE_COMPLETE": 100,
                        "CLEAN_PR": 85,
                        "VERDICT": 100
                    }
                    task.progress = progress_map.get(stage, task.progress)
                    await self._broadcast(task.task_id, {
                        "type": "PIPELINE_EVENT",
                        "task_id": task.task_id,
                        "stage": stage,
                        "progress": task.progress,
                        "event": event_data
                    })

                # Execute pipeline via orchestrator
                pipeline_result = await orchestrator.execute_pipeline(task.pr, event_callback=handle_event)
                task.pipeline_result = pipeline_result

                # Compute software quality & reliability report
                primary_file = task.pr.get_primary_file()
                all_issues = []
                for a in pipeline_result.agent_results:
                    all_issues.extend(a.issues)

                rag_metrics_dict = rag_engine.evaluate_retrieval_metrics(
                    query=primary_file.content,
                    retrieved_docs=pipeline_result.rag_retrievals
                )

                from app.models.metrics import RAGQualityMetrics
                rag_metrics = RAGQualityMetrics(
                    context_relevance_score=rag_metrics_dict["context_relevance"],
                    retrieval_precision=rag_metrics_dict["retrieval_precision"],
                    retrieval_recall=rag_metrics_dict["retrieval_recall"],
                    groundedness_faithfulness_score=rag_metrics_dict["groundedness"]
                )

                patched_code = pipeline_result.final_patch.patched_code if pipeline_result.final_patch else None
                quality_report = metrics_engine.generate_report(
                    pr=task.pr,
                    original_code=primary_file.content,
                    patched_code=patched_code,
                    issues=all_issues,
                    repair_attempts=pipeline_result.repair_attempts,
                    rag_metrics=rag_metrics,
                    total_latency_ms=pipeline_result.total_latency_ms
                )
                task.quality_report = quality_report
                task.status = "COMPLETED"
                task.progress = 100
                task.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

                await self._broadcast(task.task_id, {
                    "type": "TASK_COMPLETED",
                    "task_id": task.task_id,
                    "status": "COMPLETED",
                    "pipeline_result": pipeline_result.model_dump(),
                    "quality_report": quality_report.model_dump()
                })

            except Exception as e:
                task.status = "FAILED"
                task.error = str(e)
                task.completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
                await self._broadcast(task.task_id, {
                    "type": "TASK_FAILED",
                    "task_id": task.task_id,
                    "error": str(e)
                })
            finally:
                self.queue.task_done()

worker_pool = ScalableWorkerPool(concurrency=4)
