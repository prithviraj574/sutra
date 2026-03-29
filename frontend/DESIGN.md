web application/stitch/projects/3438999353497193178/screens/5ab2600fb2384dec9cd8f0c3fe1a569a
# Sutra - Ethereal Minimalism

## Product Overview

**The Pitch:** Sutra is an autonomous AI collaboration platform where users orchestrate swarms of agents through a primary chat modality to build custom software on the fly. It transforms complex multi-agent workflows into a serene, frictionless conversation, materializing fully functional applications directly alongside the dialogue.

**For:** Technical founders, product managers, and orchestrators who demand zero-friction execution and value high-signal, low-noise environments.

**Device:** desktop

**Design Direction:** Ethereal Minimalism. Absolute typographical clarity and expansive whitespace grounded by sparse, breathtaking auras of a high-altitude sunset gradient to indicate agent activity and system state.

**Inspired by:** Claude, Linear, Vercel

---

## Screens

- **Hub:** Command center showing active agent swarms and recent workspace sessions
- **Chat Canvas:** Dual-pane interface with conversational thread and dynamic rendering surface
- **Agent Assembly:** Node-less, configuration-driven builder for assigning roles and toolsets to specific agents
- **Artifact View:** Immersive, distraction-free environment for interacting with on-the-fly generated software

---

## Key Flows

**Orchestrating a new workflow:** Generates custom software from a single prompt

1. User is on **Hub** -> sees floating `+ Initialize Session` input
2. User clicks **input** and types prompt -> enters **Chat Canvas**
3. System responds, subtle sunset aura glows around the active agent avatar -> dynamically renders UI in the right panel

---

## Design System

### Color Palette

- **Primary:** `#111111` - Primary buttons, heavy text, active states
- **Background:** `#FDFCFB` - Main application background (warm pearl)
- **Surface:** `#F4F4F0` - Chat bubbles, secondary sidebars, input fields
- **Text:** `#222222` - Primary readability
- **Muted:** `#888883` - Timestamps, placeholder text, subtle borders
- **Accent (Aura Gradient):** `linear-gradient(135deg, #3B82F6 0%, #8B5CF6 35%, #F97316 70%, #FCD34D 100%)` - Agent thinking states, active artifact borders, primary CTA hover states

### Typography

Distinctive, editorial typography paired with razor-sharp geometric sans for data.

- **Headings:** `Newsreader`, 400, 24-32px, tracking `-0.02em`
- **Body:** `Satoshi`, 400, 15px, leading `1.6`
- **Small text:** `Satoshi`, 500, 12px, uppercase, tracking `0.05em`
- **Code/Data:** `JetBrains Mono`, 400, 13px

**Style notes:** Zero drop shadows on standard elements. Depth is achieved entirely through background color shifts (`#FDFCFB` to `#F4F4F0`) and 1px borders (`#E5E5E0`). The "sunset aura" is applied as a highly blurred background behind active elements (`filter: blur(24px)`) or as a 1px solid gradient border. Sharp `4px` border radius on all elements for a precise, engineered feel.

### Design Tokens

```css
:root {
  --color-primary: #111111;
  --color-background: #FDFCFB;
  --color-surface: #F4F4F0;
  --color-text: #222222;
  --color-muted: #888883;
  --color-border: #E5E5E0;
  --gradient-sunset: linear-gradient(135deg, #3B82F6, #8B5CF6, #F97316, #FCD34D);
  --font-serif: 'Newsreader', serif;
  --font-sans: 'Satoshi', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --radius: 4px;
  --spacing-base: 8px;
}
```

---

## Screen Specifications

### Hub

**Purpose:** The entry point. Calm overview of past and current agent sessions.

**Layout:** Single centered column, max-width `800px`, heavy top padding (`120px`).

**Key Elements:**
- **Omnibox:** `64px` height, `4px` radius, `#F4F4F0` background. `Newsreader` `20px` placeholder text.
- **Session List:** Vertical list. `1px` bottom border `#E5E5E0`.
- **Status Indicator:** `6px` dot. Uses `--gradient-sunset` when swarm is active.

**States:**
- **Empty:** "No active sessions." centered, `Satoshi`, `14px`, `#888883`.
- **Loading:** Skeleton pulses `#F4F4F0` to `#E5E5E0`.
- **Error:** `1px` red border `#FF4444` on omnibox.

**Components:**
- **Session Row:** `64px` height, `#FDFCFB`, title left, timestamp right.

