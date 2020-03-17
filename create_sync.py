"""
Simple script to generate the sync API from the async API with minimal
changes to ensure both stay in sync.
"""
import re
from pathlib import Path
from functools import partial
from typing import Callable


def _make_sub(pat: str, repl: str = '', flags: int = 0) -> Callable[[str], str]:
    """Create a regex substitution function for the given arguments."""
    return partial(re.compile(pat, flags=flags).sub, repl)  # noqa


SUBSTITUTIONS = [
    _make_sub(  # Remove asyncio import
        'import asyncio.*\n',
        flags=re.MULTILINE,
    ),
    _make_sub(  # Replace close task with simple call
        r"#.*\n\s*"
        r"aio\.get_event_loop\(\)\.create_task\(self\._client\.aclose\(\)\)",
        repl='self._client.close()',
        flags=re.MULTILINE,
    ),
    _make_sub('Async'),  # Remove Async from classes
    # Adjust thrift import paths
    _make_sub(r'contrib\.aio\.client', 'thrift'),
    _make_sub(r'contrib\.aio\.'),
    _make_sub(r'(?<!\w)(async|await)\s?'),  # Remove async/await
]

WARNING = """\
################################################################################
# WARNING: This file was autogenerated by create_sync.py. Please do not change
# it and instead make your changes to the aio subpackage and create_sync.py
# as necessary to ensure the implementations to do not diverge.
################################################################################
"""

if __name__ == '__main__':
    pkg = Path('thriftpy2_httpx_client')
    for file in (pkg / 'aio').glob('*.py'):
        sync_file = pkg / 'sync' / file.name
        code = file.read_text()
        for sub in SUBSTITUTIONS:
            code = sub(code)
        sync_file.write_text(WARNING + code)
