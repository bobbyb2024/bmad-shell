import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from bmad_orch.config.schema import ResourceConfig
from bmad_orch.engine.emitter import EventEmitter
from bmad_orch.engine.resources import ResourceMonitor
from bmad_orch.exceptions import ResourceError
from bmad_orch.engine.events import ResourceThresholdBreached

@pytest.fixture
def resource_config():
    return ResourceConfig(polling_interval=0.1, cpu_threshold=80.0, memory_threshold=80.0)

@pytest.fixture
def emitter():
    return EventEmitter()

@pytest.fixture
def executor():
    mock = MagicMock()
    mock.running_pids = [123, 456]
    mock._intentional_kills = set()
    mock.mark_intentional_kill = lambda pid: mock._intentional_kills.add(pid)
    return mock

@pytest.mark.asyncio
async def test_resource_monitor_start_stop(resource_config, emitter, executor):
    with patch("bmad_orch.engine.resources.psutil") as mock_psutil:
        monitor = ResourceMonitor(resource_config, emitter)
        await monitor.start(executor)
        assert monitor._task is not None
        await monitor.stop()
        assert monitor._task is None

@pytest.mark.asyncio
async def test_resource_monitor_no_op_mode(resource_config, emitter, executor):
    with patch("bmad_orch.engine.resources.PSUTIL_AVAILABLE", False):
        monitor = ResourceMonitor(resource_config, emitter)
        await monitor.start(executor)
        assert monitor._task is None
        await monitor.stop()

@pytest.mark.asyncio
async def test_resource_monitor_threshold_breach_cpu(resource_config, emitter, executor):
    with patch("bmad_orch.engine.resources.psutil") as mock_psutil:
        class NoSuchProcess(Exception): pass
        class AccessDenied(Exception): pass
        class ZombieProcess(Exception): pass
        mock_psutil.NoSuchProcess = NoSuchProcess
        mock_psutil.AccessDenied = AccessDenied
        mock_psutil.ZombieProcess = ZombieProcess

        # Mock virtual memory to return something sensible
        mock_psutil.virtual_memory().total = 1000
        
        # Mock processes
        # Orchestrator (PID 1000)
        mock_orch = MagicMock()
        mock_orch.memory_info().rss = 100
        mock_orch.cpu_percent.return_value = 10.0
        mock_orch.children.return_value = []
        
        # Subprocess 1 (PID 123)
        mock_p1 = MagicMock()
        mock_p1.memory_info().rss = 200
        mock_p1.cpu_percent.return_value = 80.0 # This breaches 80%
        mock_p1.children.return_value = []
        
        # Subprocess 2 (PID 456)
        mock_p2 = MagicMock()
        mock_p2.memory_info().rss = 50
        mock_p2.cpu_percent.return_value = 5.0
        mock_p2.children.return_value = []
        
        def mock_process(pid):
            if pid == 1000: return mock_orch
            if pid == 123: return mock_p1
            if pid == 456: return mock_p2
            raise Exception("NoSuchProcess")
            
        mock_psutil.Process.side_effect = mock_process
        
        with patch("os.getpid", return_value=1000):
            monitor = ResourceMonitor(resource_config, emitter)
            # Pre-initialization is no longer needed because _get_process handles it naturally.

            # Use a mock emitter to capture events
            events = []
            emitter.subscribe(ResourceThresholdBreached, lambda e: events.append(e))

            # Run one poll manually
            monitor._executor = executor
            with pytest.raises(ResourceError) as excinfo:
                await monitor._poll()
            
            assert "Resource breach (cpu)" in str(excinfo.value)
            assert len(events) == 1
            assert events[0].resource_name == "cpu"
            assert events[0].current_value >= 80.0
            
            # Verify offender was killed
            assert 123 in executor._intentional_kills
            mock_p1.kill.assert_called_once()

@pytest.mark.asyncio
async def test_resource_monitor_threshold_breach_memory(resource_config, emitter, executor):
    with patch("bmad_orch.engine.resources.psutil") as mock_psutil:
        class NoSuchProcess(Exception): pass
        class AccessDenied(Exception): pass
        class ZombieProcess(Exception): pass
        mock_psutil.NoSuchProcess = NoSuchProcess
        mock_psutil.AccessDenied = AccessDenied
        mock_psutil.ZombieProcess = ZombieProcess

        # Mock virtual memory: total 1000, threshold 80% = 800
        mock_psutil.virtual_memory().total = 1000
        
        # Mock processes
        # Orchestrator (PID 1000)
        mock_orch = MagicMock()
        mock_orch.memory_info().rss = 100
        mock_orch.cpu_percent.return_value = 1.0
        mock_orch.children.return_value = []
        
        # Subprocess 1 (PID 123)
        mock_p1 = MagicMock()
        mock_p1.memory_info().rss = 800 # This breaches 80% (total 100+800=900)
        mock_p1.cpu_percent.return_value = 1.0
        mock_p1.children.return_value = []
        
        mock_psutil.Process.side_effect = lambda pid: mock_orch if pid == 1000 else mock_p1
        
        with patch("os.getpid", return_value=1000):
            monitor = ResourceMonitor(resource_config, emitter)
            # Pre-initialization is no longer needed because _get_process handles it naturally.
            monitor._executor = executor

            with pytest.raises(ResourceError) as excinfo:
                await monitor._poll()

            assert "Resource breach (memory)" in str(excinfo.value)
            assert 123 in executor._intentional_kills

