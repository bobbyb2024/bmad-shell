import asyncio
import logging
import os
from typing import TYPE_CHECKING, Any

from bmad_orch.config.schema import ResourceConfig
from bmad_orch.engine.emitter import EventEmitter
from bmad_orch.engine.events import ResourceThresholdBreached
from bmad_orch.exceptions import ResourceError

if TYPE_CHECKING:
    from bmad_orch.engine.cycle import CycleExecutor

logger = logging.getLogger(__name__)

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil library is not available. Resource monitoring will be disabled.")

class ResourceMonitor:
    def __init__(self, config: ResourceConfig, emitter: EventEmitter):
        self.config = config
        self.emitter = emitter
        self._task: asyncio.Task | None = None
        self._executor: "CycleExecutor | None" = None
        self._enabled = PSUTIL_AVAILABLE
        self._processes: dict[int, Any] = {}

    def _get_process(self, pid: int) -> Any | None:
        try:
            if pid not in self._processes:
                proc = psutil.Process(pid)
                proc.cpu_percent(interval=None)
                self._processes[pid] = proc
            return self._processes[pid]
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            self._processes.pop(pid, None)
            return None

    async def start(self, executor: "CycleExecutor"):
        if not self._enabled:
            logger.info("ResourceMonitor started in no-op mode (psutil missing or disabled).")
            return

        self._executor = executor
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("ResourceMonitor started.")

    async def stop(self):
        if self._task:
            if not self._task.done():
                self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.debug(f"ResourceMonitor task stopped with exception: {e}")
            self._task = None
        logger.info("ResourceMonitor stopped.")

    async def _poll_loop(self):
        self._get_process(os.getpid())

        while True:
            try:
                await asyncio.sleep(self.config.polling_interval)
                await self._poll()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                if isinstance(e, ResourceError):
                    raise
                logger.error(f"Error in ResourceMonitor poll loop: {e}", exc_info=True)

    async def _poll(self):
        if not self._executor:
            return

        running_pids = self._executor.running_pids
        orchestrator_pid = os.getpid()
        
        all_tracked_pids = [orchestrator_pid] + running_pids
        total_cpu = 0.0
        total_rss = 0.0
        
        process_stats = []
        active_pids = set()

        for pid in all_tracked_pids:
            proc = self._get_process(pid)
            if not proc:
                continue
                
            try:
                active_pids.add(pid)
                rss = proc.memory_info().rss
                cpu = proc.cpu_percent(interval=None)

                # Children
                try:
                    children = proc.children(recursive=True)
                    for child in children:
                        child_proc = self._get_process(child.pid)
                        if not child_proc:
                            continue
                        active_pids.add(child.pid)
                        try:
                            child_rss = child_proc.memory_info().rss
                            child_cpu = child_proc.cpu_percent(interval=None)
                            rss += child_rss
                            cpu += child_cpu
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            self._processes.pop(child.pid, None)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass

                total_rss += rss
                total_cpu += cpu

                if pid != orchestrator_pid:
                    process_stats.append({
                        "pid": pid,
                        "cpu": cpu,
                        "rss": rss
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                self._processes.pop(pid, None)

        # Cleanup dead processes
        dead_pids = set(self._processes.keys()) - active_pids
        for dead_pid in dead_pids:
            self._processes.pop(dead_pid, None)

        # Check thresholds
        try:
            memory_usage_percent = (total_rss / psutil.virtual_memory().total) * 100
        except Exception:
            memory_usage_percent = 0.0
        
        cpu_breached = total_cpu > self.config.cpu_threshold
        mem_breached = memory_usage_percent > self.config.memory_threshold
        
        if cpu_breached or mem_breached:
            resource_name = "cpu" if cpu_breached else "memory"
            current_value = total_cpu if cpu_breached else memory_usage_percent
            threshold = self.config.cpu_threshold if cpu_breached else self.config.memory_threshold
            
            self.emitter.emit(ResourceThresholdBreached(
                resource_name=resource_name,
                current_value=current_value,
                threshold=threshold
            ))
            
            logger.warning(f"Resource threshold breached: {resource_name}={current_value:.1f}% (threshold={threshold}%)")
            
            # Identify offender
            if process_stats:
                if cpu_breached:
                    offender = max(process_stats, key=lambda x: x["cpu"])
                else:
                    offender = max(process_stats, key=lambda x: x["rss"])
                
                offender_pid = offender["pid"]
                logger.error(f"Killing offending subprocess tree (PID {offender_pid}) due to resource breach.")
                
                self._executor.mark_intentional_kill(offender_pid)
                
                try:
                    proc = psutil.Process(offender_pid)
                    try:
                        children = proc.children(recursive=True)
                        for child in children:
                            try:
                                child.kill()
                            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                                continue
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        pass
                    proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                
                raise ResourceError(f"Resource breach ({resource_name}): Killed subprocess {offender_pid}")
            else:
                logger.critical("Orchestrator itself is exceeding resource thresholds!")
                raise ResourceError(f"Resource breach ({resource_name}): Orchestrator exceeding threshold")
