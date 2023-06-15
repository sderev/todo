# TODO CLI Tool

This is a command-line interface (CLI) tool for managing a TODO list. It supports adding tasks, marking tasks as completed, deleting tasks, listing all tasks, and even managing a list of daily tasks.

<!-- TOC -->
## Table of Contents

1. [Installation](#installation)
1. [Usage](#usage)
1. [Daily Tasks](#daily-tasks)
1. [Command Completion](#command-completion)
    1. [Bash](#bash)
    1. [Zsh](#zsh)
<!-- /TOC -->

## Installation

1. Make sure you have Python 3.6 or later installed.
2. Clone this repository to your local machine.

    ```sh
    git clone https://github.com/sderev/todo
    ```

3. Add the repository to your system's PATH.

    To add the repository to your system's PATH, you may need to modify your system's shell configuration file (like `~/.bashrc`, `~/.bash_profile`, or `~/.zshrc`), and add a line like the following, adjusting the path to match where you cloned the repository:

    ```bash
    export PATH=$PATH:/path/to/cloned/repository
    ```

    **OR**

    * Create a symbolic link somewhere in your PATH to the `todo` file in the repository.

        ```bash
        ln -s /path/to/cloned/repository $PATH:/todo
        ```

        Replace `$PATH:/` with a folder in your PATH.

After this, the script can be run from any location on the command line as follows:

```bash
todo add "Learn about Podman containers"
```

## Usage

Here are the available commands:

* Add a new task: `todo add "Buy groceries"`
* List all tasks: `todo list`
* Mark tasks as completed: `todo complete 1 2`
* Delete tasks: `todo delete 1 2`
* Clear all tasks: `todo clear`
* Add daily tasks: `todo daily`

## Daily Tasks

You can create a list of daily tasks to be added automatically. These tasks should be written in a file named `daily_tasks.txt` located in the `~/TODO/` directory. The tasks should be written one per line.

Please note that the path to the `daily_tasks.txt` file is hardcoded. If you need to use a different path, you will need to modify the `daily()` function in the script.

## Command Completion

In the `completion` directory of the repo, you will find completion files for bash and zsh. To use these, follow the instructions specific to your shell:

### Bash

Copy the `todo-completion.bash` file to the `/etc/bash_completion.d/` directory:

```bash
sudo cp completion/todo-completion.bash /etc/bash_completion.d/todo
```

### Zsh

Source the `todo-completion.zsh` file in your `~/.zshrc` file:

```bash
echo "source /path/to/cloned/repository/completion/todo-completion.zsh" >> ~/.zshrc
```

Remember to replace `/path/to/cloned/repository` with the actual path to the cloned repository.

