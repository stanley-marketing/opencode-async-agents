# Hire Employee Task

## Purpose

To allow users to hire specialized employees from different fields (engineering, design, product, etc.) who are masters in their own field. This task provides a structured way to discover, select, and "hire" these specialized employees.

## Processing Flow

### 1. Identify Employee Category

If the user hasn't specified an employee category:
- List all available categories from .bmad-core/employee-types/
- Ask the user to select a category

If the user has specified a category:
- Verify the category exists
- If not, list available categories and ask for selection

### 2. List Available Employee Types

- Show all employee types in the selected category
- Display brief descriptions of each employee type
- Allow user to select an employee type

### 3. Load and Present Employee Details

- Load the employee prompt from .bmad-core/employee-types/{category}/{employee-type}.md
- Present the employee's capabilities and expertise
- Show what tasks they can perform

### 4. Confirm Hiring

- Ask user to confirm they want to hire this employee
- Explain that hiring means loading this employee's prompt for use
- Provide options for how to use the employee (direct task assignment, consultation, etc.)

## Available Employee Categories

- engineering: Software engineers, backend architects, frontend developers, etc.
- design: UI/UX designers, visual storytellers, brand guardians, etc.
- product: Product managers, sprint prioritizers, trend researchers, etc.
- testing: QA specialists, test automation engineers, performance benchmarkers, etc.
- project-management: Project coordinators, studio producers, experiment trackers, etc.

## Implementation Notes

When executing this task:
1. Always list available options in numbered format
2. Wait for explicit user selection before proceeding
3. Load employee prompts directly from .bmad-core/employee-types/
4. Present the full employee prompt to the user for review
5. Allow user to accept or reject the employee

## YOLO Mode

In YOLO mode, the task will:
1. List all available employee categories and types
2. Allow user to quickly select and hire without detailed review
3. Still require final confirmation before completing the hire