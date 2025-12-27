import next from 'eslint-config-next'

/**
 * Next.js 16 ships a flat ESLint config. We spread its defaults so we can
 * append project-specific tweaks later without losing the upstream settings.
 */
const config = next.map((entry) => {
  if (!('rules' in entry) || !entry.rules) {
    return entry
  }

  return {
    ...entry,
    rules: {
      ...entry.rules,
      'react-hooks/exhaustive-deps': 'off',
      'react-hooks/purity': 'off',
      'react-hooks/set-state-in-effect': 'off',
    },
  }
})

export default config
