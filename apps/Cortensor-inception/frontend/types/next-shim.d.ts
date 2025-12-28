declare module 'next/app' {
  export type AppProps = any;
}

declare module 'next/link' {
  import React from 'react';
  const Link: React.FC<any>;
  export default Link;
}
