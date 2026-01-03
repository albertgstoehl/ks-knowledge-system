#!/usr/bin/env python3
import click
import httpx
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional

console = Console()

API_BASE_URL = "http://localhost:8000"

@click.group()
def cli():
    """Bookmark Manager CLI"""
    pass

@cli.command()
@click.argument('url')
def add(url: str):
    """Add a new bookmark"""
    try:
        response = httpx.post(f"{API_BASE_URL}/bookmarks", json={"url": url})
        response.raise_for_status()

        data = response.json()
        console.print(f"[green]✓[/green] Added bookmark: {data['url']}")
        console.print(f"  ID: {data['id']}")
        console.print(f"  State: {data['state']}")
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

@cli.command()
@click.option('--state', type=click.Choice(['inbox', 'read']), help='Filter by state')
@click.option('--limit', default=20, help='Number of results')
def list(state: Optional[str], limit: int):
    """List bookmarks"""
    params = {"limit": limit}
    if state:
        params["state"] = state

    try:
        response = httpx.get(f"{API_BASE_URL}/bookmarks", params=params)
        response.raise_for_status()

        bookmarks = response.json()

        if not bookmarks:
            console.print("[yellow]No bookmarks found[/yellow]")
            return

        table = Table(title="Bookmarks")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("State", style="magenta")
        table.add_column("URL", style="blue")

        for bm in bookmarks:
            table.add_row(
                str(bm['id']),
                bm['title'] or "Untitled",
                bm['state'],
                bm['url'][:50] + "..." if len(bm['url']) > 50 else bm['url']
            )

        console.print(table)
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

@cli.command()
@click.argument('query')
@click.option('--semantic', is_flag=True, help='Use semantic search')
@click.option('--state', type=click.Choice(['inbox', 'read']), help='Filter by state')
@click.option('--limit', default=10, help='Number of results')
def search(query: str, semantic: bool, state: Optional[str], limit: int):
    """Search bookmarks"""
    endpoint = "semantic" if semantic else "keyword"

    payload = {
        "query": query,
        "limit": limit
    }
    if state:
        payload["state"] = state

    try:
        response = httpx.post(f"{API_BASE_URL}/search/{endpoint}", json=payload)
        response.raise_for_status()

        results = response.json()

        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        table = Table(title=f"Search Results: '{query}'")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="white")
        if semantic:
            table.add_column("Score", style="green")
        table.add_column("URL", style="blue")

        for result in results:
            bm = result.get('bookmark', result)
            row = [
                str(bm['id']),
                bm['title'] or "Untitled",
            ]
            if semantic:
                row.append(f"{result['score']:.3f}")
            row.append(bm['url'][:40] + "..." if len(bm['url']) > 40 else bm['url'])

            table.add_row(*row)

        console.print(table)
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

@cli.command()
@click.argument('bookmark_id', type=int)
@click.argument('state', type=click.Choice(['inbox', 'read']))
def mark(bookmark_id: int, state: str):
    """Mark bookmark as read/inbox"""
    try:
        response = httpx.patch(
            f"{API_BASE_URL}/bookmarks/{bookmark_id}",
            json={"state": state}
        )
        response.raise_for_status()

        console.print(f"[green]✓[/green] Marked bookmark {bookmark_id} as {state}")
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

@cli.command()
@click.argument('bookmark_id', type=int)
@click.argument('description')
def set_description(bookmark_id: int, description: str):
    """Update bookmark description and regenerate embedding"""
    try:
        response = httpx.patch(
            f"{API_BASE_URL}/bookmarks/{bookmark_id}/description",
            json={"description": description}
        )
        response.raise_for_status()

        data = response.json()
        console.print(f"[green]✓[/green] Updated description for bookmark {bookmark_id}")
        console.print(f"  New description: {data['description'][:100]}...")
        console.print(f"  [dim]Embedding regenerated[/dim]")
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

@cli.command()
@click.argument('bookmark_id', type=int)
def delete(bookmark_id: int):
    """Delete a bookmark"""
    if click.confirm(f"Delete bookmark {bookmark_id}?"):
        try:
            response = httpx.delete(f"{API_BASE_URL}/bookmarks/{bookmark_id}")
            response.raise_for_status()

            console.print(f"[green]✓[/green] Deleted bookmark {bookmark_id}")
        except httpx.HTTPError as e:
            console.print(f"[red]Error:[/red] {e}")

@cli.command()
def backup():
    """Create a database backup"""
    try:
        response = httpx.post(f"{API_BASE_URL}/backup/create")
        response.raise_for_status()

        data = response.json()
        console.print(f"[green]✓[/green] Backup created: {data['path']}")
    except httpx.HTTPError as e:
        console.print(f"[red]Error:[/red] {e}")

if __name__ == '__main__':
    cli()
