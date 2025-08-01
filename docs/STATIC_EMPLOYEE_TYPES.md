# Static Employee Types Feature

This feature allows users to hire specialized employees from different fields who are masters in their own field.

## Overview

The static employee types feature provides a structured way to discover, select, and "hire" specialized employees from various categories including:
- Engineering (frontend developers, backend architects, AI engineers, etc.)
- Design (UI/UX designers, visual storytellers, brand guardians, etc.)
- Product (product managers, sprint prioritizers, trend researchers, etc.)
- Testing (QA specialists, test automation engineers, performance benchmarkers, etc.)
- Project Management (project coordinators, studio producers, experiment trackers, etc.)

## Implementation Details

### Directory Structure

The employee types are organized in the following directory structure:
```
.bmad-core/
  employee-types/
    engineering/
      ai-engineer.md
      backend-architect.md
      devops-automator.md
      frontend-developer.md
      mobile-app-builder.md
      rapid-prototyper.md
      test-writer-fixer.md
    design/
      brand-guardian.md
      ui-designer.md
      ux-researcher.md
      visual-storyteller.md
      whimsy-injector.md
    product/
      feedback-synthesizer.md
      sprint-prioritizer.md
      trend-researcher.md
    testing/
      api-tester.md
      performance-benchmarker.md
      test-results-analyzer.md
      tool-evaluator.md
      workflow-optimizer.md
    project-management/
      experiment-tracker.md
      project-shipper.md
      studio-producer.md
```

### New CLI Command

A new command `hire-specialist` has been added to the CLI server:

```
hire-specialist [category]
```

When called without arguments, it lists all available categories. When called with a category, it lists all available employee types in that category.

### Integration with BMAD System

The feature integrates with the existing BMAD system by:
1. Adding the `hire-employee.md` task to the dependencies
2. Updating the BMAD master configuration to include the new hire command
3. Creating a mapping between user requests and specialized employee types

## Usage Examples

1. List all available employee categories:
   ```
   hire-specialist
   ```

2. List all engineering specialists:
   ```
   hire-specialist engineering
   ```

3. Hire a frontend developer:
   ```
   hire john frontend-developer smart
   ```

## Future Enhancements

1. Integration with the BMAD master agent to allow hiring through the `*hire` command
2. Automatic loading of employee prompts when hiring specialized employees
3. Enhanced matching algorithm to suggest the best employee type based on task description