@pytest.mark.asyncio
async def test_resource_monitor_handles_nosuchprocess(resource_config, emitter, executor):
    with patch("bmad_orch.engine.resources.psutil") as mock_psutil:
        class NoSuchProcess(Exception): pass
        class AccessDenied(Exception): pass
        class ZombieProcess(Exception): pass
        mock_psutil.NoSuchProcess = NoSuchProcess
        mock_psutil.AccessDenied = AccessDenied
        mock_psutil.ZombieProcess = ZombieProcess

        mock_psutil.virtual_memory().total = 1000
        mock_psutil.Process.side_effect = NoSuchProcess() # Simulate all processes gone

        monitor = ResourceMonitor(resource_config, emitter)
        monitor._executor = executor

        # Should not raise exception
        await monitor._poll()

@pytest.mark.asyncio
async def test_resource_monitor_handles_zombie_process(resource_config, emitter, executor):
    with patch("bmad_orch.engine.resources.psutil") as mock_psutil:
        class NoSuchProcess(Exception): pass
        class AccessDenied(Exception): pass
        class ZombieProcess(Exception): pass
        mock_psutil.NoSuchProcess = NoSuchProcess
        mock_psutil.AccessDenied = AccessDenied
        mock_psutil.ZombieProcess = ZombieProcess

        mock_psutil.virtual_memory().total = 1000
        mock_psutil.Process.side_effect = ZombieProcess() # Simulate zombie processes

        monitor = ResourceMonitor(resource_config, emitter)
        monitor._executor = executor

        # Should not raise exception
        await monitor._poll()

@pytest.mark.asyncio
async def test_runner_integrates_resource_monitor(resource_config, emitter, executor):
    with patch("bmad_orch.engine.resources.psutil") as mock_psutil:
        class NoSuchProcess(Exception): pass
        class AccessDenied(Exception): pass
        class ZombieProcess(Exception): pass
        mock_psutil.NoSuchProcess = NoSuchProcess
        mock_psutil.AccessDenied = AccessDenied
        mock_psutil.ZombieProcess = ZombieProcess
        mock_psutil.virtual_memory.return_value.total = 1000

        # Mock a breach in the first poll
        mock_orch = MagicMock()
        mock_orch.memory_info.return_value.rss = 100
        mock_orch.cpu_percent.return_value = 100.0 # Breach!
        mock_orch.children.return_value = []
        mock_psutil.Process.return_value = mock_orch
        
        from bmad_orch.engine.runner import Runner
        from bmad_orch.config.schema import OrchestratorConfig, GitConfig, PauseConfig, ErrorConfig, ProviderConfig, CycleConfig, StepConfig
        from bmad_orch.types import StepType
        
        config = OrchestratorConfig(
            providers={1: ProviderConfig(name="test", cli="test", model="test")},
            cycles={"test": CycleConfig(steps=[StepConfig(skill="test", provider=1, type=StepType.GENERATIVE, prompt="test")])},
            git=GitConfig(enabled=False),
            pauses=PauseConfig(between_steps=0, between_cycles=0, between_workflows=0),
            error_handling=ErrorConfig(max_retries=1),
            resources=resource_config
        )
        
        runner = Runner(config)
        runner.adapter_factory = MagicMock()
        
        # We want to verify that run() eventually calls _handle_impactful_error 
        # when the monitor raises ResourceError
        with patch.object(runner, "_handle_impactful_error", new_callable=AsyncMock) as mock_handle:
            # We need to mock _init_git and other things that might fail
            runner._init_git = AsyncMock()
            
            # Mock executor.execute_cycle to wait a bit
            async def slow_cycle(*args, **kwargs):
                await asyncio.sleep(1.0)
                return MagicMock()
            
            with patch("bmad_orch.engine.runner.CycleExecutor") as mock_executor_cls:
                mock_executor = mock_executor_cls.return_value
                mock_executor.execute_cycle.side_effect = slow_cycle
                mock_executor.running_pids = []
                
                with pytest.raises(ResourceError):
                    await runner.run()
                
                mock_handle.assert_called_once()
