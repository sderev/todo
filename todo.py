#!/usr/bin/python3


import subprocess
import click
import json
from pathlib import Path


user = subprocess.run(["whoami"], capture_output=True, text=True).stdout.strip()
TODO_FOLDER = Path(f"/home/{user}/TODO/")
if not TODO_FOLDER.is_dir():
    TODO_FOLDER.mkdir()
TODO_FILE = TODO_FOLDER / ".todos.json"


def load_todos():
    if not TODO_FILE.exists():
        TODO_FILE.touch()
        json.dump([], TODO_FILE.open("w"))
    return json.loads(TODO_FILE.read_text())

def save_todos(todos):
    json.dump(todos, TODO_FILE.open("w"))


@click.group()
def main():
    pass


@main.command()
@click.argument("task", nargs=-1)
def add(task):
    todos = load_todos()
    todos.append({"task": " ".join(task), "completed": False})
    save_todos(todos)
    click.echo(f"Task added: {' '.join(task)}")


@main.command()
def list():
    todos = load_todos()
    success_story = False

    if not todos:
        click.echo("The TODO list is empty. 🥳")
        return

    for task in todos:
        if task["completed"] == False:
            break
    else:
        success_story = True

    click.echo("")  
    for idx, task in enumerate(todos, 1):
        status = (
            "\x1b[38;5;10m✓\x1b[0m" if task["completed"] else "\x1b[38;5;9m✗\x1b[0m"
        )
        click.echo(f"{idx}. {status} {task['task']}")

    click.echo("")  
    if success_story:
        click.echo("The TODO list has been completed. 😎🥳")


@main.command()
@click.argument("indexes", type=int, nargs=-1)
def complete(indexes):
    todos = load_todos()
    for idx in indexes:
        if 1 <= idx <= len(todos):
            todos[idx - 1]["completed"] = True
            save_todos(todos)
            click.echo(f"Task completed: {todos[idx - 1]['task']}")
        else:
            click.echo("Invalid index")


@main.command()
@click.argument("indexes", type=int, nargs=-1)
def delete(indexes):
    todos = load_todos()
    tasks_to_delete = []

    for idx in indexes:
        if 1 <= idx <= len(todos):
            tasks_to_delete.append(todos[idx - 1])
        else:
            click.echo(f"Invalid index: {idx}")

    tasks_deleted = []
    for task in tasks_to_delete:
        if task in todos:
            todos.remove(task)
            tasks_deleted.append(task["task"])
    save_todos(todos)

    if tasks_deleted:
        click.echo(f"Task(s) deleted: {', '.join(tasks_deleted)}.")


@main.command()
def clear():
    json.dump([], TODO_FILE.open("w"))


if __name__ == "__main__":
    main()
