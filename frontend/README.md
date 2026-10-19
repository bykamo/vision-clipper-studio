# VisionClipper Studio — Frontend

React 19 + Vite 6 + Tailwind CSS v4 dashboard for the VisionClipper Studio
backend. The built output in `dist/` is served by the Python backend at
<http://127.0.0.1:5050>.

## Development

```bash
npm install
npm run dev        # http://127.0.0.1:3000 (proxies /api, /stream, /cancel, /shutdown to :5050)
```

Start the backend in a second terminal so the proxy has something to talk to:

```bash
cd ..
.venv/bin/python -m backend.main
```

## Scripts

| Script                 | What it does                                           |
| ---------------------- | ------------------------------------------------------ |
| `npm run dev`          | Vite dev server on port 3000 with API proxy            |
| `npm run build`        | Production build into `dist/` (does **not** typecheck) |
| `npm run typecheck`    | `tsc --noEmit` — strict, `noUnusedLocals` enabled      |
| `npm run lint`         | ESLint (flat config, TS + React Hooks + Prettier)      |
| `npm run lint:fix`     | ESLint with `--fix`                                    |
| `npm run format`       | Prettier write for `src/**/*.{ts,tsx,css}`             |
| `npm run format:check` | Prettier check (used by CI)                            |
| `npm run verify`       | `typecheck` + `lint` + `build` — run before committing |

> **Important:** `vite build` strips types without checking them, so a
> component can reference an undefined symbol and still build. Always run
> `npm run typecheck` (or `npm run verify`) before committing.

## Structure

```
src/
├── App.tsx                    # Root shell
├── main.tsx                   # React entry, wraps App in ErrorBoundary
├── index.css                  # Tailwind v4 + iPhone mockup / transport styles
├── components/
│   ├── SimpleClipperDashboard.tsx  # 3-column workspace, workflow state, SSE
│   ├── PhonePreview.tsx            # 9:16 phone mockup + TikTok/Reels/Shorts overlays
│   ├── StudioSettingsModal.tsx     # AI / Whisper / YouTube / TikTok settings
│   ├── ErrorBoundary.tsx           # Top-level render error guard
│   ├── SkeletonLoading.tsx         # Analyzing-state skeletons
│   ├── BrandIcons.tsx              # Custom provider/brand SVGs
│   └── ui/                         # Small shadcn-style primitives
├── data/subtitlePresets.ts    # Subtitle style presets
├── lib/utils.ts               # `cn()` class merge helper
└── types/index.ts             # Shared types
```

## Notes

- The phone mockup renders at a fixed 356×772 CSS-pixel screen and is scaled
  down to fit the column, so overlay type sizes are authored at true phone
  dimensions (see `PhonePreview.tsx`).
- `public/images/mockup-apple-iphone-17-pro-2025-transparent.png` is the phone
  frame overlay; `logo-icon-transparent.png` is the empty-state logo.
