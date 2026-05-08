## ADDED Requirements

### Requirement: Shared Project AppShell
The frontend SHALL render project workspace pages with one shared AppShell containing a white sidebar, primary navigation, recent project list, bottom actions, top project header, and light gray page background.

#### Scenario: Agent and dashboard share shell
- **WHEN** a user navigates between `/projects/{project_id}/agent` and `/projects/{project_id}/dashboard`
- **THEN** the sidebar, top project header, project title, navigation labels, background, and brand colors remain consistent while only the main page content changes

#### Scenario: Active navigation state
- **WHEN** the current route is `/projects/{project_id}/agent`
- **THEN** the "Agent 分析" navigation item is highlighted

#### Scenario: Dashboard active navigation state
- **WHEN** the current route is `/projects/{project_id}/dashboard`
- **THEN** the "结果看板" navigation item is highlighted

### Requirement: Agent Analysis Workspace
The frontend SHALL render the Agent analysis page as a conversation-driven workspace with a page header, quick prompts, conversation stream, message composer, and right-side run inspector.

#### Scenario: Message-first prompt submission
- **WHEN** a user sends a message from the Agent composer
- **THEN** the frontend sends the prompt through the existing message runtime path and does not create an Agent run directly from the page

#### Scenario: Runtime events visible
- **WHEN** assistant messages, tool calls, approvals, job progress, artifacts, or errors arrive from the event stream
- **THEN** the page displays the corresponding conversation cards and inspector state without leaving the Agent analysis layout

### Requirement: Result Dashboard Workspace
The frontend SHALL render the result dashboard with a filter bar, core conclusion banner, KPI summary strip, chart grid, recommendation panel, drill-down drawer, and export modal.

#### Scenario: Dashboard overview loads
- **WHEN** a user opens `/projects/{project_id}/dashboard`
- **THEN** the page displays the core conclusion, four KPI cards, Pareto chart, LocalGap waterfall, GMV trend comparison, strategy quadrant, and four recommendation groups

#### Scenario: Drill-down interaction
- **WHEN** a user clicks a KPI card, chart element, quadrant bubble, or recommendation category tag
- **THEN** the dashboard opens a drill-down drawer with detail KPIs, trend context, contribution table, and a method explanation panel

#### Scenario: Export interaction
- **WHEN** a user clicks the dashboard export button
- **THEN** the dashboard opens an export modal with format and scope selectors

### Requirement: Ratio-Aware One-Page Fit
The frontend SHALL fit dense Agent and dashboard canvases to the available page ratio so the complete designed content fills the page content area without vertical page scrolling.

#### Scenario: Arbitrary desktop content fit
- **WHEN** a user opens the Agent analysis page or result dashboard using a wide, narrow, tall, or short desktop viewport
- **THEN** the main content canvas scales according to the available page width-height ratio, fills the page content area, and remains fully visible

#### Scenario: Stable scale after refresh
- **WHEN** the page has calculated its scale after a user refresh or route entry
- **THEN** subsequent content rendering, resize observer activity, or minor layout changes do not continuously recalculate the scale

#### Scenario: Overlay usability
- **WHEN** the dashboard drill-down drawer or export modal is opened
- **THEN** the overlay renders outside the scaled canvas and keeps normal viewport-relative sizing
