import asyncio
import codecs
import errno
import fcntl
import os
import signal
import time
from collections.abc import AsyncIterator

from bmad_orch.exceptions import ProviderCrashError, ProviderTimeoutError
from bmad_orch.types import OutputChunk


async def spawn_pty_process(
    cmd: list[str], timeout: float = 30.0, env: dict[str, str] | None = None, grace_period: float = 2.0
) -> AsyncIterator[OutputChunk]:
    """Spawn a process in a PTY and yield output chunks."""
    if os.name != "posix":
        raise NotImplementedError("spawn_pty_process is only supported on POSIX.")

    master_fd, slave_fd = os.openpty()

    # Set master_fd to non-blocking
    flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
    fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=False,  # Keep FDs open for child
            start_new_session=True,
            env=env,
        )
    finally:
        # We MUST close slave_fd in the parent process as soon as child has it
        os.close(slave_fd)

    queue: asyncio.Queue[bytes | Exception | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def read_callback() -> None:
        try:
            data = os.read(master_fd, 4096)
            if not data:
                # EOF
                loop.remove_reader(master_fd)
                queue.put_nowait(None)
            else:
                queue.put_nowait(data)
        except (BlockingIOError, InterruptedError):
            pass
        except OSError as e:
            if e.errno == errno.EIO:
                # EIO means slave closed, treat as EOF
                loop.remove_reader(master_fd)
                queue.put_nowait(None)
            else:
                loop.remove_reader(master_fd)
                queue.put_nowait(e)
        except Exception as e:
            loop.remove_reader(master_fd)
            queue.put_nowait(e)

    loop.add_reader(master_fd, read_callback)

    start_time = time.time()
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    
    try:
        while True:
            elapsed = time.time() - start_time
            remaining = max(0.0, timeout - elapsed)
            if remaining <= 0:
                raise TimeoutError()

            try:
                # Wait for data or timeout
                data = await asyncio.wait_for(queue.get(), timeout=remaining)
                if data is None:
                    # EOF
                    break
                if isinstance(data, Exception):
                    raise data

                text = decoder.decode(data, final=False)
                if text:
                    yield OutputChunk(content=text, timestamp=time.time())

            except TimeoutError:
                # Handle total timeout reached — kill entire process group
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=grace_period)
                except TimeoutError:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except (ProcessLookupError, PermissionError):
                        process.kill()
                    await process.wait()
                raise ProviderTimeoutError(f"Process {cmd} timed out after {timeout}s") from None

        await process.wait()
        if process.returncode != 0:
            raise ProviderCrashError(
                f"Process {cmd} failed with exit code {process.returncode}"
            )

    finally:
        loop.remove_reader(master_fd)
        try:
            os.close(master_fd)
        except OSError:
            pass

        if process.returncode is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=grace_period)
            except TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    process.kill()
                await process.wait()
