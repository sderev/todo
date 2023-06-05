#!/usr/bin/python3


import click
import json
from pathlib import Path


@click.group()
def main():
    pass


def setup_dir_and_file(TODO_FOLDER, TODO_FILE):
    """Creates folder and json file if they don't exist yet."""
    TODO_FOLDER.mkdir(exist_ok=True, parents=True)
    if not TODO_FILE.exists():
        json.dump([], TODO_FILE.open("w"))


def load_todos():
    return json.loads(TODO_FILE.read_text())


def save_todos(todos):
    json.dump(todos, TODO_FILE.open("w"))


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

    if not todos:
        click.echo("The TODO list is empty. 🥳")
        return

    click.echo("")

    GREEN = "\x1b[38;5;10m"
    RED = "\x1b[38;5;9m"
    RESET = "\x1b[0m"
    for idx, task in enumerate(todos, 1):
        status = f"{GREEN}✓{RESET}" if task["completed"] else f"{RED}✗{RESET}"
        click.echo(f"{idx}. {status} {task['task']}")

    click.echo("")
    if all(task["completed"] for task in todos):
        click.echo("The TODO list has been completed. 😎🥳")


def invalid_indexes(indexes):
    invalid_indexes = [idx for idx in indexes if idx < 1 or idx > len(load_todos())]
    if invalid_indexes:
        click.echo(f"Invalid index(es): {', '.join(map(str, invalid_indexes))}")
    return invalid_indexes


def valid_indexes(indexes):
    invalid = invalid_indexes(indexes)
    return [idx for idx in indexes if idx not in invalid]


@main.command()
@click.argument("indexes", type=int, nargs=-1)
def complete(indexes):
    todos = load_todos()
    tasks = valid_indexes(indexes)
    for idx in tasks:
        if not todos[idx - 1]["completed"]:
            todos[idx - 1]["completed"] = True
            save_todos(todos)
            click.echo(f"Task completed: {todos[idx - 1]['task']}")
        else:
            click.echo(f"Task already completed: {todos[idx - 1]['task']}")


@main.command()
@click.argument("indexes", type=int, nargs=-1)
def delete(indexes):
    todos = load_todos()
    tasks_to_delete = []

    tasks = valid_indexes(indexes)
    for idx in tasks:
        tasks_to_delete.append(todos[idx - 1])

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
    click.echo("The TODO list has been cleared.")


@main.command()
def daily():
    try:
        with open("/home/sebastien/TODO/daily_tasks.txt", "r") as file:
            daily_tasks = [task.strip() for task in file.readlines()]
    except FileNotFoundError:
        click.echo("No ~/TODO/daily_tasks.txt file found.")
    else:
        for task in daily_tasks:
            todos = load_todos()
            todos.append({"task": task, "completed": False})
            save_todos(todos)
            click.echo(f"Task added: {task}")


TODO_FOLDER = Path.home() / "TODO"
TODO_FILE = TODO_FOLDER / ".todos.json"


if __name__ == "__main__":
    setup_dir_and_file(TODO_FOLDER, TODO_FILE)
    main()