**Interactions:**
- **Click Session Row:** Routes to Chat Canvas.
- **Hover Omnibox:** `1px` solid border transition to `#111111`.

**Responsive:**
- **Desktop:** `800px` centered.
- **Tablet:** `90%` width.
- **Mobile:** `100%` width, `16px` padding.

### Chat Canvas

**Purpose:** The core working environment for agent orchestration and software rendering.

**Layout:** Split pane. Left `45%` (Chat), Right `55%` (Canvas). Separated by `1px` `#E5E5E0` border.

**Key Elements:**
- **Chat Feed:** Scrollable area. User messages right-aligned (`#F4F4F0` background), Agent messages left-aligned (transparent background).
- **Composer:** Fixed at bottom left. `auto-expand` textarea.
- **Canvas Area:** Renders the generated UI. `1px` border `--gradient-sunset` when updating.

**States:**
- **Agent Thinking:** A `32px` avatar circle pulses with `--gradient-sunset` and `blur(8px)`.
- **Canvas Empty:** Centered text "Awaiting artifact generation...", `14px`, `#888883`.

**Components:**
- **Message Bubble:** `15px` `Satoshi`, `24px` line-height, `16px` padding, `4px` radius.
- **Agent Avatar:** `32px` square, `4px` radius, `#111111` background, white monogram.

**Interactions:**
- **Focus Composer:** Border `#111111`.
- **Agent Resolves:** Sunset gradient flashes briefly at `0.2` opacity across Canvas area, fading in `400ms`.

**Responsive:**
- **Desktop:** Side-by-side split.
- **Tablet:** Stacked, Canvas takes top `50vh`, Chat bottom `50vh`.
- **Mobile:** Tabbed interface between Chat and Canvas.

### Agent Assembly

**Purpose:** Configuring specialized agents for the swarm.

**Layout:** Sidebar left (`240px`), Main configuration area right.

**Key Elements:**
- **Agent List:** Left sidebar. Highlight active agent with `#F4F4F0` background.
- **System Prompt Editor:** Large text area, `JetBrains Mono`, `13px`, `#F4F4F0` background.
- **Tool Toggles:** Minimal switch components to enable/disable specific capabilities (e.g., "Web Search", "File System").

**States:**
- **Saving:** "Saving..." text top right, `#888883`.
- **Unsaved Changes:** `8px` sunset gradient dot next to agent name.

**Components:**
- **Toggle Switch:** `32x16px`, `#E5E5E0` inactive, `#111111` active. `14x14px` white nub.

**Interactions:**
- **Toggle Click:** Nub slides right `150ms`, background fills `#111111`.

**Responsive:**
- **Desktop:** `240px` sidebar left.
- **Tablet:** Off-canvas sidebar.
- **Mobile:** Stacked accordion.

### Artifact View

**Purpose:** Full-screen immersion into the generated software, removing the chat context.

**Layout:** `100vw`, `100vh`. Absolute minimalist wrapper.

**Key Elements:**
- **Top Bar:** `48px` height, `#FDFCFB` background, `1px` bottom border `#E5E5E0`. Contains back button and deploy CTA.
- **Software Frame:** Fills remaining viewport.
- **Deploy Button:** Top right. Solid `#111111`, white text, `Satoshi`, `13px`.

**States:**
- **Building:** Full screen gradient overlay at `0.05` opacity, breathing animation.
- **Live:** Top bar fades to `0.3` opacity until hovered.

**Components:**
- **Back Button:** `&larr; Return to Chat`, `Satoshi`, `13px`, `#888883`.

**Interactions:**
- **Hover Deploy:** Button background transitions to `--gradient-sunset` in `200ms`.
- **Click Deploy:** Success toast appears top center, green `#10B981` border.

**Responsive:**
- **Desktop:** Full bleed.
- **Tablet:** Full bleed.
- **Mobile:** Full bleed, top bar icons only.

---

## Build Guide

**Stack:** React and TypeScript

**Build Order:**
1. **Chat Canvas** - The most complex screen. Establishing the dual-pane layout, typography hierarchy, and message bubble styles here defines 80% of the app's components.
2. **Hub** - Reuses the input components and typography from Chat. Establishes the layout boundaries.
3. **Agent Assembly** - Introduces forms, toggles, and sidebar navigation.
4. **Artifact View** - Simplest layout, utilizes existing top bar and button components.