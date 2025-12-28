// Utility function to safely extract hostname from URL
export const safeGetHostname = (url: string): string => {
    if (!url || typeof url !== 'string') {
        return 'unknown page'
    }

    // Check if it's a valid URL format
    try {
        // First check if it looks like a URL
        if (!url.includes('://') && !url.startsWith('//')) {
            return url === 'this page' ? 'this page' : 'unknown page'
        }

        const urlObj = new URL(url)
        return urlObj.hostname || 'unknown page'
    } catch {
        return url === 'this page' ? 'this page' : 'unknown page'
    }
}
  