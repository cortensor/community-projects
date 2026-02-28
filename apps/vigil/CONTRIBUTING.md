# Contributing to Vigil

Thank you for your interest in contributing! This project is open source and welcomes contributions from the community.

## Getting Started

1. **Fork the repository**
2. **Clone your fork:**
   ```bash
   git clone https://github.com/yourusername/incident-commander.git
   cd incident-commander
   ```
3. **Install dependencies:**
   ```bash
   ./start.sh
   ```

## Development Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow existing code style
   - Add tests if applicable
   - Update documentation

3. **Test your changes:**
   ```bash
   ./examples/test-agent.sh
   ```

4. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push to your fork:**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**

## Commit Message Convention

We follow conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: add email notification support
fix: resolve WebSocket reconnection issue
docs: update deployment guide
```

## Code Style

### TypeScript
- Use TypeScript strict mode
- Prefer interfaces over types
- Use async/await over promises
- Add JSDoc comments for public APIs

### React
- Use functional components with hooks
- Keep components small and focused
- Use TypeScript for props
- Follow existing naming conventions

### General
- Use meaningful variable names
- Keep functions small and focused
- Add comments for complex logic
- Remove console.logs before committing

## Project Structure

```
backend/src/
├── monitors/     # Metrics collection
├── detectors/    # Anomaly detection
├── actions/      # Action executors
├── evidence/     # Evidence bundling
├── managers/     # Orchestration
├── simulator/    # Demo mode
├── api/          # REST + WebSocket
├── db/           # Database
└── types/        # TypeScript types

frontend/src/
├── components/   # React components
├── hooks/        # Custom hooks
└── utils/        # Utility functions
```

## Adding New Features

### Adding a New Action Type

1. Create action executor in `backend/src/actions/`
2. Add to `ActionExecutor` class
3. Update `Action` type in `types/index.ts`
4. Add rate limiting
5. Update evidence bundler
6. Update UI to display action
7. Document in TOOLS.md

### Adding a New Metric

1. Update `MetricsSnapshot` interface
2. Add collection in `MetricsMonitor`
3. Add anomaly detection threshold
4. Update UI metric cards
5. Update documentation

### Adding a New Model

1. Add to `MODELS` array in `detectors/cortensor.ts`
2. Update consensus logic if needed
3. Test with existing incidents
4. Update documentation

## Testing

### Manual Testing
```bash
# Start services
./start.sh

# Run test script
./examples/test-agent.sh

# Test demo mode
# 1. Open http://localhost:5173
# 2. Click "Simulate Incident"
# 3. Verify full workflow
```

### Automated Testing
```bash
cd backend
npm test

cd frontend
npm test
```

## Documentation

When adding features, update:
- README.md - If user-facing
- ARCHITECTURE.md - If changing system design
- TOOLS.md - If adding/changing agent capabilities
- DEPLOYMENT.md - If affecting deployment
- DEMO.md - If affecting demo flow

## Pull Request Guidelines

### Before Submitting
- [ ] Code follows project style
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] No console.logs or debug code
- [ ] Branch is up to date with main

### PR Description Should Include
- What changes were made
- Why the changes were needed
- How to test the changes
- Screenshots (if UI changes)
- Related issues (if any)

### Review Process
1. Automated CI checks must pass
2. At least one maintainer approval required
3. All review comments addressed
4. No merge conflicts

## Bug Reports

When reporting bugs, include:
- Description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment (OS, Node version, etc.)
- Logs/screenshots if applicable

Use the GitHub issue template.

## Feature Requests

When requesting features:
- Describe the feature
- Explain the use case
- Provide examples if possible
- Consider implementation complexity

## Questions?

- Open a GitHub Discussion
- Join Discord: discord.gg/cortensor
- Check existing documentation

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to Vigil! 🚀
