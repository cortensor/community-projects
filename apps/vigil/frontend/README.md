# Frontend Template

A modern React + TypeScript template with a beautiful UI, ready to use for your next project.

## Features

- ⚡ **Vite** - Lightning-fast development
- ⚛️ **React 18** - Latest React features
- 🎨 **Tailwind CSS** - Utility-first styling with custom design system
- ✨ **Framer Motion** - Smooth animations
- 🧭 **React Router** - Client-side routing
- 🔥 **React Hot Toast** - Beautiful notifications
- 📊 **Vercel Analytics** - Built-in analytics support
- 📝 **TypeScript** - Type safety

## Design System

The template includes a custom design system with:
- Glass morphism effects
- Custom color palette (accent-indigo, text variants)
- Smooth transitions and animations
- Responsive navigation
- Pre-styled components

## Getting Started

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Build for production:**
   ```bash
   npm run build
   ```

## Customization

### Update Branding
- Edit `src/App.tsx` - Change "YourBrand" to your app name
- Edit `index.html` - Update title and meta description
- Replace `public/favicon.png` with your logo

### Add Routes
Add new routes in `src/App.tsx`:
```tsx
const navLinks = [
  { path: '/your-route', label: 'Your Page', icon: '🎯' },
];
```

### Create Components
Add components in `src/components/` directory

### Add Context
Add global state in `src/context/` directory

## Project Structure

```
src/
├── components/     # Reusable components
├── context/        # React context providers
├── hooks/          # Custom hooks
├── utils/          # Utility functions
├── assets/         # Static assets
├── App.tsx         # Main app component
├── main.tsx        # Entry point
└── index.css       # Global styles
```

## License

MIT
