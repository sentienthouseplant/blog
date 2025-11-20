# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "rich"
# ]
# ///

from rich.console import Console
from time import sleep

console = Console()

with console.status(":wave: Hello, world!") as status:
    sleep(1)