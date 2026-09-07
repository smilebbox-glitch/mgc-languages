# Engineering Project Workspace — v3.9.0

## Purpose

The Project Workspace is the project-level shell above Part 360, document/CAD intelligence, Design Review and ECR/ECO. It is designed for engineers and engineering managers who need one answer to: **what is in this project, what is blocking it, and what needs attention before a release decision?**

## Project contents

A project can define:

- project code and name;
- engineering owner;
- phase and status;
- root part/assembly number;
- target release date;
- project ACL groups;
- engineering milestones.

The workspace then derives, from existing authoritative records:

- visible parts and documents;
- BOM-based assembly tree;
- open validation issues;
- active ECR/ECO;
- latest Design Reviews;
- project milestones;
- a recent project timeline.

## Release-readiness indicator

The indicator is deterministic and explainable. Current weights are:

| Gate | Weight |
|---|---:|
| Documentation | 35% |
| Quality / validation issues | 25% |
| Engineering changes | 20% |
| Design Reviews | 10% |
| Milestones | 10% |

The service reports every gate separately as well as the combined score. Critical validation issues, failed project documents and urgent/critical open changes appear as blockers. Overdue milestones appear as review blockers.

### Important governance rule

`readiness.advisory_only = true` and `human_release_approval_required = true` are returned by the API. A high score is **not** a release authorization. Final release remains a controlled human decision under the company's engineering process.

## ACL behavior

Project ACL controls who can see the project shell. It does **not** expand access to underlying evidence. Document ACL remains authoritative. A user who can see a project but cannot see a restricted drawing cannot receive that drawing's derived issue/part evidence through the Project Workspace.

## Assembly tree

The assembly tree is reconstructed from visible BOM evidence and the configured `root_part_number`. Traversal is bounded and cycle-safe. If no root assembly or visible BOM exists, the UI shows that the tree is not available rather than inventing structure.

## API

- `GET /api/v1/projects`
- `POST /api/v1/projects` — engineering admin
- `PATCH /api/v1/projects/{project_code}` — engineering admin
- `GET /api/v1/projects/{project_code}/workspace`
- `POST /api/v1/projects/{project_code}/milestones`
- `PATCH /api/v1/projects/{project_code}/milestones/{milestone_id}`

All human-facing routes require engineer identity. Project creation/settings require Engineering Admin. Milestone state changes require project visibility and are recorded in the audit log.
