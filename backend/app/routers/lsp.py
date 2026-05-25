import shutil
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lsp", tags=["LSP"])

@router.websocket("")
async def lsp_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    sqls_path = shutil.which("sqls")
    if sqls_path is None:
        await websocket.send_json({
            "status": "error",
            "code": "LSP_BINARY_MISSING",
            "message": "sqls binary not found"
        })
        await websocket.close()
        return

    try:
        # Spawn the language server process using asyncio
        process = await asyncio.create_subprocess_exec(
            sqls_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
    except Exception as e:
        logger.error(f"Failed to spawn sqls language server: {str(e)}")
        await websocket.send_json({
            "status": "error",
            "code": "LSP_SPAWN_FAILED",
            "message": f"Failed to spawn sqls process: {str(e)}"
        })
        await websocket.close()
        return

    async def read_from_ws():
        try:
            while True:
                data = await websocket.receive_text()
                if process.stdin and process.returncode is None:
                    process.stdin.write(data.encode('utf-8'))
                    await process.stdin.drain()
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error(f"WebSocket read error: {str(e)}")
        finally:
            if process.returncode is None:
                try:
                    process.terminate()
                except Exception:
                    pass

    async def read_from_proc():
        try:
            while True:
                if process.stdout and process.returncode is None:
                    # Read chunks of bytes as they arrive from the language server stdout
                    data = await process.stdout.read(65536)
                    if not data:
                        break
                    await websocket.send_text(data.decode('utf-8'))
                else:
                    break
        except Exception as e:
            logger.error(f"Process stdout read error: {str(e)}")
        finally:
            try:
                await websocket.close()
            except Exception:
                pass

    try:
        # Run read from WS and read from Subprocess concurrently
        await asyncio.gather(read_from_ws(), read_from_proc())
    except Exception as e:
        logger.error(f"LSP proxy loop terminated: {str(e)}")
    finally:
        if process.returncode is None:
            try:
                process.terminate()
            except Exception:
                pass
