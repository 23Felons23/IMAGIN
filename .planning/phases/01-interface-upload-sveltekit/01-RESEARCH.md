# Phase 1: Interface & Upload (SvelteKit)
## Domain Research

**1. SvelteKit & Vite Initialization**
SvelteKit or Vite+Svelte is typically established via `npx -y create-vite@latest frontend --template svelte`. The application relies entirely on `.svelte` files which encapsulate HTML, Javascript, and Vanilla CSS locally within `<style>` blocks or globally in `app.css`.

**2. Handling Bouncy/Hormozi Styles**
Following the `frontend-design` aesthetics protocol, we avoid Tailwind "slop" and instead handwrite strong Brutalist CSS variables with severe border-radius reductions (or thick sharp edges), heavy shadowing (`box-shadow: 4px 4px 0px #000;`), and maximalist colors like safety orange (#FF5500) and electric cyan (#00FFCC). Emojis and bouncing subtitles will be rendered server-side via Remotion later, but the frontend configuration interface must embody this identical brutalist, rapid-fire ethos.

**3. Audio/Video File Uploads in Svelte**
Large file handling is best avoided in Memory. A true Web Service will proxy to a backend. For this phase, we establish a robust HTML5 File Dropzone using `on:drop` coupled with `event.dataTransfer.files`. We'll simulate the wait queue before backend integration triggers.

**4. Architecture Decisions**
- Keep dependencies lean. No bulky UI libraries. Vanilla CSS Grid for brutalist structure. 
- A single Page Application view (`App.svelte`) is enough for the upload dashboard.
- State handled efficiently via Svelte reactive declarations (`$: jobs`).
