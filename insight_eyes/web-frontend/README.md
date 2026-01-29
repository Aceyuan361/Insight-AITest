# Insight Eye - Web Frontend

Web-based performance monitoring dashboard for Insight Eye. Built with React + TypeScript + Vite, featuring a cyberpunk neon theme UI with real-time performance metrics visualization.

## Features

- Real-time performance monitoring dashboard
- WebSocket-based live data updates
- Interactive charts using ECharts
- Cyberpunk neon theme UI
- Responsive design for cross-platform access
- State management with Zustand
- TailwindCSS for styling

## Prerequisites

- **Node.js**: 22+ (Check with `node --version`)
- **npm**: 10+ (Check with `npm --version`)
- **Backend**: FastAPI server running on http://localhost:8000

## Installation

1. Install dependencies:
```bash
npm install
```

## Development

Start the development server:
```bash
npm run dev
```

The application will be available at http://localhost:3000

The dev server proxies:
- API requests (`/api/*`) → http://localhost:8000
- WebSocket connections (`/ws/*`) → ws://localhost:8000

## Build

Build for production:
```bash
npm run build
```

The built files will be in the `dist/` directory.

Preview production build:
```bash
npm run preview
```

## Project Structure

```
web-frontend/
├── src/
│   ├── main.tsx          # Application entry point
│   ├── App.tsx           # Root component
│   └── index.css         # Global styles with TailwindCSS
├── public/               # Static assets
├── index.html            # HTML template
├── vite.config.ts        # Vite configuration
├── tailwind.config.js    # TailwindCSS configuration
└── tsconfig.json         # TypeScript configuration
```

## Technology Stack

- **React 19**: UI framework
- **TypeScript**: Type-safe development
- **Vite**: Build tool and dev server
- **ECharts**: Chart visualization library
- **Zustand**: State management
- **TailwindCSS**: Utility-first CSS framework
- **Axios**: HTTP client
- **Day.js**: Date/time manipulation

## Neon Theme Colors

- CPU: `#00f2ff` (cyan)
- Memory: `#7000ff` (purple)
- FPS: `#ffb400` (orange)
- Network Up: `#00ff87` (green)
- Network Down: `#0062ff` (blue)
- Background: `#0a0a0a` (dark)
- Card: `#141414` (dark gray)

## Environment Variables

Create environment files as needed:

- `.env` - Shared environment variables
- `.env.local` - Local overrides (gitignored)
- `.env.production` - Production environment

## Linting

Run ESLint:
```bash
npm run lint
```

## License

Part of the Insight Eye project.
