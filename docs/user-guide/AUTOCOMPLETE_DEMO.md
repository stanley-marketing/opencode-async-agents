# Autocomplete Demo

## How to use autocomplete in the CLI

1. Start the CLI server:
   ```
   python3 src/cli_server.py
   ```

2. Once the CLI is running, you can use TAB completion:
   - Type the first few letters of a command and press TAB to complete the command name
   - Press TAB twice to see all available completions
   - After typing a command and a space, press TAB to get context-sensitive argument completion

## Available commands for autocomplete:

- help
- quit / exit
- hire
- fire
- assign / start
- stop
- status
- sessions
- lock
- release
- request
- approve
- deny
- progress
- task
- cleanup
- chat
- chat-start
- chat-stop
- chat-status
- agents
- bridge
- employees
- files
- clear
- history
- models
- model-set

## Context-sensitive argument completion:

### hire command:
- Type `hire` + TAB to complete the command
- Type `hire ` (with space) + TAB to get help with syntax
- Type `hire <name> ` (with space) + TAB to suggest common roles: developer, analyst, pm, qa, devops, designer
- Type `hire <name> <role> ` (with space) + TAB to suggest smartness levels: smart, normal

### fire/assign/start/stop/progress/task commands:
- Type `fire ` (with space) + TAB to suggest existing employee names from the database
- Type `fire jo` + TAB to complete employee names starting with "jo"

### lock command:
- Type `lock ` (with space) + TAB to suggest existing employee names
- Type `lock <name> ` (with space) + TAB to suggest common file paths

### release command:
- Type `release ` (with space) + TAB to suggest existing employee names
- Type `release <name> ` (with space) + TAB to suggest files currently locked by that employee

### request command:
- Type `request ` (with space) + TAB to suggest existing employee names
- Type `request <name> ` (with space) + TAB to suggest common file paths

### approve/deny commands:
- Type `approve ` (with space) + TAB to suggest pending request IDs
- Type `deny ` (with space) + TAB to suggest pending request IDs

### model-set command:
- Type `model-set ` (with space) + TAB to suggest levels: smart, normal

## Examples:

1. Type "h" then press TAB twice to see all commands starting with "h"
2. Type "sta" then press TAB to complete to "start"
3. Type "fire " then press TAB to see existing employee names
4. Type "fire john" then press TAB to complete the employee name
5. Type "lock sarah " then press TAB to see common file paths
6. Type "hire " then press TAB to get help with the command syntax

The enhanced autocomplete feature makes it easier to use the CLI by reducing typos and providing quick access to available commands and context-sensitive argument completion exactly as you type.