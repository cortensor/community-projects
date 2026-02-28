import { ImageResponse } from 'next/og';

// Route segment config
export const runtime = 'edge';

// Image metadata
export const alt = 'Cortex.OS Auditor';
export const size = {
  width: 32,
  height: 32,
};
export const contentType = 'image/png';

// Image generation
export default function Icon() {
  const protocol = process.env.NODE_ENV === 'development' ? 'http' : 'https';
  // Attempt to detect host using standard env vars
  const host = process.env.NEXT_PUBLIC_APP_URL || process.env.VERCEL_URL || 'localhost:3000';
  const logoUrl = host.startsWith('http') ? `${host}/Cortex_OS.png` : `${protocol}://${host}/Cortex_OS.png`;

  return new ImageResponse(
    (
      <div
        style={{
          background: 'transparent',
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <img
          src={logoUrl}
          style={{
            width: '280%', // Aggressive zoom to crop padding
            height: '280%',
            objectFit: 'contain',
          }}
        />
      </div>
    ),
    {
      ...size,
    }
  );
}
